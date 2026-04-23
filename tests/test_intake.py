from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

from visa_agent.dossier_contract import load_dossier_schema, missing_required_dossier_fields, validate_dossier_payload
from visa_agent.vision_intake import VisionUploadedDocument, extract_dossier_from_documents

try:
    import visa_agent.server as server_module
    from visa_agent.server import (
        DraftBundleResponse,
        FillPageRequest,
        VisionIntakeExtractRequest,
        VisionUploadedDocumentRequest,
        post_dossier_document,
        post_dossier_preview,
        post_vision_extract,
        post_vision_prompt,
        post_vision_validate,
        get_draft_bundle,
    )
    SERVER_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment-dependent
    server_module = None
    DraftBundleResponse = None
    FillPageRequest = None
    VisionIntakeExtractRequest = None
    VisionUploadedDocumentRequest = None
    post_dossier_document = None
    post_dossier_preview = None
    post_vision_extract = None
    post_vision_prompt = None
    post_vision_validate = None
    get_draft_bundle = None
    SERVER_IMPORT_ERROR = exc


ROOT = Path(__file__).resolve().parents[1]
INTAKE_HTML = ROOT / "app" / "intake.html"
INTAKE_JS = ROOT / "app" / "intake.js"
FULL_DOSSIER_SAMPLE = ROOT / "sample_data" / "china_b1b2_sample.json"


def sample_dossier() -> dict[str, object]:
    return json.loads(FULL_DOSSIER_SAMPLE.read_text(encoding="utf-8"))


class DossierContractTests(unittest.TestCase):
    def test_full_dossier_sample_validates(self) -> None:
        validated = validate_dossier_payload(sample_dossier())
        self.assertEqual(validated["case_id"], "CN-B1B2-001")
        self.assertEqual(validated["identity"]["surname"], "ZHANG")

    def test_missing_required_path_is_reported(self) -> None:
        payload = sample_dossier()
        del payload["identity"]["surname"]
        missing = missing_required_dossier_fields(payload)
        self.assertIn("identity.surname", missing)

    def test_manual_form_contains_full_dossier_paths(self) -> None:
        html = INTAKE_HTML.read_text(encoding="utf-8")
        manual_form_match = re.search(r'<form id="manual-form"[\s\S]+?</form>', html)
        self.assertIsNotNone(manual_form_match)
        form_names = re.findall(r'name="([^"]+)"', manual_form_match.group(0))
        self.assertIn("case_id", form_names)
        self.assertIn("identity.birth_province", form_names)
        self.assertIn("employment_education.monthly_income_local", form_names)
        self.assertIn("security_background.explanations", form_names)
        self.assertIn("evidence_catalog", form_names)

    def test_static_page_uses_dossier_schema_and_export(self) -> None:
        script = INTAKE_JS.read_text(encoding="utf-8")
        self.assertIn("dossier.schema.json", script)
        self.assertIn("/dossier-schema", script)
        self.assertIn("/dossier/preview", script)
        self.assertIn("china-b1b2-dossier.json", script)
        self.assertIn("完整 dossier JSON 对象", script)

    def test_clipboard_copy_has_exec_command_fallback(self) -> None:
        script = INTAKE_JS.read_text(encoding="utf-8")
        self.assertIn("copyTextToClipboard", script)
        self.assertIn('document.execCommand("copy")', script)

    def test_manifest_cards_include_explicit_upload_trigger(self) -> None:
        script = INTAKE_JS.read_text(encoding="utf-8")
        self.assertIn("upload-trigger", script)
        self.assertIn("选择图片", script)

    def test_request_model_rejects_extra_fields(self) -> None:
        if FillPageRequest is None:
            self.skipTest(f"server dependencies unavailable: {SERVER_IMPORT_ERROR}")
        with self.assertRaises(Exception):
            FillPageRequest(page_id="travel_page", extra_field="value")


@unittest.skipIf(server_module is None, f"server dependencies unavailable: {SERVER_IMPORT_ERROR}")
class DossierPreviewEndpointTests(unittest.TestCase):
    def tearDown(self) -> None:
        server_module.ACTIVE_DOSSIER_DOCUMENT = None

    def test_preview_endpoint_returns_status_summary(self) -> None:
        payload = post_dossier_preview(sample_dossier()).model_dump()
        self.assertTrue(payload["ok"])
        self.assertGreater(payload["status_counts"]["ready"], 0)
        self.assertEqual(payload["dossier"]["travel_plan"]["visa_class"], "B1/B2")

    def test_dossier_document_becomes_single_source_for_draft_bundle(self) -> None:
        post_dossier_document(sample_dossier())
        response: DraftBundleResponse = get_draft_bundle()
        bundle = response.model_dump()["bundle"]
        self.assertEqual(bundle["case_id"], "CN-B1B2-001")
        self.assertIn("summary", bundle)
        self.assertGreater(len(bundle["pages"]), 0)


class VisionDossierTests(unittest.TestCase):
    def test_prompt_endpoint_returns_copyable_text(self) -> None:
        if post_vision_prompt is None:
            self.skipTest(f"server dependencies unavailable: {SERVER_IMPORT_ERROR}")
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

    def test_uploaded_images_can_build_complete_dossier_json(self) -> None:
        def fake_extractor(documents, schema) -> dict[str, object]:
            return sample_dossier()

        result = extract_dossier_from_documents(
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
            schema=load_dossier_schema(),
            model_extractor=fake_extractor,
        )
        self.assertEqual(result.missing_fields, [])
        self.assertIsNotNone(result.dossier_document)
        self.assertEqual(result.dossier_document["identity"]["surname"], "ZHANG")

    def test_partial_model_result_returns_missing_fields(self) -> None:
        result = extract_dossier_from_documents(
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
            schema=load_dossier_schema(),
            model_extractor=lambda documents, schema: {"case_id": "X"},
        )
        self.assertIsNone(result.dossier_document)
        self.assertIn("identity", result.missing_fields)

    def test_vision_endpoint_returns_missing_fields_when_model_result_is_incomplete(self) -> None:
        if server_module is None:
            self.skipTest(f"server dependencies unavailable: {SERVER_IMPORT_ERROR}")
        original = server_module.extract_dossier_from_documents

        def fake_extract(documents, schema):
            return original(
                [VisionUploadedDocument(kind=item.kind, filename=item.filename, media_type=item.media_type, base64_data=item.base64_data) for item in documents],
                schema=schema,
                model_extractor=lambda documents, schema: {"case_id": "X"},
            )

        server_module.extract_dossier_from_documents = fake_extract
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
            server_module.extract_dossier_from_documents = original

        self.assertTrue(payload["ok"])
        self.assertIsNone(payload["dossier_document"])
        self.assertIn("identity", payload["missing_fields"])

    def test_validate_endpoint_accepts_pasted_model_result(self) -> None:
        if post_vision_validate is None:
            self.skipTest(f"server dependencies unavailable: {SERVER_IMPORT_ERROR}")
        payload = post_vision_validate(type("Req", (), {"result": sample_dossier()})()).model_dump()
        self.assertTrue(payload["ok"])
        self.assertIsNotNone(payload["dossier_document"])
        self.assertEqual(payload["missing_fields"], [])


if __name__ == "__main__":
    unittest.main()
