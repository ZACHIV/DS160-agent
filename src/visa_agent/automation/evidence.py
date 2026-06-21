"""Visual evidence storage for browser automation diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from pathlib import Path

from visa_agent.browser.cdp_client import capture_page_screenshot


def _safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "unknown"


def default_evidence_dir() -> Path:
    from visa_agent._paths import project_root

    return project_root().parent / ".ds160" / "visual-evidence"


@dataclass(frozen=True)
class VisualEvidence:
    kind: str
    label: str
    path: str


class VisualEvidenceStore:
    """Stores screenshots and other visual evidence for failed automation nodes."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or default_evidence_dir()

    def screenshot(self, ws_url: str, *, kind: str, label: str) -> VisualEvidence | None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"{timestamp}-{_safe_slug(label)}-{_safe_slug(kind)}.png"
        try:
            path = capture_page_screenshot(ws_url, self.root / filename)
        except Exception:
            return None
        return VisualEvidence(kind=kind, label=label, path=str(path))
