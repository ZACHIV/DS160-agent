from __future__ import annotations

from pathlib import Path
import unittest

from visa_agent.page_ids import PAGE_ID_NORMALIZE
from visa_agent.schema import load_dossier


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = ROOT / "sample_data" / "china_b1b2_sample.json"


class PageAssistTests(unittest.TestCase):
    def test_previous_us_travel_page_normalizes_to_previous_travel(self) -> None:
        self.assertEqual(PAGE_ID_NORMALIZE["previous_us_travel_page"], "previous_travel")

    def test_sample_dossier_supports_personal2_fields(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        self.assertEqual(dossier.identity.nationality, "CHINA")


if __name__ == "__main__":
    unittest.main()
