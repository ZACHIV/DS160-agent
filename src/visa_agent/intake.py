from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from visa_agent.intake_contract import validate_intake_payload
from visa_agent.schema import (
    ApplicantDossier,
    ApplicantIdentity,
    EmploymentEducation,
    FamilyContacts,
    SecurityBackground,
    TravelPlan,
)


DEFAULT_SOURCE_IDS = ["intake:web-form"]


@dataclass(frozen=True)
class ApplicantIntake:
    surname: str
    given_names: str
    native_full_name: str | None
    sex: str
    marital_status: str
    date_of_birth: str
    birth_city: str
    passport_number: str
    passport_issue_date: str
    passport_expiration_date: str
    trip_purpose: str
    intended_arrival_date: str
    intended_length_of_stay_value: str
    intended_length_of_stay_unit: str
    payer_name: str
    us_contact_name: str
    us_contact_organization: str | None
    us_contact_phone: str
    us_contact_address_line1: str
    us_contact_city: str
    us_contact_state: str
    us_contact_postal_code: str
    us_contact_email: str | None
    primary_occupation: str
    current_employer_name: str
    current_employer_address: str
    father_full_name: str
    mother_full_name: str
    spouse_full_name: str | None
    communicable_disease: bool
    arrest_history: bool


def load_intake_document(path: str | Path) -> ApplicantIntake:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return ApplicantIntake(**validate_intake_payload(raw))


def intake_to_dict(intake: ApplicantIntake) -> dict[str, object]:
    return asdict(intake)


def _normalized_optional(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _normalized_required(value: str) -> str:
    return value.strip()


def _purpose_notes(trip_purpose: str) -> str:
    purpose = trip_purpose.strip()
    purpose_map = {
        "tourism": "Tourism and personal travel in the United States.",
        "business": "Short business visit including meetings or partner discussions.",
        "business_tourism": "Attend business meetings and combine with short tourism.",
        "family_visit": "Visit family or friends in the United States.",
    }
    return purpose_map.get(purpose, purpose or "B1/B2 travel purpose needs operator review.")


def build_dossier_from_intake(intake: ApplicantIntake) -> ApplicantDossier:
    identity = ApplicantIdentity(
        surname=_normalized_required(intake.surname).upper(),
        given_names=_normalized_required(intake.given_names).upper(),
        native_full_name=_normalized_optional(intake.native_full_name),
        sex=_normalized_required(intake.sex).upper(),
        marital_status=_normalized_required(intake.marital_status).upper(),
        date_of_birth=_normalized_required(intake.date_of_birth),
        birth_city=_normalized_required(intake.birth_city).upper(),
        birth_province=None,
        birth_country="CHINA",
        nationality="CHINA",
        passport_number=_normalized_required(intake.passport_number).upper(),
        passport_issuance_country="CHINA",
        passport_issue_date=_normalized_required(intake.passport_issue_date),
        passport_expiration_date=_normalized_required(intake.passport_expiration_date),
        passport_book_number=None,
        source_ids=list(DEFAULT_SOURCE_IDS),
    )
    travel_plan = TravelPlan(
        visa_class="B1/B2",
        purpose_notes=_purpose_notes(intake.trip_purpose),
        intended_arrival_date=_normalized_required(intake.intended_arrival_date),
        intended_length_of_stay_value=_normalized_required(intake.intended_length_of_stay_value),
        intended_length_of_stay_unit=_normalized_required(intake.intended_length_of_stay_unit).upper(),
        payer_name=_normalized_required(intake.payer_name),
        us_contact_name=_normalized_required(intake.us_contact_name),
        us_contact_organization=_normalized_optional(intake.us_contact_organization),
        us_contact_address_line1=_normalized_required(intake.us_contact_address_line1),
        us_contact_city=_normalized_required(intake.us_contact_city),
        us_contact_state=_normalized_required(intake.us_contact_state).upper(),
        us_contact_postal_code=_normalized_required(intake.us_contact_postal_code),
        us_contact_phone=_normalized_required(intake.us_contact_phone),
        us_contact_email=_normalized_optional(intake.us_contact_email),
        source_ids=list(DEFAULT_SOURCE_IDS),
    )
    employment_education = EmploymentEducation(
        primary_occupation=_normalized_required(intake.primary_occupation).upper(),
        current_employer_name=_normalized_required(intake.current_employer_name),
        current_employer_address=_normalized_required(intake.current_employer_address),
        monthly_income_local=None,
        school_name=None,
        source_ids=list(DEFAULT_SOURCE_IDS),
    )
    family_contacts = FamilyContacts(
        father_full_name=_normalized_required(intake.father_full_name).upper(),
        mother_full_name=_normalized_required(intake.mother_full_name).upper(),
        spouse_full_name=_normalized_optional(intake.spouse_full_name.upper() if intake.spouse_full_name else None),
        us_relative_name=None,
        us_relative_status=None,
        source_ids=list(DEFAULT_SOURCE_IDS),
    )
    security_background = SecurityBackground(
        yes_no_answers={
            "communicable_disease": intake.communicable_disease,
            "arrest_history": intake.arrest_history,
        },
        explanations={},
        source_ids=list(DEFAULT_SOURCE_IDS),
    )
    return ApplicantDossier(
        case_id="INTAKE-LOCAL-001",
        identity=identity,
        travel_plan=travel_plan,
        employment_education=employment_education,
        family_contacts=family_contacts,
        security_background=security_background,
        evidence_catalog={},
    )


def dossier_to_dict(dossier: ApplicantDossier) -> dict[str, object]:
    payload = asdict(dossier)
    payload["evidence_catalog"] = list(payload["evidence_catalog"].values())
    return payload


def intake_payload_to_dossier(payload: dict[str, Any]) -> ApplicantDossier:
    return build_dossier_from_intake(ApplicantIntake(**validate_intake_payload(payload)))
