from __future__ import annotations

from pathlib import Path
import unittest

from visa_agent.schema import load_dossier
from visa_agent.browser.live_form_fill import _month_abbrev


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = ROOT / "sample_data" / "china_b1b2_sample.json"


class LiveFormFillTests(unittest.TestCase):
    def test_month_abbrev_mapping(self) -> None:
        self.assertEqual(_month_abbrev("08"), "AUG")

    def test_sample_dossier_has_personal1_values(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)
        self.assertEqual(dossier.identity.surname, "ZHANG")
        self.assertEqual(dossier.identity.birth_country, "CHINA")


if __name__ == "__main__":
    unittest.main()

