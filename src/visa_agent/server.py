"""Local FastAPI server bridging the DS-160 assistant frontend to Chrome via CDP."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Allow running directly: python -m visa_agent.server
sys.path.insert(0, str(Path(__file__).parent.parent))

from visa_agent.browser.cdp_client import find_target_websocket_url, list_debug_targets
from visa_agent.browser.live_form_fill import (
    _PAGE_FILL_HANDLERS,
    detect_current_page,
    fill_current_supported_page,
    save_current_page,
)
from visa_agent.schema import load_dossier

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CDP_PORT = int(os.environ.get("CDP_PORT", "9222"))
DOSSIER_PATH = os.environ.get(
    "DOSSIER_PATH",
    str(Path(__file__).parent.parent.parent / "sample_data" / "china_b1b2_sample.json"),
)

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


class DetectPageResponse(BaseModel):
    page_key: str
    url: str
    title: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_dossier():
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
    _NORMALIZE = {
        "personal_page_1": "personal1",
        "personal_page_2": "personal2",
        "passport_page": "passport",
        "travel_page": "travel",
        "travel_companions_page": "travel_companions",
        "previous_travel_page": "previous_travel",
        "address_phone_page": "address_phone",
        "employment_page": "employment",
        "family_page": "family",
        "security_page": "security",
    }
    if page_id:
        canonical = _NORMALIZE.get(page_id, page_id)
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
