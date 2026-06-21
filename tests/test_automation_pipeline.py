from __future__ import annotations

import unittest

from visa_agent.automation.pipeline import PipelineNode, TaskPipeline


class TaskPipelineTests(unittest.TestCase):
    def test_runs_nodes_in_order_and_updates_context(self) -> None:
        pipeline = TaskPipeline({
            "start": PipelineNode("start", action=lambda ctx: {"seen": ["start"]}, next=["finish"]),
            "finish": PipelineNode(
                "finish",
                action=lambda ctx: {"seen": ctx["seen"] + ["finish"]},
            ),
        })

        result = pipeline.run("start")

        self.assertTrue(result.completed)
        self.assertEqual(result.context["seen"], ["start", "finish"])
        self.assertEqual([event.status for event in result.events], [
            "starting",
            "succeeded",
            "starting",
            "succeeded",
        ])
        self.assertEqual(result.events[0].to_dict(), {
            "node": "start",
            "status": "starting",
            "detail": {},
        })

    def test_routes_to_on_error_when_recognition_misses(self) -> None:
        pipeline = TaskPipeline({
            "probe": PipelineNode(
                "probe",
                recognition=lambda ctx: False,
                next=["should_not_run"],
                on_error=["fallback"],
            ),
            "fallback": PipelineNode("fallback", action=lambda ctx: {"fallback": True}),
            "should_not_run": PipelineNode("should_not_run", action=lambda ctx: {"bad": True}),
        })

        result = pipeline.run("probe")

        self.assertTrue(result.completed)
        self.assertTrue(result.context["fallback"])
        self.assertNotIn("bad", result.context)


if __name__ == "__main__":
    unittest.main()
