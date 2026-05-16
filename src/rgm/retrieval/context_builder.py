from __future__ import annotations

from typing import Any

from rgm.models import RecallContext
from rgm.storage.sqlite_store import SQLiteStore

PREFERENCE_TYPES = {"Preference", "WorkflowHint", "ToolConfig"}
SESSION_TYPES = {"SessionNote"}
EVIDENCE_TYPES = {"Evidence", "Result"}
DOCUMENT_TYPES = {"Document", "Chunk"}

DEFAULT_CONTEXT_LIMITS = {
    "document_context": 12,
    "research_context": 20,
    "operational_context": 10,
    "preference_context": 10,
    "session_context": 10,
    "evidence": 12,
    "graph_paths": 30,
    "reasoning_edges": 30,
}

INTENT_CONTEXT_LIMITS = {
    "research_evidence": {
        "document_context": 16,
        "research_context": 20,
        "evidence": 16,
        "graph_paths": 40,
        "reasoning_edges": 40,
    },
    "hypothesis_trace": {
        "document_context": 12,
        "research_context": 24,
        "evidence": 12,
        "graph_paths": 40,
        "reasoning_edges": 40,
    },
    "preference_query": {
        "preference_context": 12,
        "operational_context": 8,
        "graph_paths": 10,
        "reasoning_edges": 10,
    },
}


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


def _limits_for_intent(intent: str) -> dict[str, int]:
    return DEFAULT_CONTEXT_LIMITS | INTENT_CONTEXT_LIMITS.get(intent, {})


def _append_unique(items: list[dict[str, Any]], payload: dict[str, Any], seen: set[str], limit: int) -> None:
    item_id = payload["id"]
    if item_id in seen or len(items) >= limit:
        return
    seen.add(item_id)
    items.append(payload)


def _dedupe_paths(paths: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    for path in paths:
        key = (tuple(path["nodes"]), tuple(path["edges"]))
        if key in seen:
            continue
        seen.add(key)
        unique.append({"nodes": path["nodes"], "edges": path["edges"]})
        if len(unique) >= limit:
            break
    return unique


def _dedupe_edge_payloads(edges: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for edge in edges:
        if edge["id"] in seen:
            continue
        seen.add(edge["id"])
        unique.append(edge)
        if len(unique) >= limit:
            break
    return unique


def build_context(
    query: str,
    intent: str,
    search_result: dict[str, Any],
    expansion: dict[str, Any],
    store: SQLiteStore | None = None,
) -> RecallContext:
    db = store or SQLiteStore()
    context = RecallContext(query=query, intent=intent)
    limits = _limits_for_intent(intent)

    nodes = [db.get_node(node_id) for node_id in expansion["node_ids"]]
    nodes = [node for node in nodes if node is not None and node.status == "active"]
    edges = [db.get_edge(edge_id) for edge_id in expansion["edge_ids"]]
    edges = [edge for edge in edges if edge is not None]
    seen_by_bucket: dict[str, set[str]] = {
        "document_context": set(),
        "research_context": set(),
        "operational_context": set(),
        "preference_context": set(),
        "session_context": set(),
        "evidence": set(),
    }

    for node in nodes:
        payload = _node_payload(node)
        if node.type in DOCUMENT_TYPES:
            _append_unique(context.document_context, payload, seen_by_bucket["document_context"], limits["document_context"])
        elif node.type in PREFERENCE_TYPES:
            _append_unique(context.preference_context, payload, seen_by_bucket["preference_context"], limits["preference_context"])
        elif node.type in SESSION_TYPES:
            _append_unique(context.session_context, payload, seen_by_bucket["session_context"], limits["session_context"])
        elif node.type in EVIDENCE_TYPES:
            _append_unique(context.evidence, payload, seen_by_bucket["evidence"], limits["evidence"])
        elif node.layer == "research":
            _append_unique(context.research_context, payload, seen_by_bucket["research_context"], limits["research_context"])
        elif node.layer == "lightweight":
            _append_unique(context.operational_context, payload, seen_by_bucket["operational_context"], limits["operational_context"])

    reasoning_edges = _dedupe_edge_payloads([_edge_payload(edge) for edge in edges if edge.reasoning_allowed], limits["reasoning_edges"])
    context.graph_paths = _dedupe_paths(expansion["paths"], limits["graph_paths"])
    context.debug_info = {
        "seed_ids": search_result["seed_ids"],
        "seed_node_count": len(search_result["nodes"]),
        "seed_chunk_count": len(search_result["chunks"]),
        "expanded_node_count": len(nodes),
        "expanded_edge_count": len(edges),
        "returned_counts": {
            "document_context": len(context.document_context),
            "research_context": len(context.research_context),
            "operational_context": len(context.operational_context),
            "preference_context": len(context.preference_context),
            "session_context": len(context.session_context),
            "evidence": len(context.evidence),
            "graph_paths": len(context.graph_paths),
        },
        "context_limits": limits,
        "max_hops": expansion["max_hops"],
        "cross_project_allowed": expansion.get("cross_project_allowed", False),
        "reasoning_edges": reasoning_edges,
    }
    return context
