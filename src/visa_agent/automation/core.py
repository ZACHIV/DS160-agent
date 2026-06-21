"""Clean DS-160 automation orchestration over the browser fill engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from visa_agent.audit_log import log_page_fill
from visa_agent.browser.cdp_client import list_debug_targets
from visa_agent.browser.live_form_fill import (
    _PAGE_FILL_HANDLERS,
    detect_current_page,
    extract_application_id,
    fill_and_continue,
    fill_current_supported_page,
)
from visa_agent.checkpoint import (
    FillCheckpoint,
    checkpoint_workspace,
    load_checkpoint,
    save_checkpoint,
)
from visa_agent.page_ids import PAGE_ID_NORMALIZE, bundle_page_id
from visa_agent.schema import ApplicantDossier
from visa_agent.automation.pipeline import PipelineEvent, PipelineNode, TaskPipeline


class AutomationError(RuntimeError):
    """Base error for browser automation orchestration."""


class BrowserUnavailableError(AutomationError):
    """Raised when the Chrome DevTools endpoint cannot be reached."""


class PageDetectionError(AutomationError):
    """Raised when the current CEAC page cannot be detected."""


class UnsupportedPageError(AutomationError):
    """Raised when a detected page has no fill handler."""


@dataclass(frozen=True)
class FillPageOutcome:
    ok: bool
    page_key: str
    filled: list[str]
    missing: list[str]
    application_id: str | None = None
    pipeline_events: list[PipelineEvent] = field(default_factory=list)


@dataclass(frozen=True)
class FillAndContinueOutcome:
    ok: bool
    page_key: str
    new_page_key: str | None
    filled: list[str]
    missing: list[str]
    application_id: str | None = None
    pipeline_events: list[PipelineEvent] = field(default_factory=list)


class DS160AutomationCore:
    """Coordinates DS-160 fill tasks without HTTP or frontend concerns."""

    def __init__(self, cdp_port: int = 9222) -> None:
        self.cdp_port = cdp_port

    def fill_page(
        self,
        dossier: ApplicantDossier,
        requested_page_id: str | None = None,
    ) -> FillPageOutcome:
        context: dict[str, Any] = {
            "dossier": dossier,
            "requested_page_id": requested_page_id,
        }
        result = TaskPipeline(self._fill_page_nodes()).run("check_browser", context)
        if not result.completed:
            self._raise_pipeline_error(result.error)
        return FillPageOutcome(
            ok=bool(result.context["fill_ok"]),
            page_key=str(result.context["page_key"]),
            filled=list(result.context["filled"]),
            missing=list(result.context["missing"]),
            application_id=result.context.get("application_id"),
            pipeline_events=result.events,
        )

    def fill_current_page_and_continue(
        self,
        dossier: ApplicantDossier,
        requested_page_id: str | None = None,
    ) -> FillAndContinueOutcome:
        context: dict[str, Any] = {
            "dossier": dossier,
            "requested_page_id": requested_page_id,
        }
        result = TaskPipeline(self._fill_continue_nodes()).run("check_browser", context)
        if not result.completed:
            self._raise_pipeline_error(result.error)
        return FillAndContinueOutcome(
            ok=bool(result.context["fill_ok"] and result.context["next_ok"]),
            page_key=str(result.context["page_key"]),
            new_page_key=result.context.get("new_page_key"),
            filled=list(result.context["filled"]),
            missing=list(result.context["missing"]),
            application_id=result.context.get("application_id"),
            pipeline_events=result.events,
        )

    def detect_application_id(self) -> str | None:
        try:
            result = extract_application_id()
        except Exception:
            return None
        if result.ok:
            return str(result.payload.get("application_id") or "") or None
        return None

    def save_detected_application_id(
        self,
        dossier: ApplicantDossier,
        application_id: str | None,
        current_page_key: str | None = None,
    ) -> None:
        if not application_id:
            return
        try:
            existing = load_checkpoint(checkpoint_workspace())
            checkpoint = FillCheckpoint(
                case_id=dossier.case_id,
                application_id=application_id,
                completed_pages=list(existing.completed_pages) if existing else [],
                current_page_key=current_page_key or (existing.current_page_key if existing else None),
            )
            save_checkpoint(checkpoint, checkpoint_workspace())
        except Exception:
            pass

    def _fill_page_nodes(self) -> dict[str, PipelineNode]:
        return {
            "check_browser": PipelineNode("check_browser", action=self._check_browser, next=["resolve_page"]),
            "resolve_page": PipelineNode("resolve_page", action=self._resolve_page, next=["fill_page"]),
            "fill_page": PipelineNode("fill_page", action=self._fill_page_action, next=["record_fill"]),
            "record_fill": PipelineNode("record_fill", action=self._record_fill),
        }

    def _fill_continue_nodes(self) -> dict[str, PipelineNode]:
        return {
            "check_browser": PipelineNode("check_browser", action=self._check_browser, next=["resolve_page"]),
            "resolve_page": PipelineNode("resolve_page", action=self._resolve_page, next=["ensure_supported"]),
            "ensure_supported": PipelineNode(
                "ensure_supported",
                recognition=lambda ctx: str(ctx.get("page_key") or "") in _PAGE_FILL_HANDLERS,
                next=["fill_continue"],
            ),
            "fill_continue": PipelineNode("fill_continue", action=self._fill_continue_action, next=["save_checkpoint"]),
            "save_checkpoint": PipelineNode("save_checkpoint", action=self._save_fill_continue_checkpoint, next=["record_fill"]),
            "record_fill": PipelineNode("record_fill", action=self._record_fill),
        }

    def _check_browser(self, context: dict[str, Any]) -> dict[str, Any]:
        try:
            tabs = list_debug_targets(port=self.cdp_port)
        except Exception as exc:
            raise BrowserUnavailableError(
                "Chrome not reachable on CDP port. Launch Chrome with --remote-debugging-port=9222"
            ) from exc
        if not tabs:
            raise BrowserUnavailableError(
                "Chrome not reachable on CDP port. Launch Chrome with --remote-debugging-port=9222"
            )
        return {"open_tabs": tabs}

    def _resolve_page(self, context: dict[str, Any]) -> dict[str, Any]:
        requested = context.get("requested_page_id")
        if requested:
            return {"page_key": PAGE_ID_NORMALIZE.get(str(requested), str(requested))}

        try:
            detected = detect_current_page()
        except Exception as exc:
            raise PageDetectionError(f"Cannot detect current page: {exc}") from exc

        page_key = detected.payload.get("page_key")
        if not page_key:
            raise PageDetectionError("Cannot detect current page.")
        return {"page_key": page_key}

    def _fill_page_action(self, context: dict[str, Any]) -> dict[str, Any]:
        dossier: ApplicantDossier = context["dossier"]
        page_key = str(context.get("page_key") or "")
        handler = _PAGE_FILL_HANDLERS.get(page_key)
        result = handler(dossier) if handler else fill_current_supported_page(dossier)

        filled = list(result.payload.get("filled") or [])
        missing = list(result.payload.get("missing") or [])
        result_page_key = page_key or result.payload.get("page_key", "unsupported")
        application_id = self.detect_application_id()
        current_page_key = bundle_page_id(str(result_page_key)) or str(result_page_key)
        self.save_detected_application_id(dossier, application_id, current_page_key=current_page_key)
        return {
            "fill_ok": result.ok,
            "page_key": result_page_key,
            "filled": filled,
            "missing": missing,
            "application_id": application_id,
        }

    def _fill_continue_action(self, context: dict[str, Any]) -> dict[str, Any]:
        dossier: ApplicantDossier = context["dossier"]
        page_key = str(context["page_key"])
        result = fill_and_continue(page_key, dossier)
        fill_payload = result.get("fill_payload") or {}
        raw_new_key = result.get("new_page_key")
        new_page_key = bundle_page_id(str(raw_new_key)) if raw_new_key else None
        application_id = result.get("application_id") or self.detect_application_id()
        return {
            "fill_ok": bool(result.get("fill_ok")),
            "next_ok": bool(result.get("next_ok")),
            "filled": list(fill_payload.get("filled") or []),
            "missing": list(fill_payload.get("missing") or []),
            "new_page_key": new_page_key,
            "raw_new_page_key": raw_new_key,
            "application_id": application_id,
        }

    def _save_fill_continue_checkpoint(self, context: dict[str, Any]) -> dict[str, Any]:
        if not context.get("fill_ok"):
            return {}

        dossier: ApplicantDossier = context["dossier"]
        page_key = str(context["page_key"])
        application_id = context.get("application_id")
        raw_new_key = context.get("raw_new_page_key")
        new_page_key = context.get("new_page_key")
        try:
            existing = load_checkpoint(checkpoint_workspace())
            completed = list(existing.completed_pages) if existing else []
            if page_key not in completed:
                completed.append(page_key)
            checkpoint = FillCheckpoint(
                case_id=dossier.case_id,
                application_id=application_id or (existing.application_id if existing else None),
                completed_pages=completed,
                current_page_key=new_page_key or raw_new_key,
            )
            save_checkpoint(checkpoint, checkpoint_workspace())
        except Exception:
            pass
        return {}

    def _record_fill(self, context: dict[str, Any]) -> dict[str, Any]:
        dossier: ApplicantDossier = context["dossier"]
        page_key = str(context.get("page_key") or "unsupported")
        filled = list(context.get("filled") or [])
        missing = list(context.get("missing") or [])
        ok = bool(context.get("fill_ok"))
        log_page_fill(
            dossier.case_id,
            page_key,
            len(filled),
            len(missing),
            application_id=context.get("application_id"),
            ok=ok,
        )
        return {}

    def _raise_pipeline_error(self, error: str | None) -> None:
        if error and "Chrome not reachable" in error:
            raise BrowserUnavailableError(error)
        if error == "RECOGNITION_MISSED":
            raise UnsupportedPageError("No fill handler for current page")
        if error and error.startswith("Cannot detect current page"):
            raise PageDetectionError(error)
        raise AutomationError(error or "Automation pipeline failed")
