from __future__ import annotations

from typing import Any

from rgm.models import RecallContext
from rgm.storage.sqlite_store import SQLiteStore

PREFERENCE_TYPES = {"Preference", "WorkflowHint", "ToolConfig"}
SESSION_TYPES = {"SessionNote"}
EVIDENCE_TYPES = {"Evidence", "Result"}


def _node_payload(node) -> dict[str, Any]:
    return {
        "id": node.id,
        "type": node.type,
        "layer": node.layer,
        "scope": node.scope,
        "project": node.project,
        "title": node.title,
        "content": node.content,
        "importance": node.importance,
        "confidence": node.confidence,
        "source_system": node.source_system,
        "metadata": node.metadata,
    }


def _edge_payload(edge) -> dict[str, Any]:
    return {
        "id": edge.id,
        "source": edge.source,
        "relation": edge.relation,
        "target": edge.target,
        "layer": edge.layer,
        "confidence": edge.confidence,
        "semantic_strength": edge.semantic_strength,
        "reasoning_allowed": edge.reasoning_allowed,
        "source_rule": edge.source_rule,
        "metadata": edge.metadata,
    }


def build_context(
    query: str,
    intent: str,
    search_result: dict[str, Any],
    expansion: dict[str, Any],
    store: SQLiteStore | None = None,
) -> RecallContext:
    db = store or SQLiteStore()
    context = RecallContext(query=query, intent=intent)

    nodes = [db.get_node(node_id) for node_id in expansion["node_ids"]]
    nodes = [node for node in nodes if node is not None and node.status == "active"]
    edges = [db.get_edge(edge_id) for edge_id in expansion["edge_ids"]]
    edges = [edge for edge in edges if edge is not None]

    for node in nodes:
        payload = _node_payload(node)
        if node.type in PREFERENCE_TYPES:
            context.preference_context.append(payload)
        elif node.type in SESSION_TYPES:
            context.session_context.append(payload)
        elif node.layer == "research":
            context.research_context.append(payload)
        elif node.layer == "lightweight":
            context.operational_context.append(payload)
        elif node.type in EVIDENCE_TYPES:
            context.evidence.append(payload)

        if node.type in EVIDENCE_TYPES and payload not in context.evidence:
            context.evidence.append(payload)

    reasoning_edges = [_edge_payload(edge) for edge in edges if edge.reasoning_allowed]
    context.graph_paths = [
        {
            "nodes": path["nodes"],
            "edges": path["edges"],
        }
        for path in expansion["paths"]
    ]
    context.debug_info = {
        "seed_ids": search_result["seed_ids"],
        "seed_node_count": len(search_result["nodes"]),
        "seed_chunk_count": len(search_result["chunks"]),
        "expanded_node_count": len(nodes),
        "expanded_edge_count": len(edges),
        "max_hops": expansion["max_hops"],
        "reasoning_edges": reasoning_edges,
    }
    return context

