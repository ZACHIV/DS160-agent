from __future__ import annotations

from dataclasses import fields
from pathlib import Path
import re
import unittest

from visa_agent.intake_contract import intake_field_names, required_intake_fields, validate_intake_payload
from visa_agent.intake import ApplicantIntake, build_dossier_from_intake
from visa_agent.vision_intake import VisionUploadedDocument, extract_intake_from_documents
import visa_agent.server as server_module
from visa_agent.server import (
    DraftBundleResponse,
    IntakePreviewRequest,
    FillPageRequest,
    get_draft_bundle,
    post_vision_prompt,
    post_vision_extract,
    post_vision_validate,
    VisionIntakeExtractRequest,
    VisionUploadedDocumentRequest,
    post_intake_document,
    post_intake_preview,
)


def sample_payload() -> dict[str, object]:
    return {
        "surname": "zhang",
        "given_names": "wei",
        "native_full_name": "张伟",
        "sex": "MALE",
        "marital_status": "MARRIED",
        "date_of_birth": "1990-08-15",
        "birth_city": "Shanghai",
        "passport_number": "e12345678",
        "passport_issue_date": "2023-05-12",
        "passport_expiration_date": "2033-05-11",
        "trip_purpose": "business_tourism",
        "intended_arrival_date": "2026-09-10",
        "intended_length_of_stay_value": "12",
        "intended_length_of_stay_unit": "DAYS",
        "payer_name": "Shanghai Example Trading Co., Ltd.",
        "us_contact_name": "Michael Chen",
        "us_contact_organization": "Example US Imports",
        "us_contact_phone": "+1 415 555 0187",
        "us_contact_address_line1": "500 Market Street",
        "us_contact_city": "San Francisco",
        "us_contact_state": "California",
        "us_contact_postal_code": "94105",
        "us_contact_email": "mchen@example.com",
        "primary_occupation": "BUSINESSPERSON",
        "current_employer_name": "Shanghai Example Trading Co., Ltd.",
        "current_employer_address": "88 Huaihai Middle Road, Shanghai, China",
        "father_full_name": "Zhang Jianguo",
        "mother_full_name": "Li Hua",
        "spouse_full_name": "Wang Li",
        "communicable_disease": False,
        "arrest_history": False,
    }


ROOT = Path(__file__).resolve().parents[1]
INTAKE_HTML = ROOT / "app" / "intake.html"
INTAKE_JS = ROOT / "app" / "intake.js"


class IntakeBuilderTests(unittest.TestCase):
    def test_builder_applies_china_defaults_and_normalization(self) -> None:
        dossier = build_dossier_from_intake(ApplicantIntake(**sample_payload()))
        self.assertEqual(dossier.identity.surname, "ZHANG")
        self.assertEqual(dossier.identity.given_names, "WEI")
        self.assertEqual(dossier.identity.birth_country, "CHINA")
        self.assertEqual(dossier.identity.nationality, "CHINA")
        self.assertEqual(dossier.identity.passport_issuance_country, "CHINA")
        self.assertEqual(dossier.travel_plan.visa_class, "B1/B2")
        self.assertEqual(dossier.travel_plan.us_contact_state, "CALIFORNIA")
        self.assertEqual(dossier.family_contacts.father_full_name, "ZHANG JIANGUO")
        self.assertEqual(dossier.security_background.yes_no_answers["arrest_history"], False)

    def test_contract_validates_and_normalizes_optional_fields(self) -> None:
        payload = sample_payload()
        payload["native_full_name"] = None
        validated = validate_intake_payload(payload)
        self.assertIn("us_contact_organization", validated)
        self.assertIn("spouse_full_name", validated)

    def test_applicant_intake_fields_match_schema_properties(self) -> None:
        dataclass_fields = [field.name for field in fields(ApplicantIntake)]
        self.assertEqual(dataclass_fields, intake_field_names())

    def test_manual_form_field_names_match_schema_properties(self) -> None:
        html = INTAKE_HTML.read_text(encoding="utf-8")
        manual_form_match = re.search(r'<form id="manual-form"[\s\S]+?</form>', html)
        self.assertIsNotNone(manual_form_match)
        form_names = re.findall(r'name="([^"]+)"', manual_form_match.group(0))
        form_names = [name for name in form_names if name not in {"communicable_disease", "arrest_history"}] + ["communicable_disease", "arrest_history"]
        unique_names: list[str] = []
        for name in form_names:
            if name not in unique_names:
                unique_names.append(name)
        self.assertEqual(unique_names, intake_field_names())

    def test_required_schema_fields_exist_in_manual_form(self) -> None:
        html = INTAKE_HTML.read_text(encoding="utf-8")
        for field_name in required_intake_fields():
            self.assertIn(f'name="{field_name}"', html)

    def test_manifest_cards_include_explicit_upload_trigger(self) -> None:
        script = INTAKE_JS.read_text(encoding="utf-8")
        self.assertIn("upload-trigger", script)
        self.assertIn("选择图片", script)

    def test_clipboard_copy_has_exec_command_fallback(self) -> None:
        script = INTAKE_JS.read_text(encoding="utf-8")
        self.assertIn("copyTextToClipboard", script)
        self.assertIn('document.execCommand("copy")', script)

    def test_static_page_has_local_manifest_and_prompt_fallbacks(self) -> None:
        script = INTAKE_JS.read_text(encoding="utf-8")
        self.assertIn("FALLBACK_VISION_MANIFEST", script)
        self.assertIn("FALLBACK_SCHEMA_DOCUMENT", script)
        self.assertIn("buildLocalPromptText", script)
        self.assertIn("已切换到离线模式", script)

    def test_invalid_enum_is_rejected_by_contract(self) -> None:
        payload = sample_payload()
        payload["trip_purpose"] = "unknown"
        with self.assertRaisesRegex(ValueError, "Invalid intake fields"):
            validate_intake_payload(payload)

    def test_invalid_date_is_rejected_by_contract(self) -> None:
        payload = sample_payload()
        payload["passport_issue_date"] = "2023/05/12"
        with self.assertRaisesRegex(ValueError, "Invalid intake fields"):
            validate_intake_payload(payload)

    def test_invalid_email_is_rejected_by_contract(self) -> None:
        payload = sample_payload()
        payload["us_contact_email"] = "invalid-email"
        with self.assertRaisesRegex(ValueError, "Invalid intake fields"):
            validate_intake_payload(payload)

    def test_request_model_rejects_extra_fields(self) -> None:
        with self.assertRaises(Exception):
            IntakePreviewRequest(**(sample_payload() | {"unexpected": "value"}))
        with self.assertRaises(Exception):
            FillPageRequest(page_id="travel_page", extra_field="value")


class IntakePreviewEndpointTests(unittest.TestCase):
    def tearDown(self) -> None:
        server_module.ACTIVE_INTAKE_DOCUMENT = None

    def test_preview_endpoint_returns_status_summary(self) -> None:
        payload = post_intake_preview(IntakePreviewRequest(**sample_payload())).model_dump()
        self.assertTrue(payload["ok"])
        self.assertGreater(payload["status_counts"]["ready"], 0)
        self.assertIn("travel.purpose_of_trip", {item["field_id"] for item in payload["review_items"]})
        self.assertEqual(payload["status_counts"]["blocked"], 0)
        self.assertEqual(payload["dossier"]["travel_plan"]["visa_class"], "B1/B2")

    def test_intake_document_becomes_single_source_for_draft_bundle(self) -> None:
        request = IntakePreviewRequest(**sample_payload())
        post_intake_document(request)
        response: DraftBundleResponse = get_draft_bundle()
        bundle = response.model_dump()["bundle"]
        self.assertEqual(bundle["case_id"], "INTAKE-LOCAL-001")
        self.assertIn("summary", bundle)
        self.assertIn("pages", bundle)
        self.assertGreater(len(bundle["pages"]), 0)


class VisionIntakeTests(unittest.TestCase):
    def test_prompt_endpoint_returns_copyable_text(self) -> None:
        payload = post_vision_prompt(
            VisionIntakeExtractRequest(
                documents=[
                    VisionUploadedDocumentRequest(
                        kind="passport_bio",
                        filename="passport.jpg",
                        media_type="image/jpeg",
                        base64_data="data:image/jpeg;base64,AAAA",
                    )
                ]
            )
        ).model_dump()
        self.assertTrue(payload["ok"])
        self.assertIn("passport.jpg", payload["prompt_text"])
        self.assertIn("目标 schema", payload["prompt_text"])

    def test_uploaded_images_can_build_complete_intake_json(self) -> None:
        def fake_extractor(documents, schema) -> dict[str, object]:
            return sample_payload()

        result = extract_intake_from_documents(
            [
                VisionUploadedDocument(kind=kind, filename=f"{kind}.jpg", media_type="image/jpeg", base64_data="data:image/jpeg;base64,AAAA")
                for kind in {
                    "passport_bio": "",
                    "trip_proof": "",
                    "us_contact_proof": "",
                    "employment_proof": "",
                    "family_info_sheet": "",
                    "security_questionnaire": "",
                }
            ],
            schema={"properties": {}, "required": []},
            model_extractor=fake_extractor,
        )
        self.assertEqual(result.missing_fields, [])
        self.assertIsNotNone(result.intake_document)
        self.assertEqual(result.intake_document["surname"], "zhang")
        self.assertEqual(result.intake_document["trip_purpose"], "business_tourism")
        self.assertEqual(result.intake_document["communicable_disease"], False)

    def test_partial_model_result_returns_missing_fields(self) -> None:
        result = extract_intake_from_documents(
            [
                VisionUploadedDocument(kind=kind, filename=f"{kind}.jpg", media_type="image/jpeg", base64_data="data:image/jpeg;base64,AAAA")
                for kind in {
                    "passport_bio": "",
                    "trip_proof": "",
                    "us_contact_proof": "",
                    "employment_proof": "",
                    "family_info_sheet": "",
                    "security_questionnaire": "",
                }
            ],
            schema={"properties": {}, "required": []},
            model_extractor=lambda documents, schema: {"surname": "ZHANG"},
        )
        self.assertIsNone(result.intake_document)
        self.assertIn("given_names", result.missing_fields)

    def test_document_reports_still_track_missing_uploads(self) -> None:
        result = extract_intake_from_documents(
            [
                VisionUploadedDocument(kind="passport_bio", filename="passport.jpg", media_type="image/jpeg", base64_data="data:image/jpeg;base64,AAAA")
            ],
            schema={"properties": {}, "required": []},
            model_extractor=lambda documents, schema: {"surname": "ZHANG"},
        )
        self.assertTrue(any(item.kind == "trip_proof" and item.status == "missing" for item in result.documents))

    def test_vision_endpoint_returns_missing_fields_when_model_result_is_incomplete(self) -> None:
        original = server_module.extract_intake_from_documents

        def fake_extract(documents, schema):
            return original(
                [VisionUploadedDocument(kind=item.kind, filename=item.filename, media_type=item.media_type, base64_data=item.base64_data) for item in documents],
                schema=schema,
                model_extractor=lambda documents, schema: {"surname": "ZHANG"},
            )

        server_module.extract_intake_from_documents = fake_extract
        try:
            payload = post_vision_extract(
                VisionIntakeExtractRequest(
                    documents=[
                        VisionUploadedDocumentRequest(
                            kind="passport_bio",
                            filename="passport.jpg",
                            media_type="image/jpeg",
                            base64_data="data:image/jpeg;base64,AAAA",
                        )
                    ]
                )
            ).model_dump()
        finally:
            server_module.extract_intake_from_documents = original

        self.assertTrue(payload["ok"])
        self.assertIsNone(payload["intake_document"])
        self.assertIn("given_names", payload["missing_fields"])

    def test_validate_endpoint_accepts_pasted_model_result(self) -> None:
        payload = post_vision_validate(type("Req", (), {"result": sample_payload()})()).model_dump()
        self.assertTrue(payload["ok"])
        self.assertIsNotNone(payload["intake_document"])
        self.assertEqual(payload["missing_fields"], [])


if __name__ == "__main__":
    unittest.main()
