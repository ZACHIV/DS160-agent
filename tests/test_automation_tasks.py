from __future__ import annotations

import unittest

from visa_agent.automation.tasks import automation_task_catalog

try:
    from visa_agent.server import get_automation_tasks
    SERVER_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment-dependent
    get_automation_tasks = None
    SERVER_IMPORT_ERROR = exc


class AutomationTaskCatalogTests(unittest.TestCase):
    def test_catalog_contains_core_task_entries(self) -> None:
        catalog = automation_task_catalog()
        entries = {task["entry"]: task for task in catalog}

        self.assertIn("fill_page", entries)
        self.assertIn("fill_and_continue", entries)
        self.assertIn("dom_drift", entries)
        self.assertEqual(entries["fill_page"]["pipeline_nodes"][0], "check_browser")
        self.assertIn("visual-evidence", entries["dom_drift"]["tags"])


@unittest.skipIf(get_automation_tasks is None, f"server dependencies unavailable: {SERVER_IMPORT_ERROR}")
class AutomationTaskEndpointTests(unittest.TestCase):
    def test_endpoint_returns_task_catalog(self) -> None:
        payload = get_automation_tasks().model_dump()

        self.assertTrue(payload["ok"])
        self.assertGreaterEqual(len(payload["tasks"]), 3)
        self.assertIn("entry", payload["tasks"][0])


if __name__ == "__main__":
    unittest.main()
