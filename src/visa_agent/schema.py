from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ApplicantIdentity:
    surname: str
    given_names: str
    native_full_name: str | None
    sex: str
    marital_status: str
    date_of_birth: str
    birth_city: str
    birth_province: str | None
    birth_country: str
    nationality: str
    passport_number: str
    passport_issuance_country: str
    passport_issue_date: str
    passport_expiration_date: str
    passport_book_number: str | None
    source_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TravelPlan:
    visa_class: str
    purpose_notes: str | None
    intended_arrival_date: str | None
    intended_length_of_stay_value: str | None
    intended_length_of_stay_unit: str | None
    payer_name: str | None
    us_contact_name: str | None
    us_contact_organization: str | None
    us_contact_address_line1: str | None
    us_contact_city: str | None
    us_contact_state: str | None
    us_contact_postal_code: str | None
    us_contact_phone: str | None
    us_contact_email: str | None
    source_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EmploymentEducation:
    primary_occupation: str | None
    current_employer_name: str | None
    current_employer_address: str | None
    monthly_income_local: str | None
    school_name: str | None
    source_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FamilyContacts:
    father_full_name: str | None
    mother_full_name: str | None
    spouse_full_name: str | None
    us_relative_name: str | None
    us_relative_status: str | None
    source_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SecurityBackground:
    yes_no_answers: dict[str, bool]
    explanations: dict[str, str]
    source_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    kind: str
    description: str


@dataclass(frozen=True)
class ApplicantDossier:
    case_id: str
    identity: ApplicantIdentity
    travel_plan: TravelPlan
    employment_education: EmploymentEducation
    family_contacts: FamilyContacts
    security_background: SecurityBackground
    evidence_catalog: dict[str, EvidenceItem]


def _load_identity(payload: dict[str, Any]) -> ApplicantIdentity:
    return ApplicantIdentity(
        surname=payload["surname"],
        given_names=payload["given_names"],
        native_full_name=payload.get("native_full_name"),
        sex=payload["sex"],
        marital_status=payload["marital_status"],
        date_of_birth=payload["date_of_birth"],
        birth_city=payload["birth_city"],
        birth_province=payload.get("birth_province"),
        birth_country=payload["birth_country"],
        nationality=payload["nationality"],
        passport_number=payload["passport_number"],
        passport_issuance_country=payload["passport_issuance_country"],
        passport_issue_date=payload["passport_issue_date"],
        passport_expiration_date=payload["passport_expiration_date"],
        passport_book_number=payload.get("passport_book_number"),
        source_ids=list(payload.get("source_ids", [])),
    )


def _load_travel_plan(payload: dict[str, Any]) -> TravelPlan:
    return TravelPlan(
        visa_class=payload["visa_class"],
        purpose_notes=payload.get("purpose_notes"),
        intended_arrival_date=payload.get("intended_arrival_date"),
        intended_length_of_stay_value=payload.get("intended_length_of_stay_value"),
        intended_length_of_stay_unit=payload.get("intended_length_of_stay_unit"),
        payer_name=payload.get("payer_name"),
        us_contact_name=payload.get("us_contact_name"),
        us_contact_organization=payload.get("us_contact_organization"),
        us_contact_address_line1=payload.get("us_contact_address_line1"),
        us_contact_city=payload.get("us_contact_city"),
        us_contact_state=payload.get("us_contact_state"),
        us_contact_postal_code=payload.get("us_contact_postal_code"),
        us_contact_phone=payload.get("us_contact_phone"),
        us_contact_email=payload.get("us_contact_email"),
        source_ids=list(payload.get("source_ids", [])),
    )


def _load_employment(payload: dict[str, Any]) -> EmploymentEducation:
    return EmploymentEducation(
        primary_occupation=payload.get("primary_occupation"),
        current_employer_name=payload.get("current_employer_name"),
        current_employer_address=payload.get("current_employer_address"),
        monthly_income_local=payload.get("monthly_income_local"),
        school_name=payload.get("school_name"),
        source_ids=list(payload.get("source_ids", [])),
    )


def _load_family(payload: dict[str, Any]) -> FamilyContacts:
    return FamilyContacts(
        father_full_name=payload.get("father_full_name"),
        mother_full_name=payload.get("mother_full_name"),
        spouse_full_name=payload.get("spouse_full_name"),
        us_relative_name=payload.get("us_relative_name"),
        us_relative_status=payload.get("us_relative_status"),
        source_ids=list(payload.get("source_ids", [])),
    )


def _load_security(payload: dict[str, Any]) -> SecurityBackground:
    return SecurityBackground(
        yes_no_answers=dict(payload.get("yes_no_answers", {})),
        explanations=dict(payload.get("explanations", {})),
        source_ids=list(payload.get("source_ids", [])),
    )


def load_dossier(path: str | Path) -> ApplicantDossier:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return load_dossier_payload(raw)


def load_dossier_payload(raw: dict[str, Any]) -> ApplicantDossier:
    evidence_catalog = {
        item["id"]: EvidenceItem(
            id=item["id"],
            kind=item["kind"],
            description=item["description"],
        )
        for item in raw.get("evidence_catalog", [])
    }
    return ApplicantDossier(
        case_id=raw["case_id"],
        identity=_load_identity(raw["identity"]),
        travel_plan=_load_travel_plan(raw["travel_plan"]),
        employment_education=_load_employment(raw["employment_education"]),
        family_contacts=_load_family(raw["family_contacts"]),
        security_background=_load_security(raw["security_background"]),
        evidence_catalog=evidence_catalog,
    )
