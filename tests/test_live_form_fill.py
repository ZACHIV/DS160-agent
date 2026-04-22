from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from visa_agent.schema import load_dossier
from visa_agent.browser.live_form_fill import (
    PAGE_MATCHERS,
    PREVIOUS_TRAVEL_URL_SUBSTRING,
    _address_phone_defaults,
    _family_relative_mock_dob,
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

    def test_family_relative_mock_dob_is_stable(self) -> None:
        self.assertEqual(_family_relative_mock_dob("father"), "1965-03-12")
        self.assertEqual(_family_relative_mock_dob("mother"), "1968-07-21")

    def test_family_spouse_defaults_follow_identity_country(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        defaults = _family_spouse_defaults(dossier)
        self.assertEqual(defaults["dob"], "1992-11-08")
        self.assertEqual(defaults["nationality"], "CHINA")

    def test_sanitize_ds160_name_removes_punctuation(self) -> None:
        self.assertEqual(_sanitize_ds160_name("Shanghai Example Trading Co., Ltd."), "SHANGHAI EXAMPLE TRADING CO LTD")

    def test_work_education_previous_defaults_are_populated(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        defaults = _work_education_previous_defaults(dossier)
        self.assertEqual(defaults["prev_employer_name"], "SHANGHAI MODERN LOGISTICS CO LTD")
        self.assertEqual(defaults["school_name"], "SHANGHAI BUSINESS UNIVERSITY")

    def test_work_education_additional_defaults_are_populated(self) -> None:
        defaults = _work_education_additional_defaults()
        self.assertEqual(defaults["clan_name"], "HAN")
        self.assertEqual(defaults["country_visited"], "SINGAPORE")

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

    def test_address_phone_defaults_use_stable_mock_values(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        defaults = _address_phone_defaults(dossier)
        self.assertEqual(defaults["home_addr1"], "88 Huaihai Middle Road")
        self.assertEqual(defaults["home_city"], "Shanghai")
        self.assertEqual(defaults["home_state"], "Shanghai")
        self.assertEqual(defaults["primary_phone"], "862155558800")
        self.assertEqual(defaults["work_phone"], "862168889900")
        self.assertEqual(defaults["email"], "zhang.wei@example.cn")


if __name__ == "__main__":
    unittest.main()
