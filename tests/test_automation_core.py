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

        class FakeDriver:
            def list_targets(self):
                return [{"url": "https://ceac.state.gov", "webSocketDebuggerUrl": "ws://test"}]

            def detect_current_page(self):
                return {"page_key": "personal1"}

            def detect_application_id(self):
                return "AA00TEST1"

            def supports_page(self, page_key):
                return page_key == "personal1"

            def fill_page(self, page_key, loaded):
                self.last_page_key = page_key
                return FakeResult()

            def fill_and_continue(self, page_key, loaded):
                raise AssertionError("not used")

        driver = FakeDriver()
        with tempfile.TemporaryDirectory() as td, patch(
            "visa_agent.automation.core.checkpoint_workspace", return_value=Path(td)
        ), patch(
            "visa_agent.audit_log._today_log", return_value=Path(td) / "audit.jsonl"
        ):
            outcome = DS160AutomationCore(driver=driver).fill_page(dossier, requested_page_id="personal1")

        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.page_key, "personal1")
        self.assertEqual(driver.last_page_key, "personal1")
        self.assertEqual(outcome.filled, ["surname"])
        self.assertEqual(outcome.missing, [])
        self.assertEqual(outcome.application_id, "AA00TEST1")
        self.assertEqual(outcome.pipeline_events[-1].node, "record_fill")

    def test_fill_continue_uses_driver_support_check(self) -> None:
        dossier = load_dossier(SAMPLE_PATH)

        class FakeDriver:
            def list_targets(self):
                return [{"url": "https://ceac.state.gov", "webSocketDebuggerUrl": "ws://test"}]

            def detect_current_page(self):
                return {"page_key": "personal1"}

            def detect_application_id(self):
                return "AA00TEST1"

            def supports_page(self, page_key):
                return page_key == "personal1"

            def fill_page(self, page_key, loaded):
                raise AssertionError("not used")

            def fill_and_continue(self, page_key, loaded):
                return {
                    "fill_ok": True,
                    "next_ok": True,
                    "fill_payload": {"filled": ["surname"], "missing": []},
                    "new_page_key": "personal2",
                    "application_id": "AA00TEST1",
                }

        with tempfile.TemporaryDirectory() as td, patch(
            "visa_agent.automation.core.checkpoint_workspace", return_value=Path(td)
        ), patch(
            "visa_agent.audit_log._today_log", return_value=Path(td) / "audit.jsonl"
        ):
            outcome = DS160AutomationCore(driver=FakeDriver()).fill_current_page_and_continue(
                dossier,
                requested_page_id="personal1",
            )

        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.page_key, "personal1")
        self.assertEqual(outcome.new_page_key, "personal_page_2")
        self.assertEqual([event.node for event in outcome.pipeline_events if event.status == "succeeded"], [
            "check_browser",
            "resolve_page",
            "ensure_supported",
            "fill_continue",
            "save_checkpoint",
            "record_fill",
        ])


if __name__ == "__main__":
    unittest.main()
