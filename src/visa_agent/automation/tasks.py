"""Automation task catalog exposed to UI and future resource files."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AutomationTask:
    name: str
    entry: str
    description: str
    default_check: bool = False
    repeatable: bool = False
    tags: list[str] = field(default_factory=list)
    pipeline_nodes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "entry": self.entry,
            "description": self.description,
            "default_check": self.default_check,
            "repeatable": self.repeatable,
            "tags": list(self.tags),
            "pipeline_nodes": list(self.pipeline_nodes),
        }


TASK_CATALOG: tuple[AutomationTask, ...] = (
    AutomationTask(
        name="Fill Current Page",
        entry="fill_page",
        description="Fill the detected or selected DS-160 page and record audit/checkpoint metadata.",
        default_check=True,
        tags=["browser", "fill"],
        pipeline_nodes=["check_browser", "resolve_page", "fill_page", "record_fill"],
    ),
    AutomationTask(
        name="Fill And Continue",
        entry="fill_and_continue",
        description="Fill the current DS-160 page, save progress, and advance to the next page.",
        tags=["browser", "fill", "navigation"],
        pipeline_nodes=[
            "check_browser",
            "resolve_page",
            "ensure_supported",
            "fill_continue",
            "save_checkpoint",
            "record_fill",
        ],
    ),
    AutomationTask(
        name="Check DOM Drift",
        entry="dom_drift",
        description="Check representative selectors on the current page and save visual evidence when drift is unhealthy.",
        tags=["diagnostics", "visual-evidence"],
        pipeline_nodes=["detect_page", "check_selectors", "capture_evidence_on_warning"],
    ),
)


def automation_task_catalog() -> list[dict[str, Any]]:
    return [task.to_dict() for task in TASK_CATALOG]
