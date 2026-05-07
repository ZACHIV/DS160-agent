"""Declarative page and field definitions for DS-160 form filling.

Centralizes all hardcoded selectors into auditable data structures,
separating the "what" (selectors, field mappings) from the "how" (CDP execution).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from visa_agent.schema import ApplicantDossier

# Resolver: takes dossier, returns the value to fill (or None if field should be skipped)
Resolver = Callable[[ApplicantDossier], str | bool | None]

# Condition: takes dossier, returns True if this field should be filled
Condition = Callable[[ApplicantDossier], bool]


@dataclass(frozen=True)
class FieldBinding:
    """A single form-field-to-dossier binding.

    Exactly one value source is used, in priority order:
    1. resolver (custom function)
    2. source_path (dotted path into ApplicantDossier)
    3. hardcoded (literal constant)
    """

    field_id: str  # Logical name, e.g. "identity_surname"
    selector: str  # CSS selector or [name="...$..."] radio name
    input_kind: str  # "text" | "select_value" | "select_text" | "radio_click" | "radio" | "checkbox"

    # Value source (one of these three)
    source_path: str | None = None  # e.g. "identity.surname"
    hardcoded: str | bool | None = None  # Literal constant
    resolver: Resolver | None = None  # Custom (dossier) -> value

    # For radio inputs: the value attribute to select (e.g. 'Y', 'N', 'REGULAR')
    choice_value: str | None = None

    # For select_text: alternative fallback path for partial match
    alt_source_path: str | None = None

    # If condition returns False, this field is skipped
    condition: Condition | None = None

    # After filling, wait for this selector to appear (used for dependent fields)
    wait_selector_after: str | None = None

    # Verify the filled value by reading back from DOM
    verify: bool = False
    verify_selector: str | None = None  # If different from main selector


@dataclass(frozen=True)
class FillPhase:
    """A group of fields filled in a single CDP round-trip."""

    fields: list[FieldBinding]
    wait_before_ms: int = 0  # Wait before executing this phase
    label: str = ""  # Human-readable label for debugging


@dataclass(frozen=True)
class PageDefinition:
    """Complete declarative definition of a DS-160 form page."""

    page_key: str  # e.g. "personal1"
    url_matchers: list[str]  # URL substrings or "node=..." values
    phases: list[FillPhase]
    save_checkpoint: bool = False  # Auto-save after this page
