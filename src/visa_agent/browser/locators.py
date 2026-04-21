from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class LocatorSpec:
    strategy: str
    target: str
    input_kind: str
    choice_labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


PAGE_LOCATORS: dict[str, dict[str, LocatorSpec]] = {
    "personal_page_1": {
        "identity_surname": LocatorSpec("label", "Surname", "text"),
        "identity_given_names": LocatorSpec("label", "Given Names", "text"),
        "identity_native_full_name": LocatorSpec("label", "Full Name in Native Alphabet", "text"),
        "identity_sex": LocatorSpec("label", "Sex", "select"),
        "identity_marital_status": LocatorSpec("label", "Marital Status", "select"),
        "identity_date_of_birth": LocatorSpec("label", "Date of Birth", "date"),
        "identity_birth_city": LocatorSpec("label", "City of Birth", "text"),
        "identity_birth_country": LocatorSpec("label", "Country/Region of Origin", "select"),
        "identity_nationality": LocatorSpec("label", "Nationality", "select"),
        "passport_number": LocatorSpec("label", "Passport/Travel Document Number", "text"),
        "passport_issue_date": LocatorSpec("label", "Issue Date", "date"),
        "passport_expiration_date": LocatorSpec("label", "Expiration Date", "date"),
    },
    "travel_page": {
        "travel_purpose_of_trip": LocatorSpec("label", "Purpose of Trip to the U.S.", "select"),
        "travel_intended_arrival_date": LocatorSpec("label", "Date of Arrival", "date"),
        "travel_intended_length_of_stay": LocatorSpec("label", "Length of Stay in U.S.", "text"),
        "travel_payer_name": LocatorSpec("label", "Person/Entity Paying for Your Trip", "text"),
        "travel_us_contact_name": LocatorSpec("label", "Contact Person Name in the U.S.", "text"),
        "travel_us_contact_phone": LocatorSpec("label", "U.S. Contact Phone Number", "text"),
    },
    "employment_page": {
        "employment_primary_occupation": LocatorSpec("label", "Primary Occupation", "select"),
        "employment_current_employer_name": LocatorSpec("label", "Present Employer or School Name", "text"),
    },
    "family_page": {
        "family_father_full_name": LocatorSpec("label", "Father's Full Name", "text"),
        "family_mother_full_name": LocatorSpec("label", "Mother's Full Name", "text"),
    },
    "security_page": {
        "security_communicable_disease": LocatorSpec(
            "label",
            "Do you have a communicable disease?",
            "radio",
            choice_labels={"true": "Yes", "false": "No"},
        ),
        "security_arrest_history": LocatorSpec(
            "label",
            "Have you ever been arrested or convicted?",
            "radio",
            choice_labels={"true": "Yes", "false": "No"},
        ),
    },
}


def resolve_locator(page_id: str, locator_key: str) -> LocatorSpec | None:
    return PAGE_LOCATORS.get(page_id, {}).get(locator_key)
