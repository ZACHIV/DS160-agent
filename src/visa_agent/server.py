"""Local FastAPI server bridging the DS-160 assistant frontend to Chrome via CDP."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

# Allow running directly: python -m visa_agent.server
sys.path.insert(0, str(Path(__file__).parent.parent))

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = PROJECT_ROOT / "app"

from visa_agent.browser.cdp_client import find_target_websocket_url, list_debug_targets
from visa_agent.browser.live_form_fill import (
    _PAGE_FILL_HANDLERS,
    detect_current_page,
    fill_and_continue,
    fill_current_supported_page,
    save_current_page,
)
from visa_agent.dossier_contract import (
    dossier_to_dict,
    load_dossier_schema,
    validate_dossier_payload,
)
from visa_agent.draft_bundle import build_draft_bundle
from visa_agent.encryption import encrypt_dossier_json, is_encrypted_dossier
from visa_agent.mapping import map_dossier_to_ds160
from visa_agent.page_ids import PAGE_ID_NORMALIZE, bundle_page_id
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
ACTIVE_DOSSIER_DOCUMENT: dict[str, Any] | None = None

app = FastAPI(title="DS-160 Local Fill Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static assets (CSS, JS) from the app directory
if APP_DIR.is_dir():
    app.mount("/app", StaticFiles(directory=str(APP_DIR)), name="app_static")


@app.get("/", response_class=HTMLResponse)
def get_landing():
    """Unified landing page linking intake and assistant."""
    if (APP_DIR / "index.html").is_file():
        return HTMLResponse((APP_DIR / "index.html").read_text(encoding="utf-8"))
    # Fallback inline landing page
    return HTMLResponse("""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>DS-160 Visa Assistant</title>
<style>
:root{--bg:#0a0a0f;--surface:#141420;--text:#e0e0e0;--accent:#6fcf97;--accent2:#5b9bd5}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:var(--bg);color:var(--text);display:flex;align-items:center;justify-content:center;min-height:100vh}
main{display:flex;gap:2rem;max-width:720px;padding:2rem}
.card{background:var(--surface);border-radius:12px;padding:2rem;text-align:center;flex:1;border:1px solid #222;transition:border-color .2s}
.card:hover{border-color:var(--accent)}
.card h2{font-size:1.25rem;margin-bottom:.5rem}
.card p{color:#888;margin-bottom:1.5rem;font-size:.9rem;line-height:1.5}
.card a{display:inline-block;padding:.6rem 1.5rem;border-radius:6px;text-decoration:none;font-weight:600;font-size:.9rem}
.card a.primary{background:var(--accent);color:#000}
.card a.secondary{background:var(--accent2);color:#fff}
</style>
</head>
<body>
<main>
<div class="card"><h2>资料采集</h2><p>填写申请人全部信息，生成统一 dossier 文件。</p><a class="secondary" href="/intake">打开 Intake</a></div>
<div class="card"><h2>表单填写</h2><p>导入 dossier 文件，在 DS-160 页面上自动填入。</p><a class="primary" href="/assistant">打开 Assistant</a></div>
</main>
</body>
</html>""")


@app.get("/intake", response_class=HTMLResponse)
def get_intake():
    """Serve the DS-160 intake page."""
    html = (APP_DIR / "intake.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/assistant", response_class=HTMLResponse)
def get_assistant():
    """Serve the DS-160 fill assistant page."""
    html = (APP_DIR / "ds160-assistant.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


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


class FillContinueResponse(BaseModel):
    ok: bool
    page_key: str
    new_page_key: str | None
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
    dossier_document_loaded: bool


class DetectPageResponse(BaseModel):
    page_key: str
    url: str
    title: str


class DossierPreviewResponse(BaseModel):
    ok: bool
    dossier: dict[str, Any]
    status_counts: dict[str, int]
    review_items: list[dict[str, Any]]
    blocked_items: list[dict[str, Any]]
    top_fill_fields: list[dict[str, Any]]
    hard_stops: list[str]
    page_count: int


class DossierDocumentResponse(BaseModel):
    ok: bool
    dossier_document: dict[str, Any]
    case_id: str


class DraftBundleResponse(BaseModel):
    ok: bool
    bundle: dict[str, Any]


class DossierSchemaResponse(BaseModel):
    ok: bool
    schema_document: dict[str, Any]


class DossierPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    identity: dict[str, Any]
    travel_plan: dict[str, Any]
    employment_education: dict[str, Any]
    family_contacts: dict[str, Any]
    security_background: dict[str, Any]
    evidence_catalog: list[dict[str, Any]] = []


class DossierEncryptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    passphrase: str


class DossierEncryptResponse(BaseModel):
    ok: bool
    encrypted_payload: dict[str, Any]


class DossierDecryptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    encrypted_payload: dict[str, Any]
    passphrase: str


class DossierDecryptResponse(BaseModel):
    ok: bool
    dossier_document: dict[str, Any]
    case_id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_dossier():
    if ACTIVE_DOSSIER_DOCUMENT is not None:
        try:
            return load_dossier_payload(ACTIVE_DOSSIER_DOCUMENT)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Cannot build dossier from active document: {exc}")
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


def _build_preview_payload(dossier) -> DossierPreviewResponse:
    mapped = map_dossier_to_ds160(dossier)
    execution_plan = build_execution_plan(mapped)
    draft_bundle = build_draft_bundle(dossier)
    status_counts = {"ready": 0, "needs_review": 0, "blocked": 0}
    for field in mapped:
        status_counts[field.status] = status_counts.get(field.status, 0) + 1
    review_items = [field.to_dict() for field in mapped if field.status == "needs_review"]
    blocked_items = [field.to_dict() for field in mapped if field.status == "blocked"]
    top_fill_fields = [field.to_dict() for field in mapped if field.status == "ready"][:8]
    return DossierPreviewResponse(
        ok=True,
        dossier=dossier_to_dict(dossier),
        status_counts=status_counts,
        review_items=review_items,
        blocked_items=blocked_items,
        top_fill_fields=top_fill_fields,
        hard_stops=list(execution_plan.hard_stops),
        page_count=int(draft_bundle["summary"]["page_count"]),
    )


def _coerce_active_document(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    dossier_payload = validate_dossier_payload(payload)
    dossier = load_dossier_payload(dossier_payload)
    return dossier_payload, dossier.case_id


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
        dossier_document_loaded=ACTIVE_DOSSIER_DOCUMENT is not None,
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


@app.post("/dossier/preview", response_model=DossierPreviewResponse)
def post_dossier_preview(req: DossierPreviewRequest):
    """Validate a full dossier payload and return preview status."""
    try:
        payload = validate_dossier_payload(dict(req.model_dump()))
        dossier = load_dossier_payload(payload)
        return _build_preview_payload(dossier)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/dossier-schema", response_model=DossierSchemaResponse)
def get_dossier_schema():
    """Return the canonical dossier schema used by intake and execution flows."""
    return DossierSchemaResponse(ok=True, schema_document=load_dossier_schema())


@app.post("/dossier-document", response_model=DossierDocumentResponse)
def post_dossier_document(req: DossierPreviewRequest):
    """Set the active dossier document used by the fill assistant."""
    global ACTIVE_DOSSIER_DOCUMENT
    payload = dict(req.model_dump())
    ACTIVE_DOSSIER_DOCUMENT, case_id = _coerce_active_document(payload)
    return DossierDocumentResponse(
        ok=True,
        dossier_document=ACTIVE_DOSSIER_DOCUMENT,
        case_id=case_id,
    )


@app.get("/dossier-document", response_model=DossierDocumentResponse)
def get_dossier_document():
    """Return the currently loaded dossier document."""
    if ACTIVE_DOSSIER_DOCUMENT is None:
        raise HTTPException(status_code=404, detail="No dossier document loaded")
    dossier = _load_dossier()
    return DossierDocumentResponse(
        ok=True,
        dossier_document=ACTIVE_DOSSIER_DOCUMENT,
        case_id=dossier.case_id,
    )


@app.post("/dossier-document/encrypt", response_model=DossierEncryptResponse)
def post_dossier_encrypt(req: DossierEncryptRequest):
    """Encrypt the active dossier document with a passphrase."""
    if ACTIVE_DOSSIER_DOCUMENT is None:
        raise HTTPException(status_code=404, detail="No dossier document loaded")
    if len(req.passphrase) < 8:
        raise HTTPException(status_code=400, detail="Passphrase must be at least 8 characters")
    plaintext = json.dumps(ACTIVE_DOSSIER_DOCUMENT, ensure_ascii=False)
    encrypted = encrypt_dossier_json(plaintext, req.passphrase)
    return DossierEncryptResponse(
        ok=True,
        encrypted_payload=json.loads(encrypted),
    )


@app.post("/dossier-document/decrypt", response_model=DossierDecryptResponse)
def post_dossier_decrypt(req: DossierDecryptRequest):
    """Decrypt an encrypted dossier and set it as the active document."""
    global ACTIVE_DOSSIER_DOCUMENT
    from visa_agent.encryption import decrypt_dossier_json

    if not is_encrypted_dossier(req.encrypted_payload):
        raise HTTPException(status_code=400, detail="Payload is not an encrypted dossier")
    try:
        encrypted_json = json.dumps(req.encrypted_payload, ensure_ascii=False)
        plaintext = decrypt_dossier_json(encrypted_json, req.passphrase)
    except Exception:
        raise HTTPException(status_code=400, detail="Decryption failed. Wrong passphrase or corrupted data.")
    dossier_payload = json.loads(plaintext)
    ACTIVE_DOSSIER_DOCUMENT, case_id = _coerce_active_document(dossier_payload)
    return DossierDecryptResponse(
        ok=True,
        dossier_document=ACTIVE_DOSSIER_DOCUMENT,
        case_id=case_id,
    )


@app.get("/draft-bundle", response_model=DraftBundleResponse)
def get_draft_bundle():
    """Build the assistant bundle from the active dossier document or legacy dossier."""
    dossier = _load_dossier()
    return DraftBundleResponse(ok=True, bundle=build_draft_bundle(dossier))


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


@app.post("/fill-and-continue", response_model=FillContinueResponse)
def post_fill_and_continue(req: FillPageRequest):
    """Fill the current page, save, and click Next to advance to the next page."""
    tabs = _check_cdp()
    if not tabs:
        raise HTTPException(status_code=503, detail="Chrome not reachable on CDP port. Launch Chrome with --remote-debugging-port=9222")

    dossier = _load_dossier()

    canonical = PAGE_ID_NORMALIZE.get(req.page_id, req.page_id) if req.page_id else None
    if not canonical:
        try:
            detected = detect_current_page()
            canonical = detected.payload.get("page_key")
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Cannot detect current page: {exc}")

    if canonical not in _PAGE_FILL_HANDLERS:
        raise HTTPException(status_code=400, detail=f"No fill handler for page {canonical}")

    try:
        result = fill_and_continue(canonical, dossier)
        fill_payload = result.get("fill_payload") or {}
        filled = list(fill_payload.get("filled") or [])
        missing = list(fill_payload.get("missing") or [])
        raw_new_key = result.get("new_page_key")
        new_page_key = bundle_page_id(raw_new_key) if raw_new_key else None
        return FillContinueResponse(
            ok=bool(result.get("fill_ok") and result.get("next_ok")),
            page_key=canonical,
            new_page_key=new_page_key,
            filled=filled,
            missing=missing,
            message=f"Filled {len(filled)} fields, {len(missing)} missing. Next page: {new_page_key or 'unknown'}",
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
        host=os.environ.get("API_HOST", "127.0.0.1"),
        port=int(os.environ.get("API_PORT", "8765")),
        reload=False,
        log_level="info",
    )
