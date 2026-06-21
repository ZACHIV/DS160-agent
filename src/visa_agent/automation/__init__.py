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

__all__ = [
    "AutomationError",
    "BrowserUnavailableError",
    "DS160AutomationCore",
    "FillAndContinueOutcome",
    "FillPageOutcome",
    "PageDetectionError",
    "UnsupportedPageError",
]
