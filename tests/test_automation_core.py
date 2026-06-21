from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from visa_agent.automation.core import DS160AutomationCore
from visa_agent.schema import load_dossier


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = ROOT / "sample_data" / "china_b1b2_sample.json"


class AutomationCoreTests(unittest.TestCase):
    def test_fill_page_runs_browser_fill_and_audit_pipeline(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)

        class FakeResult:
            ok = True
            payload = {"filled": ["surname"], "missing": []}

        with tempfile.TemporaryDirectory() as td, patch(
            "visa_agent.automation.core.list_debug_targets",
            return_value=[{"url": "https://ceac.state.gov", "webSocketDebuggerUrl": "ws://test"}],
        ), patch(
            "visa_agent.automation.core._PAGE_FILL_HANDLERS",
            {"personal1": lambda loaded: FakeResult()},
        ), patch.object(
            DS160AutomationCore, "detect_application_id", return_value="AA00TEST1"
        ), patch(
            "visa_agent.automation.core.checkpoint_workspace", return_value=Path(td)
        ), patch(
            "visa_agent.audit_log._today_log", return_value=Path(td) / "audit.jsonl"
        ):
            outcome = DS160AutomationCore().fill_page(dossier, requested_page_id="personal1")

        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.page_key, "personal1")
        self.assertEqual(outcome.filled, ["surname"])
        self.assertEqual(outcome.missing, [])
        self.assertEqual(outcome.application_id, "AA00TEST1")
        self.assertEqual(outcome.pipeline_events[-1].node, "record_fill")


if __name__ == "__main__":
    unittest.main()
