from __future__ import annotations

from functools import lru_cache
from datetime import datetime
import json
from pathlib import Path
from typing import Any
import re


def _schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "intake-v1.schema.json"


@lru_cache(maxsize=1)
def load_intake_schema() -> dict[str, Any]:
    return json.loads(_schema_path().read_text(encoding="utf-8"))


def intake_properties() -> dict[str, dict[str, Any]]:
    return dict(load_intake_schema().get("properties", {}))


def intake_field_names() -> list[str]:
    return list(intake_properties().keys())


def required_intake_fields() -> list[str]:
    return list(load_intake_schema().get("required", []))


def intake_optional_defaults() -> dict[str, object]:
    defaults: dict[str, object] = {}
    for name, spec in intake_properties().items():
        if "default" in spec:
            defaults[name] = spec["default"]
        elif "null" in spec.get("type", []):
            defaults[name] = None
    return defaults


def normalized_intake_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(intake_optional_defaults())
    normalized.update(payload)
    return normalized


def missing_required_intake_fields(payload: dict[str, Any]) -> list[str]:
    normalized = normalized_intake_payload(payload)
    return [field for field in required_intake_fields() if normalized.get(field) in (None, "")]


def intake_field_errors(payload: dict[str, Any]) -> dict[str, str]:
    normalized = normalized_intake_payload(payload)
    errors: dict[str, str] = {}
    for name, spec in intake_properties().items():
        value = normalized.get(name)
        field_types = spec.get("type", [])
        if not isinstance(field_types, list):
            field_types = [field_types]
        if value is None:
            if "null" in field_types or name not in required_intake_fields():
                continue
            errors[name] = "missing"
            continue
        if "boolean" in field_types and isinstance(value, bool):
            continue
        if "string" in field_types:
            if not isinstance(value, str):
                errors[name] = "must be a string"
                continue
            if spec.get("minLength", 0) and len(value.strip()) < int(spec["minLength"]):
                errors[name] = f"must be at least {spec['minLength']} characters"
                continue
            if spec.get("enum") and value not in spec["enum"]:
                errors[name] = "must match an allowed value"
                continue
            field_format = spec.get("format")
            if field_format == "date" and not _is_valid_date(value):
                errors[name] = "must use YYYY-MM-DD"
                continue
            if field_format == "email" and value and not _is_valid_email(value):
                errors[name] = "must be a valid email address"
                continue
            continue
        errors[name] = "invalid type"
    return errors


def validate_intake_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = normalized_intake_payload(payload)
    allowed = set(intake_field_names())
    extras = sorted(key for key in normalized.keys() if key not in allowed)
    if extras:
        raise ValueError(f"Unexpected intake fields: {', '.join(extras)}")
    missing = missing_required_intake_fields(normalized)
    if missing:
        raise ValueError(f"Missing required intake fields: {', '.join(missing)}")
    errors = intake_field_errors(normalized)
    if errors:
        rendered = ", ".join(f"{name} ({reason})" for name, reason in errors.items())
        raise ValueError(f"Invalid intake fields: {rendered}")
    return {key: normalized.get(key) for key in intake_field_names()}


def _is_valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _is_valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value))
