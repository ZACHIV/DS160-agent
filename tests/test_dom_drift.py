from __future__ import annotations

import unittest
from unittest.mock import patch

from visa_agent.dom_drift import check_page_selectors


class DomDriftTests(unittest.TestCase):
    def test_unhealthy_report_saves_visual_evidence(self) -> None:
        class FakeCDP:
            def __init__(self, ws_url: str) -> None:
                self.ws_url = ws_url

            def __enter__(self) -> "FakeCDP":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def call(self, method: str, params: dict | None = None) -> dict:
                return {"result": {"result": {"value": False}}}

        class FakeEvidence:
            path = "/tmp/drift.png"

        with patch("visa_agent.dom_drift.SAMPLE_SELECTORS", {"test_page": ["#a", "#b", "#c"]}), patch(
            "visa_agent.dom_drift.find_target_websocket_url", return_value="ws://test"
        ), patch("visa_agent.dom_drift.CDPWebSocket", FakeCDP), patch(
            "visa_agent.automation.evidence.VisualEvidenceStore.screenshot", return_value=FakeEvidence()
        ):
            report = check_page_selectors("test_page")

        self.assertFalse(report.healthy)
        self.assertEqual(report.found, 0)
        self.assertEqual(report.missing, ["#a", "#b", "#c"])
        self.assertEqual(report.evidence_path, "/tmp/drift.png")


if __name__ == "__main__":
    unittest.main()
