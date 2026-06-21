"""Small task pipeline runtime inspired by MaaFramework nodes."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any


PipelineAction = Callable[[dict[str, Any]], dict[str, Any]]
PipelineRecognition = Callable[[dict[str, Any]], bool]


@dataclass(frozen=True)
class PipelineNode:
    name: str
    action: PipelineAction | None = None
    recognition: PipelineRecognition | None = None
    next: list[str] = field(default_factory=list)
    on_error: list[str] = field(default_factory=list)
    attach: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineEvent:
    node: str
    status: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node": self.node,
            "status": self.status,
            "detail": dict(self.detail),
        }


@dataclass(frozen=True)
class PipelineResult:
    completed: bool
    events: list[PipelineEvent]
    context: dict[str, Any]
    last_node: str | None = None
    error: str | None = None


class TaskPipeline:
    """Executes named nodes with first-hit next/on_error routing."""

    def __init__(self, nodes: Mapping[str, PipelineNode]) -> None:
        self.nodes = dict(nodes)

    def run(self, entry: str, context: dict[str, Any] | None = None) -> PipelineResult:
        ctx = dict(context or {})
        events: list[PipelineEvent] = []
        current = entry
        visited = 0
        max_nodes = int(ctx.get("max_pipeline_nodes", 100))

        while current:
            visited += 1
            if visited > max_nodes:
                return PipelineResult(False, events, ctx, current, "PIPELINE_NODE_LIMIT")

            node = self._node(current)
            events.append(PipelineEvent(node.name, "starting", dict(node.attach)))
            try:
                if node.recognition is not None and not node.recognition(ctx):
                    events.append(PipelineEvent(node.name, "missed"))
                    current = self._first_available(node.on_error)
                    if not current:
                        return PipelineResult(False, events, ctx, node.name, "RECOGNITION_MISSED")
                    continue

                if node.action is not None:
                    update = node.action(ctx)
                    if update:
                        ctx.update(update)

                events.append(PipelineEvent(node.name, "succeeded"))
                current = self._first_available(node.next)
            except Exception as exc:
                events.append(PipelineEvent(node.name, "failed", {"error": str(exc)}))
                current = self._first_available(node.on_error)
                if not current:
                    return PipelineResult(False, events, ctx, node.name, str(exc))

        last_node = events[-1].node if events else None
        return PipelineResult(True, events, ctx, last_node)

    def _node(self, name: str) -> PipelineNode:
        try:
            return self.nodes[name]
        except KeyError:
            raise KeyError(f"Unknown pipeline node: {name}") from None

    def _first_available(self, names: list[str]) -> str | None:
        for name in names:
            if name in self.nodes:
                return name
        return None
