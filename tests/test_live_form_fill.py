from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from visa_agent.schema import load_dossier
from visa_agent.browser.live_form_fill import (
    PAGE_MATCHERS,
    PREVIOUS_TRAVEL_URL_SUBSTRING,
    _address_phone_defaults,
    _fill_security_questions,
    _family_relative_dob,
    _family_spouse_defaults,
    _find_page_ws_url,
    _month_abbrev,
    _normalize_phone_number,
    _previous_travel_los_unit,
    _sanitize_ds160_name,
    _security_explanation,
    _security_yes,
    _split_contact_name,
    _split_name_first_surname,
    _split_employer_address,
    _work_education_previous_defaults,
    _work_education_additional_defaults,
    fill_personal1_page,
    fill_personal2_page,
    fill_previous_travel_page,
    fill_travel_page,
)
from visa_agent.page_ids import PAGE_ID_NORMALIZE


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = ROOT / "sample_data" / "china_b1b2_sample.json"


class LiveFormFillTests(unittest.TestCase):
    def test_month_abbrev_mapping(self) -> None:
        self.assertEqual(_month_abbrev("08"), "AUG")

    def test_previous_travel_url_matches_ceac_target(self) -> None:
        self.assertEqual(PREVIOUS_TRAVEL_URL_SUBSTRING, "node=PreviousUSTravel")

    def test_passport_page_matchers_include_pptvisa_alias(self) -> None:
        self.assertIn("node=PptVisa", PAGE_MATCHERS["passport"])

    def test_us_contact_page_normalizes(self) -> None:
        self.assertEqual(PAGE_ID_NORMALIZE["us_contact_page"], "us_contact")
        self.assertEqual(PAGE_ID_NORMALIZE["family_relatives_page"], "family_relatives")
        self.assertEqual(PAGE_ID_NORMALIZE["family_spouse_page"], "family_spouse")
        self.assertEqual(PAGE_ID_NORMALIZE["security_part3_page"], "security_part3")

    def test_previous_travel_los_unit_maps_days_to_ds160_text(self) -> None:
        self.assertEqual(_previous_travel_los_unit("DAYS"), "Day(s)")

    def test_split_employer_address_extracts_city_state_country(self) -> None:
        self.assertEqual(
            _split_employer_address("88 Huaihai Middle Road, Shanghai, Shanghai, China"),
            ("88 Huaihai Middle Road", "Shanghai", "Shanghai", "China"),
        )

    def test_normalize_phone_number_keeps_only_digits(self) -> None:
        self.assertEqual(_normalize_phone_number("+86-21-5555-8800"), "862155558800")

    def test_split_contact_name_treats_last_token_as_surname(self) -> None:
        self.assertEqual(_split_contact_name("Michael Chen"), ("Chen", "Michael"))

    def test_split_name_first_surname_keeps_first_token_as_surname(self) -> None:
        self.assertEqual(_split_name_first_surname("ZHANG JIANGUO"), ("ZHANG", "JIANGUO"))

    def test_family_relative_dob_reads_from_dossier(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        self.assertIsNone(_family_relative_dob("father", dossier))
        self.assertIsNone(_family_relative_dob("mother", dossier))

    def test_family_spouse_defaults_uses_dossier_data(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        defaults = _family_spouse_defaults(dossier)
        self.assertIsNotNone(defaults)
        self.assertEqual(defaults.get("nationality"), "CHINA")

    def test_sanitize_ds160_name_removes_punctuation(self) -> None:
        self.assertEqual(_sanitize_ds160_name("Shanghai Example Trading Co., Ltd."), "SHANGHAI EXAMPLE TRADING CO LTD")

    def test_work_education_previous_defaults_returns_none_without_data(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        defaults = _work_education_previous_defaults(dossier)
        self.assertIsNone(defaults)

    def test_work_education_additional_defaults_returns_empty_strings(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        defaults = _work_education_additional_defaults(dossier)
        self.assertEqual(defaults["clan_name"], "")
        self.assertEqual(defaults["country_visited"], "")

    def test_security_defaults_to_no_without_schema_key(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        self.assertFalse(_security_yes(dossier, "genocide"))
        self.assertEqual(_security_explanation(dossier, "genocide"), "Explanation available upon request.")

    def test_find_page_ws_url_falls_back_to_title_match(self) -> None:
        with patch("visa_agent.browser.live_form_fill.find_target_websocket_url", side_effect=RuntimeError("miss")), patch(
            "visa_agent.browser.live_form_fill.list_debug_targets",
            return_value=[
                {
                    "title": "Nonimmigrant Visa - Passport Information",
                    "url": "https://ceac.state.gov/GenNIV/General/complete/Passport_Visa_Info.aspx?node=PptVisa",
                    "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/test",
                }
            ],
        ):
            self.assertEqual(_find_page_ws_url("passport"), "ws://127.0.0.1:9222/devtools/page/test")

    def test_sample_dossier_has_personal1_values(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        self.assertEqual(dossier.identity.surname, "ZHANG")
        self.assertEqual(dossier.identity.birth_country, "CHINA")

    def test_address_phone_defaults_returns_none_without_contact_data(self) -> None:
        # Build minimal dossier without personal_contact to verify None fallback
        dossier = load_dossier(SAMPLE_PATH)
        dossier = dossier.__class__(
            case_id=dossier.case_id,
            identity=dossier.identity,
            travel_plan=dossier.travel_plan,
            employment_education=dossier.employment_education,
            family_contacts=dossier.family_contacts,
            security_background=dossier.security_background,
            evidence_catalog=dossier.evidence_catalog,
            personal_contact=None,
            previous_travel=None,
        )
        defaults = _address_phone_defaults(dossier)
        self.assertIsNone(defaults)

    def test_personal1_fill_uses_staged_clicks_before_main_fill(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        responses = [
            {"value": {"filled": ["other_names_no", "telecode_no"], "missing": []}},
            {"value": {"filled": ["surname"], "missing": []}},
        ]
        with patch("visa_agent.browser.live_form_fill._find_page_ws_url", return_value="ws://test"), patch(
            "visa_agent.browser.live_form_fill._runtime_eval",
            side_effect=responses,
        ) as runtime_eval, patch("visa_agent.browser.live_form_fill.time.sleep"):
            result = fill_personal1_page(dossier)

        self.assertTrue(result.ok)
        self.assertEqual(runtime_eval.call_count, 2)
        first_expression = runtime_eval.call_args_list[0].args[1]
        second_expression = runtime_eval.call_args_list[1].args[1]
        self.assertIn("setRadioClick('ctl00$SiteContentPlaceHolder$FormView1$rblOtherNames', 'N')", first_expression)
        self.assertIn("setRadioClick('ctl00$SiteContentPlaceHolder$FormView1$rblTelecodeQuestion', 'N')", first_expression)
        self.assertIn("#ctl00_SiteContentPlaceHolder_FormView1_tbxAPP_SURNAME", second_expression)

    def test_personal2_fill_uses_staged_clicks_before_main_fill(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        responses = [
            {"value": {"filled": ["other_nationality_no", "perm_res_other_no"], "missing": []}},
            {"value": {"filled": ["nationality"], "missing": []}},
        ]
        with patch("visa_agent.browser.live_form_fill._find_page_ws_url", return_value="ws://test"), patch(
            "visa_agent.browser.live_form_fill._runtime_eval",
            side_effect=responses,
        ) as runtime_eval, patch("visa_agent.browser.live_form_fill.time.sleep"):
            result = fill_personal2_page(dossier)

        self.assertTrue(result.ok)
        self.assertEqual(runtime_eval.call_count, 2)
        first_expression = runtime_eval.call_args_list[0].args[1]
        second_expression = runtime_eval.call_args_list[1].args[1]
        self.assertIn("setRadioClick('ctl00$SiteContentPlaceHolder$FormView1$rblAPP_OTH_NATL_IND', 'N')", first_expression)
        self.assertIn("setRadioClick('ctl00$SiteContentPlaceHolder$FormView1$rblPermResOtherCntryInd', 'N')", first_expression)
        self.assertIn("#ctl00_SiteContentPlaceHolder_FormView1_ddlAPP_NATL", second_expression)

    def test_travel_fill_uses_staged_specific_travel_expansion(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        responses = [
            {"value": {"filled": ["specific_travel_yes"], "missing": []}},
            {"value": {"filled": ["visa_type"], "missing": []}},
            {"value": {"filled": ["purpose_specify", "arrival_day"], "missing": []}},
        ]
        with patch("visa_agent.browser.live_form_fill._find_page_ws_url", return_value="ws://test"), patch(
            "visa_agent.browser.live_form_fill._runtime_eval",
            side_effect=responses,
        ) as runtime_eval, patch(
            "visa_agent.browser.live_form_fill._wait_for_selector",
            return_value=True,
        ) as wait_for_selector, patch("visa_agent.browser.live_form_fill.time.sleep"):
            result = fill_travel_page(dossier)

        self.assertTrue(result.ok)
        self.assertEqual(runtime_eval.call_count, 3)
        self.assertEqual(wait_for_selector.call_count, 2)
        first_expression = runtime_eval.call_args_list[0].args[1]
        second_expression = runtime_eval.call_args_list[1].args[1]
        third_expression = runtime_eval.call_args_list[2].args[1]
        self.assertIn("setRadioClick('ctl00$SiteContentPlaceHolder$FormView1$rblSpecificTravel', 'Y')", first_expression)
        self.assertIn("#ctl00_SiteContentPlaceHolder_FormView1_dlPrincipalAppTravel_ctl00_ddlPurposeOfTrip", second_expression)
        self.assertIn("#ctl00_SiteContentPlaceHolder_FormView1_dlPrincipalAppTravel_ctl00_ddlOtherPurpose", third_expression)

    def test_previous_travel_fill_uses_staged_expansion(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        responses = [
            {"value": {"filled": ["prev_us_travel_yes"], "missing": []}},
            {"value": {"filled": ["prev_visa_yes"], "missing": []}},
            {"value": {"filled": ["prev_visit_day"], "missing": []}},
        ]
        with patch("visa_agent.browser.live_form_fill._find_page_ws_url", return_value="ws://test"), patch(
            "visa_agent.browser.live_form_fill._runtime_eval",
            side_effect=responses,
        ) as runtime_eval, patch(
            "visa_agent.browser.live_form_fill._wait_for_selector",
            return_value=True,
        ) as wait_for_selector, patch("visa_agent.browser.live_form_fill.time.sleep"):
            result = fill_previous_travel_page(dossier)

        self.assertTrue(result.ok)
        self.assertEqual(runtime_eval.call_count, 3)
        self.assertEqual(wait_for_selector.call_count, 2)
        first_expression = runtime_eval.call_args_list[0].args[1]
        second_expression = runtime_eval.call_args_list[1].args[1]
        third_expression = runtime_eval.call_args_list[2].args[1]
        self.assertIn("setRadioClick('ctl00$SiteContentPlaceHolder$FormView1$rblPREV_US_TRAVEL_IND', 'Y')", first_expression)
        self.assertIn("setRadioClick('ctl00$SiteContentPlaceHolder$FormView1$rblPREV_VISA_IND', 'Y')", second_expression)
        self.assertIn("#ctl00_SiteContentPlaceHolder_FormView1_dtlPREV_US_VISIT_ctl00_ddlPREV_US_VISIT_DTEDay", third_expression)

    def test_security_yes_answers_use_staged_textarea_fill(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        responses = [
            {"value": {"filled": ["communicable_disease_yes"], "missing": []}},
            {"value": {"filled": ["communicable_disease_explanation"], "missing": []}},
        ]
        with patch("visa_agent.browser.live_form_fill._find_page_ws_url", return_value="ws://test"), patch(
            "visa_agent.browser.live_form_fill._runtime_eval",
            side_effect=responses,
        ) as runtime_eval, patch(
            "visa_agent.browser.live_form_fill._wait_for_selector",
            return_value=True,
        ) as wait_for_selector, patch(
            "visa_agent.browser.live_form_fill._security_yes",
            return_value=True,
        ), patch(
            "visa_agent.browser.live_form_fill._security_explanation",
            return_value="Test explanation",
        ), patch("visa_agent.browser.live_form_fill.time.sleep"):
            result = _fill_security_questions(
                "security_part1",
                [
                    ("communicable_disease", "ctl00$SiteContentPlaceHolder$FormView1$rblDisease", "#ctl00_SiteContentPlaceHolder_FormView1_tbxDisease"),
                ],
                dossier,
            )

        self.assertTrue(result.ok)
        self.assertEqual(runtime_eval.call_count, 2)
        self.assertTrue(wait_for_selector.called)
        first_expression = runtime_eval.call_args_list[0].args[1]
        second_expression = runtime_eval.call_args_list[1].args[1]
        self.assertIn("setRadioClick(\"ctl00$SiteContentPlaceHolder$FormView1$rblDisease\", \"Y\")", first_expression)
        self.assertIn("setText(\"#ctl00_SiteContentPlaceHolder_FormView1_tbxDisease\", \"Test explanation\")", second_expression)


if __name__ == "__main__":
    unittest.main()
