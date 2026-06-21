"""Browser driver boundary for DS-160 automation."""

from __future__ import annotations

from typing import Any, Protocol

from visa_agent.browser.cdp_client import list_debug_targets
from visa_agent.browser.live_form_fill import (
    _PAGE_FILL_HANDLERS,
    detect_current_page,
    extract_application_id,
    fill_and_continue,
    fill_current_supported_page,
)
from visa_agent.browser.visible_control import VisibleControlResult
from visa_agent.schema import ApplicantDossier


class BrowserDriver(Protocol):
    """Boundary between automation orchestration and concrete browser control."""

    def list_targets(self) -> list[dict[str, Any]]:
        ...

    def detect_current_page(self) -> dict[str, Any]:
        ...

    def detect_application_id(self) -> str | None:
        ...

    def supports_page(self, page_key: str) -> bool:
        ...

    def fill_page(self, page_key: str, dossier: ApplicantDossier) -> VisibleControlResult:
        ...

    def fill_and_continue(self, page_key: str, dossier: ApplicantDossier) -> dict[str, object]:
        ...


class CDPBrowserDriver:
    """Current Chrome DevTools Protocol implementation over legacy fill functions."""

    def __init__(self, cdp_port: int = 9222) -> None:
        self.cdp_port = cdp_port

    def list_targets(self) -> list[dict[str, Any]]:
        return list_debug_targets(port=self.cdp_port)

    def detect_current_page(self) -> dict[str, Any]:
        result = detect_current_page()
        return dict(result.payload)

    def detect_application_id(self) -> str | None:
        try:
            result = extract_application_id()
        except Exception:
            return None
        if result.ok:
            return str(result.payload.get("application_id") or "") or None
        return None

    def supports_page(self, page_key: str) -> bool:
        return page_key in _PAGE_FILL_HANDLERS

    def fill_page(self, page_key: str, dossier: ApplicantDossier) -> VisibleControlResult:
        handler = _PAGE_FILL_HANDLERS.get(page_key)
        if handler:
            return handler(dossier)
        return fill_current_supported_page(dossier)

    def fill_and_continue(self, page_key: str, dossier: ApplicantDossier) -> dict[str, object]:
        return fill_and_continue(page_key, dossier)
