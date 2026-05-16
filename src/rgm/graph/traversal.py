from __future__ import annotations

from collections import deque
from typing import Any

from rgm.storage.sqlite_store import SQLiteStore

INTENT_HOPS = {
    "general_recall": 1,
    "project_state": 1,
    "preference_query": 1,
    "research_evidence": 2,
    "hypothesis_trace": 2,
    "debug_explore": 3,
}

INTENT_LAYERS = {
    "project_state": {"lightweight", "research", "cross"},
    "preference_query": {"lightweight", "cross"},
    "research_evidence": {"document", "research", "cross"},
    "hypothesis_trace": {"document", "research", "cross"},
}

BLOCKED_RELATIONS = {"RELATED_TO"}

INTENT_EDGE_ALLOWLIST = {
    "research_evidence": {
        "SUPPORTED_BY",
        "CONTRADICTED_BY",
        "TESTED_BY",
        "PRODUCES",
        "EVIDENCE_FOR",
        "HAS_CHUNK",
        "PART_OF",
        "STATES",
    },
    "hypothesis_trace": {
        "SUPPORTED_BY",
        "CONTRADICTED_BY",
        "TESTED_BY",
        "PRODUCES",
        "EVIDENCE_FOR",
        "MOTIVATES",
        "GENERATES",
        "NEXT_STEP_FOR",
        "STATES",
    },
    "preference_query": {
        "APPLIES_TO",
        "USED_BY",
        "AFFECTS",
        "NEXT_STEP_FOR",
        "PROMOTED_TO",
        "STATES",
    },
    "project_state": {
        "APPLIES_TO",
        "USED_BY",
        "AFFECTS",
        "NEXT_STEP_FOR",
        "PROMOTED_TO",
        "STATES",
    },
}


def max_hops_for_intent(intent: str, debug: bool = False) -> int:
    if intent == "debug_explore" and not debug:
        return 1
    return INTENT_HOPS.get(intent, 1)


def edge_allowed(edge_relation: str, intent: str) -> bool:
    if edge_relation in BLOCKED_RELATIONS and intent != "debug_explore":
        return False
    allowlist = INTENT_EDGE_ALLOWLIST.get(intent)
    if allowlist is not None:
        return edge_relation in allowlist
    return True


def node_allowed(node_layer: str, intent: str) -> bool:
    layers = INTENT_LAYERS.get(intent)
    if not layers:
        return True
    return node_layer in layers


def project_allowed(node_project: str | None, project: str | None, cross_project_allowed: bool) -> bool:
    if cross_project_allowed or project is None:
        return True
    return node_project in {None, project}


def expand_from_seeds(
    seed_ids: list[str],
    store: SQLiteStore | None = None,
    *,
    intent: str = "general_recall",
    debug: bool = False,
    max_hops: int | None = None,
    project: str | None = None,
    cross_project_allowed: bool = False,
) -> dict[str, Any]:
    db = store or SQLiteStore()
    hops = max_hops if max_hops is not None else max_hops_for_intent(intent, debug=debug)
    allowed_seed_ids = []
    for seed_id in seed_ids:
        node = db.get_node(seed_id)
        if node is not None and project_allowed(node.project, project, cross_project_allowed):
            allowed_seed_ids.append(seed_id)
    visited: set[str] = set(allowed_seed_ids)
    node_ids: set[str] = set(allowed_seed_ids)
    node_order: list[str] = list(dict.fromkeys(allowed_seed_ids))
    edge_ids: set[str] = set()
    edge_order: list[str] = []
    paths: list[dict[str, Any]] = []
    queue = deque((seed_id, 0, [seed_id], []) for seed_id in allowed_seed_ids)

    while queue:
        current_id, depth, path_nodes, path_edges = queue.popleft()
        if depth >= hops:
            continue
        current_node = db.get_node(current_id)
        if current_node is None:
            continue
        for edge in db.get_incident_edges(current_id):
            if not edge_allowed(edge.relation, intent):
                continue
            neighbor_id = edge.target if edge.source == current_id else edge.source
            neighbor = db.get_node(neighbor_id)
            if neighbor is None or neighbor.status != "active":
                continue
            if not project_allowed(neighbor.project, project, cross_project_allowed):
                continue
            if not node_allowed(neighbor.layer, intent):
                continue
            next_path_nodes = [*path_nodes, neighbor_id]
            next_path_edges = [*path_edges, edge.id]
            if edge.id not in edge_ids:
                edge_ids.add(edge.id)
                edge_order.append(edge.id)
            if neighbor_id not in node_ids:
                node_ids.add(neighbor_id)
                node_order.append(neighbor_id)
            paths.append({"nodes": next_path_nodes, "edges": next_path_edges})
            if neighbor_id not in visited:
                visited.add(neighbor_id)
                queue.append((neighbor_id, depth + 1, next_path_nodes, next_path_edges))

    return {
        "node_ids": node_order,
        "edge_ids": edge_order,
        "paths": paths,
        "max_hops": hops,
        "cross_project_allowed": cross_project_allowed,
    }
