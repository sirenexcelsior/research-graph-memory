from __future__ import annotations

from rgm.graph.schema import RESEARCH_TYPES, make_edge
from rgm.models import Node, stable_id
from rgm.storage.sqlite_store import SQLiteStore


def promote(node_id: str, to_type: str, store: SQLiteStore | None = None) -> dict:
    if to_type not in RESEARCH_TYPES:
        raise ValueError(f"{to_type} is not a research node type")

    db = store or SQLiteStore()
    db.init_db()
    source = db.get_node(node_id)
    if source is None:
        raise KeyError(f"Node not found: {node_id}")

    promoted = Node(
        id=stable_id("promoted", node_id, to_type, source.content),
        type=to_type,
        layer="research",
        scope=source.scope,
        project=source.project,
        source_system="promotion",
        title=source.title,
        content=source.content,
        importance=source.importance,
        confidence=max(0.0, min(1.0, source.confidence * 0.9)),
        metadata={
            "promoted_from": node_id,
            "source_type": source.type,
            "source_layer": source.layer,
            "source_metadata": source.metadata,
        },
    )
    db.upsert_node(promoted)
    edge = make_edge(
        source.id,
        "PROMOTED_TO",
        promoted.id,
        layer="cross",
        source_rule="manual_promote",
        confidence=promoted.confidence,
    )
    db.upsert_edge(edge)
    return {"source": source.model_dump(mode="json"), "promoted": promoted.model_dump(mode="json"), "edge": edge.model_dump(mode="json")}

