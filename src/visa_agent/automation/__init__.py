"""Automation core for DS-160 browser tasks."""

from visa_agent.automation.core import (
    AutomationError,
    BrowserUnavailableError,
    DS160AutomationCore,
    FillAndContinueOutcome,
    FillPageOutcome,
    PageDetectionError,
    UnsupportedPageError,
)
from visa_agent.automation.tasks import automation_task_catalog

__all__ = [
    "AutomationError",
    "BrowserUnavailableError",
    "DS160AutomationCore",
    "FillAndContinueOutcome",
    "FillPageOutcome",
    "PageDetectionError",
    "UnsupportedPageError",
    "automation_task_catalog",
]
