from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from rgm.graph.schema import make_edge
from rgm.models import Edge, Node


def _group_key(node: Node) -> tuple[str | None]:
    return (node.project,)


def _edges_between(
    sources: list[Node],
    relation: str,
    targets: list[Node],
    *,
    source_rule: str,
) -> list[Edge]:
    edges: list[Edge] = []
    for source in sources:
        for target in targets:
            if source.id == target.id:
                continue
            edges.append(
                make_edge(
                    source.id,
                    relation,
                    target.id,
                    layer="lightweight",
                    source_rule=source_rule,
                    confidence=0.65,
                    metadata={"edge_strength": "weak", "owner": "rgm", "created_by": "rule"},
                )
            )
    return edges


def build_lightweight_weak_edges(nodes: Iterable[Node], *, source_rule: str = "holographic_weak_policy") -> list[Edge]:
    grouped: dict[tuple[str | None], dict[str, list[Node]]] = defaultdict(lambda: defaultdict(list))
    for node in nodes:
        if node.layer != "lightweight":
            continue
        grouped[_group_key(node)][node.type].append(node)

    edges: list[Edge] = []
    for by_type in grouped.values():
        edges.extend(_edges_between(by_type["Preference"], "APPLIES_TO", by_type["WorkflowHint"], source_rule=source_rule))
        edges.extend(_edges_between(by_type["ToolConfig"], "USED_BY", by_type["ProjectState"], source_rule=source_rule))
        edges.extend(_edges_between(by_type["ToolConfig"], "APPLIES_TO", by_type["WorkflowHint"], source_rule=source_rule))
        edges.extend(_edges_between(by_type["ProjectDecision"], "AFFECTS", by_type["ProjectState"], source_rule=source_rule))
        edges.extend(_edges_between(by_type["Todo"], "NEXT_STEP_FOR", by_type["ProjectState"], source_rule=source_rule))
    return edges

