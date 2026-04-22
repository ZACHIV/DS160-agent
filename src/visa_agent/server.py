"""Local FastAPI server bridging the DS-160 assistant frontend to Chrome via CDP."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

# Allow running directly: python -m visa_agent.server
sys.path.insert(0, str(Path(__file__).parent.parent))

from visa_agent.browser.cdp_client import find_target_websocket_url, list_debug_targets
from visa_agent.browser.live_form_fill import (
    _PAGE_FILL_HANDLERS,
    detect_current_page,
    fill_current_supported_page,
    save_current_page,
)
from visa_agent.draft_bundle import build_draft_bundle
from visa_agent.intake_contract import intake_field_errors, load_intake_schema, normalized_intake_payload, validate_intake_payload
from visa_agent.intake import (
    ApplicantIntake,
    build_dossier_from_intake,
    dossier_to_dict,
    intake_payload_to_dossier,
)
from visa_agent.mapping import map_dossier_to_ds160
from visa_agent.vision_intake import VisionUploadedDocument, build_prompt_text, extract_intake_from_documents, vision_document_specs
from visa_agent.page_ids import PAGE_ID_NORMALIZE
from visa_agent.planner import build_execution_plan
from visa_agent.schema import load_dossier, load_dossier_payload

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CDP_PORT = int(os.environ.get("CDP_PORT", "9222"))
DOSSIER_PATH = os.environ.get(
    "DOSSIER_PATH",
    str(Path(__file__).parent.parent.parent / "sample_data" / "china_b1b2_sample.json"),
)
ACTIVE_INTAKE_DOCUMENT: dict[str, Any] | None = None
ACTIVE_DOCUMENT_KIND: str | None = None

app = FastAPI(title="DS-160 Local Fill Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class FillPageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page_id: str | None = None  # if None, auto-detect from current browser URL


class FillPageResponse(BaseModel):
    ok: bool
    page_key: str
    filled: list[str]
    missing: list[str]
    message: str


class StatusResponse(BaseModel):
    connected: bool
    cdp_port: int
    open_tabs: int
    ceac_tab_found: bool
    dossier_loaded: bool
    dossier_path: str
    intake_loaded: bool


class DetectPageResponse(BaseModel):
    page_key: str
    url: str
    title: str


class IntakePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    surname: str
    given_names: str
    native_full_name: str | None = None
    sex: str
    marital_status: str
    date_of_birth: str
    birth_city: str
    passport_number: str
    passport_issue_date: str
    passport_expiration_date: str
    trip_purpose: str
    intended_arrival_date: str
    intended_length_of_stay_value: str
    intended_length_of_stay_unit: str
    payer_name: str
    us_contact_name: str
    us_contact_organization: str | None = None
    us_contact_phone: str
    us_contact_address_line1: str
    us_contact_city: str
    us_contact_state: str
    us_contact_postal_code: str
    us_contact_email: str | None = None
    primary_occupation: str
    current_employer_name: str
    current_employer_address: str
    father_full_name: str
    mother_full_name: str
    spouse_full_name: str | None = None
    communicable_disease: bool = False
    arrest_history: bool = False


class IntakePreviewResponse(BaseModel):
    ok: bool
    dossier: dict[str, Any]
    status_counts: dict[str, int]
    review_items: list[dict[str, Any]]
    blocked_items: list[dict[str, Any]]
    top_fill_fields: list[dict[str, Any]]
    hard_stops: list[str]
    page_count: int


class IntakeDocumentResponse(BaseModel):
    ok: bool
    intake_document: dict[str, Any]
    case_id: str


class DraftBundleResponse(BaseModel):
    ok: bool
    bundle: dict[str, Any]


class IntakeSchemaResponse(BaseModel):
    ok: bool
    schema_document: dict[str, Any]


class VisionUploadedDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str
    filename: str
    media_type: str
    base64_data: str


class VisionIntakeExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    documents: list[VisionUploadedDocumentRequest]


class VisionManifestResponse(BaseModel):
    ok: bool
    documents: list[dict[str, Any]]


class VisionPromptResponse(BaseModel):
    ok: bool
    prompt_text: str


class VisionIntakeExtractResponse(BaseModel):
    ok: bool
    intake_document: dict[str, Any] | None
    missing_fields: list[str]
    warnings: list[str]
    documents: list[dict[str, Any]]


class VisionModelResultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result: dict[str, Any]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_dossier():
    if ACTIVE_INTAKE_DOCUMENT is not None:
        try:
            if ACTIVE_DOCUMENT_KIND == "dossier":
                return load_dossier_payload(ACTIVE_INTAKE_DOCUMENT)
            return intake_payload_to_dossier(validate_intake_payload(ACTIVE_INTAKE_DOCUMENT))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Cannot build dossier from intake document: {exc}")
    try:
        return load_dossier(DOSSIER_PATH)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cannot load dossier: {exc}")


def _check_cdp() -> list[dict[str, Any]]:
    try:
        return list_debug_targets(port=CDP_PORT)
    except Exception:
        return []


def _has_ceac_tab(tabs: list[dict[str, Any]]) -> bool:
    return any("ceac.state.gov" in (t.get("url") or "") for t in tabs)


def _build_preview_payload(dossier) -> IntakePreviewResponse:
    mapped = map_dossier_to_ds160(dossier)
    execution_plan = build_execution_plan(mapped)
    draft_bundle = build_draft_bundle(dossier)
    status_counts = {"ready": 0, "needs_review": 0, "blocked": 0}
    for field in mapped:
        status_counts[field.status] = status_counts.get(field.status, 0) + 1
    review_items = [field.to_dict() for field in mapped if field.status == "needs_review"]
    blocked_items = [field.to_dict() for field in mapped if field.status == "blocked"]
    top_fill_fields = [field.to_dict() for field in mapped if field.status == "ready"][:8]
    return IntakePreviewResponse(
        ok=True,
        dossier=dossier_to_dict(dossier),
        status_counts=status_counts,
        review_items=review_items,
        blocked_items=blocked_items,
        top_fill_fields=top_fill_fields,
        hard_stops=list(execution_plan.hard_stops),
        page_count=int(draft_bundle["summary"]["page_count"]),
    )


def _coerce_active_document(payload: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    if _looks_like_full_dossier(payload):
        dossier = load_dossier_payload(payload)
        return payload, dossier.case_id, "dossier"
    intake_document = validate_intake_payload(payload)
    dossier = intake_payload_to_dossier(intake_document)
    return intake_document, dossier.case_id, "intake"


def _looks_like_full_dossier(payload: dict[str, Any]) -> bool:
    required_sections = {
        "case_id",
        "identity",
        "travel_plan",
        "employment_education",
        "family_contacts",
        "security_background",
    }
    return required_sections.issubset(payload.keys())


# Map from page_id (as used in the frontend bundle) to fill function
_PAGE_FILL_MAP = {
    "personal_page_1": "personal1",
    "personal_page_2": "personal2",
    "personal1": "personal1",
    "personal2": "personal2",
}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/status", response_model=StatusResponse)
def get_status():
    """Check CDP connection and dossier availability."""
    tabs = _check_cdp()
    dossier_ok = Path(DOSSIER_PATH).exists()
    return StatusResponse(
        connected=len(tabs) > 0,
        cdp_port=CDP_PORT,
        open_tabs=len(tabs),
        ceac_tab_found=_has_ceac_tab(tabs),
        dossier_loaded=dossier_ok,
        dossier_path=DOSSIER_PATH,
        intake_loaded=ACTIVE_INTAKE_DOCUMENT is not None,
    )


@app.get("/detect-page", response_model=DetectPageResponse)
def get_detect_page():
    """Detect which DS-160 page is currently open in the browser."""
    tabs = _check_cdp()
    if not tabs:
        raise HTTPException(status_code=503, detail="Chrome not reachable on CDP port")
    try:
        result = detect_current_page()
        return DetectPageResponse(
            page_key=result.payload.get("page_key", "unsupported"),
            url=result.payload.get("url", ""),
            title=result.payload.get("title", ""),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/intake/preview", response_model=IntakePreviewResponse)
def post_intake_preview(req: IntakePreviewRequest):
    """Build a dossier from the minimal intake form and return preview status."""
    try:
        payload = validate_intake_payload(req.model_dump())
        dossier = build_dossier_from_intake(ApplicantIntake(**payload))
        return _build_preview_payload(dossier)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/intake-schema", response_model=IntakeSchemaResponse)
def get_intake_schema():
    """Return the canonical intake schema used by both intake and execution flows."""
    return IntakeSchemaResponse(ok=True, schema_document=load_intake_schema())


@app.post("/intake-document", response_model=IntakeDocumentResponse)
def post_intake_document(req: IntakePreviewRequest | dict[str, Any]):
    """Set the active intake document used by the fill assistant."""
    global ACTIVE_INTAKE_DOCUMENT, ACTIVE_DOCUMENT_KIND
    payload = req.model_dump() if isinstance(req, BaseModel) else dict(req)
    ACTIVE_INTAKE_DOCUMENT, case_id, ACTIVE_DOCUMENT_KIND = _coerce_active_document(payload)
    return IntakeDocumentResponse(
        ok=True,
        intake_document=ACTIVE_INTAKE_DOCUMENT,
        case_id=case_id,
    )


@app.get("/intake-document", response_model=IntakeDocumentResponse)
def get_intake_document():
    """Return the currently loaded intake document."""
    if ACTIVE_INTAKE_DOCUMENT is None:
        raise HTTPException(status_code=404, detail="No intake document loaded")
    dossier = _load_dossier()
    return IntakeDocumentResponse(
        ok=True,
        intake_document=ACTIVE_INTAKE_DOCUMENT,
        case_id=dossier.case_id,
    )


@app.get("/draft-bundle", response_model=DraftBundleResponse)
def get_draft_bundle():
    """Build the assistant bundle from the active intake document or legacy dossier."""
    dossier = _load_dossier()
    return DraftBundleResponse(ok=True, bundle=build_draft_bundle(dossier))


@app.get("/vision-intake/manifest", response_model=VisionManifestResponse)
def get_vision_manifest():
    """Describe which images the vision intake page expects from the user."""
    return VisionManifestResponse(ok=True, documents=vision_document_specs())


@app.post("/vision-intake/prompt", response_model=VisionPromptResponse)
def post_vision_prompt(req: VisionIntakeExtractRequest):
    """Build the prompt text that the user can paste into an external vision model."""
    documents = [
        VisionUploadedDocument(
            kind=item.kind,
            filename=item.filename,
            media_type=item.media_type,
            base64_data=item.base64_data,
        )
        for item in req.documents
    ]
    return VisionPromptResponse(ok=True, prompt_text=build_prompt_text(documents, load_intake_schema()))


@app.post("/vision-intake/extract", response_model=VisionIntakeExtractResponse)
def post_vision_extract(req: VisionIntakeExtractRequest):
    """Run vision-model extraction over uploaded images and attempt to build the intake-v1 JSON document."""
    try:
        result = extract_intake_from_documents(
            [
                VisionUploadedDocument(
                    kind=item.kind,
                    filename=item.filename,
                    media_type=item.media_type,
                    base64_data=item.base64_data,
                )
                for item in req.documents
            ],
            schema=load_intake_schema(),
        )
        return VisionIntakeExtractResponse(ok=True, **result.to_dict())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/vision-intake/validate", response_model=VisionIntakeExtractResponse)
def post_vision_validate(req: VisionModelResultRequest):
    """Validate a manually obtained vision-model result and convert it into the intake result shape."""
    try:
        payload = normalized_intake_payload(req.result)
        missing_fields = [
            field
            for field, value in payload.items()
            if field in load_intake_schema().get("required", []) and value in (None, "")
        ]
        warnings: list[str] = []
        intake_document = None
        if not missing_fields:
            try:
                intake_document = validate_intake_payload(payload)
            except Exception as exc:
                missing_fields = list(intake_field_errors(payload).keys())
                warnings.append(str(exc))
                intake_document = None
        return VisionIntakeExtractResponse(
            ok=True,
            intake_document=intake_document,
            missing_fields=missing_fields,
            warnings=warnings,
            documents=[],
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/fill-page", response_model=FillPageResponse)
def post_fill_page(req: FillPageRequest):
    """Fill the specified (or currently open) DS-160 page via CDP."""
    tabs = _check_cdp()
    if not tabs:
        raise HTTPException(status_code=503, detail="Chrome not reachable on CDP port. Launch Chrome with --remote-debugging-port=9222")

    dossier = _load_dossier()

    # Resolve page_id → canonical key
    page_id = req.page_id
    # Normalize frontend page_id (e.g. "personal_page_1" → "personal1")
    if page_id:
        canonical = PAGE_ID_NORMALIZE.get(page_id, page_id)
    else:
        # Auto-detect from browser URL
        try:
            detected = detect_current_page()
            canonical = detected.payload.get("page_key")
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Cannot detect current page: {exc}")

    try:
        handler = _PAGE_FILL_HANDLERS.get(canonical) if canonical else None
        if handler:
            result = handler(dossier)
        else:
            # Fallback: try auto-detect fill
            result = fill_current_supported_page(dossier)

        filled = result.payload.get("filled") or []
        missing = result.payload.get("missing") or []
        return FillPageResponse(
            ok=result.ok,
            page_key=canonical or result.payload.get("page_key", "unsupported"),
            filled=filled,
            missing=missing,
            message=f"Filled {len(filled)} fields, {len(missing)} missing.",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/save-page")
def post_save_page():
    """Click the Save button on the current DS-160 page."""
    tabs = _check_cdp()
    if not tabs:
        raise HTTPException(status_code=503, detail="Chrome not reachable on CDP port")
    try:
        result = save_current_page()
        return {"ok": result.ok, "payload": result.payload}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "visa_agent.server:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
        log_level="info",
    )
