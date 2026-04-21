from __future__ import annotations

import unittest


from visa_agent.browser.visible_control import VisibleControlResult


class VisibleControlTests(unittest.TestCase):
    def test_visible_control_result_serializes(self) -> None:
        result = VisibleControlResult(action="fill", ok=True, payload={"status": "START_CLICKED"})
        self.assertEqual(result.to_dict()["payload"]["status"], "START_CLICKED")


if __name__ == "__main__":
    unittest.main()

