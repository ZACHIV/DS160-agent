"""Tests for the refactored live_form_fill module and fill engine."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

from visa_agent.schema import PreviousTravelInfo, load_dossier
from visa_agent.browser.live_form_fill import (
    PAGE_MATCHERS,
    PREVIOUS_TRAVEL_URL_SUBSTRING,
    _detect_page_key,
    _PAGE_FILL_HANDLERS,
    click_next_and_wait,
    detect_current_page,
    extract_application_id,
    fill_current_supported_page,
)
from visa_agent.browser.page_definitions import (
    PAGE_REGISTRY,
    _month_abbrev,
    _sanitize_name,
    _normalize_phone,
    _split_surname_given,
    _split_first_surname,
    _los_unit_label,
    _departure_date,
    _us_contact_relationship,
    _visa_type_value,
    _travel_purpose_value,
)
from visa_agent.browser.fill_engine import (
    _should_fill,
    _generate_fill_js,
    _resolve_value,
)
from visa_agent.browser.page_spec import FieldBinding
from visa_agent.page_ids import PAGE_ID_NORMALIZE


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = ROOT / "sample_data" / "china_b1b2_sample.json"


class HelperFunctionTests(unittest.TestCase):
    """Pure-function tests for helpers now in page_definitions.py."""

    def test_month_abbrev_mapping(self) -> None:
        self.assertEqual(_month_abbrev("08"), "AUG")
        self.assertEqual(_month_abbrev("01"), "JAN")
        self.assertEqual(_month_abbrev("12"), "DEC")

    def test_sanitize_name_removes_punctuation(self) -> None:
        self.assertEqual(
            _sanitize_name("Shanghai Example Trading Co., Ltd."),
            "SHANGHAI EXAMPLE TRADING CO LTD"
        )

    def test_normalize_phone_keeps_only_digits(self) -> None:
        self.assertEqual(_normalize_phone("+86-21-5555-8800"), "862155558800")
        self.assertEqual(_normalize_phone(None, "999"), "999")

    def test_split_surname_given_treats_last_token_as_surname(self) -> None:
        self.assertEqual(_split_surname_given("Michael Chen"), ("Chen", "Michael"))

    def test_split_first_surname_keeps_first_token_as_surname(self) -> None:
        self.assertEqual(_split_first_surname("ZHANG JIANGUO"), ("ZHANG", "JIANGUO"))

    def test_los_unit_label_maps_days_to_ds160_text(self) -> None:
        self.assertEqual(_los_unit_label("DAYS"), "Day(s)")
        self.assertEqual(_los_unit_label("MONTHS"), "Month(s)")

    def test_visa_type_value_maps_b1b2(self) -> None:
        self.assertEqual(_visa_type_value("B1/B2"), "B")
        self.assertEqual(_visa_type_value("F1"), "F")

    def test_travel_purpose_value_maps_b1b2(self) -> None:
        self.assertEqual(_travel_purpose_value("B1/B2"), "B1-B2")

    def test_us_contact_relationship_defaults_to_other(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        self.assertEqual(_us_contact_relationship(dossier), "BUSINESS ASSOCIATE")

    def test_departure_date_computes_from_arrival_and_stay(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        dossier = replace(dossier, travel_plan=replace(
            dossier.travel_plan,
            intended_arrival_date="2025-06-15",
            intended_length_of_stay_value="7",
        ))
        self.assertEqual(_departure_date(dossier), "2025-06-22")


class PageDetectionTests(unittest.TestCase):
    """Tests for page detection and URL matching."""

    def test_previous_travel_url_matches_ceac_target(self) -> None:
        self.assertEqual(PREVIOUS_TRAVEL_URL_SUBSTRING, "node=PreviousUSTravel")

    def test_travel_companions_url_detected(self) -> None:
        url = "https://ceac.state.gov/GenNIV/General/complete/complete_travel.aspx?node=TravelCompanions"
        self.assertEqual(
            _detect_page_key(url, "Travel Companions Information"),
            "travel_companions"
        )

    def test_previous_travel_url_detected(self) -> None:
        url = "https://ceac.state.gov/GenNIV/General/complete/complete_travel.aspx?node=PreviousUSTravel"
        self.assertEqual(
            _detect_page_key(url, "Previous U.S. Travel Information"),
            "previous_travel"
        )

    def test_passport_page_matchers_include_pptvisa_alias(self) -> None:
        self.assertIn("node=PptVisa", PAGE_MATCHERS["passport"])


class PageIDNormalizeTests(unittest.TestCase):
    """Tests for page_id normalization mapping."""

    def test_page_id_mappings(self) -> None:
        self.assertEqual(PAGE_ID_NORMALIZE["us_contact_page"], "us_contact")
        self.assertEqual(PAGE_ID_NORMALIZE["family_relatives_page"], "family_relatives")
        self.assertEqual(PAGE_ID_NORMALIZE["family_spouse_page"], "family_spouse")
        self.assertEqual(PAGE_ID_NORMALIZE["security_part3_page"], "security_part3")


class CDPOperationTests(unittest.TestCase):
    """Tests for CDP operations that survived the refactoring."""

    def test_detect_current_page_extracts_application_id(self) -> None:
        with patch("visa_agent.browser.live_form_fill.find_target_websocket_url", return_value="ws://test"), patch(
            "visa_agent.browser.live_form_fill._runtime_eval",
            return_value={
                "value": {
                    "title": "Nonimmigrant Visa - Personal Information 1",
                    "url": "https://ceac.state.gov/GenNIV/General/complete/complete_personal.aspx?node=Personal1",
                    "application_id": "AA00FI6XAL",
                }
            },
        ):
            result = detect_current_page()

        self.assertTrue(result.ok)
        self.assertEqual(result.payload["page_key"], "personal1")
        self.assertEqual(result.payload["application_id"], "AA00FI6XAL")

    def test_extract_application_id_reads_aa_identifier(self) -> None:
        with patch("visa_agent.browser.live_form_fill.find_target_websocket_url", return_value="ws://test"), patch(
            "visa_agent.browser.live_form_fill._runtime_eval",
            return_value={"value": {"application_id": "AA00FI6XAL"}},
        ) as runtime_eval:
            result = extract_application_id()

        self.assertTrue(result.ok)
        self.assertEqual(result.payload["application_id"], "AA00FI6XAL")
        self.assertIn("Application ID", runtime_eval.call_args.args[1])

    def test_click_next_uses_next_button_not_save_button(self) -> None:
        responses = [
            {"value": {"url": "https://ceac.state.gov/GenNIV/General/complete/x.aspx?node=Personal1", "title": "Personal Information 1"}},
            {"value": {"status": "NEXT_CLICKED", "clicked": {"id": "ctl00_SiteContentPlaceHolder_UpdateButton3"}}},
            {"value": {"url": "https://ceac.state.gov/GenNIV/General/complete/y.aspx?node=Personal2", "title": "Personal Information 2"}},
        ]
        with patch("visa_agent.browser.live_form_fill.find_target_websocket_url", return_value="ws://test"), patch(
            "visa_agent.browser.live_form_fill._runtime_eval",
            side_effect=responses,
        ) as runtime_eval, patch("visa_agent.browser.live_form_fill.time.sleep"):
            result = click_next_and_wait(timeout_s=0.1)

        self.assertTrue(result.ok)
        self.assertEqual(result.payload["new_page_key"], "personal2")
        click_expression = runtime_eval.call_args_list[1].args[1]
        self.assertIn("#ctl00_SiteContentPlaceHolder_UpdateButton3", click_expression)
        self.assertNotIn("querySelector('#ctl00_SiteContentPlaceHolder_UpdateButton2')", click_expression)
        self.assertIn("needToConfirm = false", click_expression)
        self.assertIn("addEventListener('beforeunload'", click_expression)
        self.assertIn("btn.click()", click_expression)


class FillEngineTests(unittest.TestCase):
    """Tests for the new declarative fill engine."""

    def test_all_pages_have_handlers(self) -> None:
        for key in PAGE_REGISTRY:
            self.assertIn(key, _PAGE_FILL_HANDLERS, f"Missing handler for {key}")

    def test_18_pages_registered(self) -> None:
        self.assertEqual(len(PAGE_REGISTRY), 18)
        self.assertEqual(len(_PAGE_FILL_HANDLERS), 18)

    def test_personal1_has_two_phases(self) -> None:
        page = PAGE_REGISTRY["personal1"]
        self.assertEqual(len(page.phases), 2)
        self.assertEqual(page.phases[0].label, "ensure")
        self.assertEqual(page.phases[1].label, "fill")

    def test_ensure_phase_radio_click_hardcoded(self) -> None:
        page = PAGE_REGISTRY["personal1"]
        ensure = page.phases[0]
        self.assertEqual(ensure.fields[0].input_kind, "radio_click")
        self.assertEqual(ensure.fields[0].hardcoded, "N")

    def test_text_field_resolves_source_path(self) -> None:
        field = FieldBinding("test", "#selector", "text", source_path="identity.surname")
        dossier = load_dossier(SAMPLE_PATH)
        value = _resolve_value(field, dossier)
        self.assertEqual(value, "ZHANG")

    def test_hardcoded_field_returns_literal(self) -> None:
        field = FieldBinding("test", "#selector", "radio_click", hardcoded="N")
        dossier = load_dossier(SAMPLE_PATH)
        self.assertEqual(_resolve_value(field, dossier), "N")

    def test_generate_text_fill_js(self) -> None:
        field = FieldBinding("surname", "#tbxSurname", "text")
        js = _generate_fill_js(field, "ZHANG", "surname")
        self.assertIn("setText", js)
        self.assertIn('"#tbxSurname"', js)
        self.assertIn('"ZHANG"', js)

    def test_generate_radio_click_js(self) -> None:
        field = FieldBinding("other_names_no", "ctl00$rblOtherNames", "radio_click", choice_value="N")
        js = _generate_fill_js(field, "N", "other_names_no")
        self.assertIn("setRadioClick", js)
        self.assertIn('"ctl00$rblOtherNames"', js)
        self.assertIn('"N"', js)

    def test_generate_select_text_js(self) -> None:
        field = FieldBinding("sex", "#ddlGender", "select_text")
        js = _generate_fill_js(field, "Male", "sex")
        self.assertIn("setSelectText", js)

    def test_condition_false_skips_field(self) -> None:
        field = FieldBinding("test", "#sel", "text", condition=lambda d: False)
        dossier = load_dossier(SAMPLE_PATH)
        self.assertFalse(_should_fill(field, dossier))

    def test_condition_true_includes_field(self) -> None:
        field = FieldBinding("test", "#sel", "text", condition=lambda d: True)
        dossier = load_dossier(SAMPLE_PATH)
        self.assertTrue(_should_fill(field, dossier))

    def test_security_questions_have_radio_and_textarea(self) -> None:
        page = PAGE_REGISTRY["security_part1"]
        self.assertGreaterEqual(len(page.phases), 3)
        # First question about communicable_disease
        self.assertIn("communicable_disease", [f.field_id for f in page.phases[0].fields])

    def test_sample_dossier_has_personal1_values(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        self.assertEqual(dossier.identity.surname, "ZHANG")
        self.assertEqual(dossier.identity.birth_country, "CHINA")


class FillCurrentSupportedPageTests(unittest.TestCase):
    """Tests for fill_current_supported_page delegation."""

    def test_fills_when_page_recognized(self) -> None:
        with patch("visa_agent.browser.live_form_fill.find_target_websocket_url", return_value="ws://test"), patch(
            "visa_agent.browser.live_form_fill._runtime_eval",
            return_value={
                "value": {
                    "title": "Personal Information 1",
                    "url": "https://ceac.state.gov/GenNIV/General/complete/complete_personal.aspx?node=Personal1",
                    "application_id": "AA00TEST",
                }
            },
        ), patch(
            "visa_agent.browser.fill_engine._find_page_ws_url", return_value="ws://mock"
        ), patch(
            "visa_agent.browser.fill_engine._runtime_eval",
            return_value={"value": {"filled": ["surname"], "missing": []}},
        ):
            dossier = load_dossier(SAMPLE_PATH)
            result = fill_current_supported_page(dossier)

        self.assertTrue(result.ok)
        self.assertEqual(result.payload["page_key"], "personal1")


if __name__ == "__main__":
    unittest.main()
