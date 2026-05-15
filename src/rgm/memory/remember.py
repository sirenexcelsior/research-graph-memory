from __future__ import annotations

from rgm.memory.write_policy import normalize_layer, validate_manual_write
from rgm.models import Node
from rgm.storage.sqlite_store import SQLiteStore


def remember(
    content: str,
    *,
    node_type: str = "SessionNote",
    layer: str | None = None,
    scope: str = "global",
    project: str | None = None,
    title: str | None = None,
    importance: float = 0.5,
    confidence: float = 1.0,
    store: SQLiteStore | None = None,
) -> Node:
    db = store or SQLiteStore()
    db.init_db()
    final_layer = normalize_layer(node_type, layer)
    validate_manual_write(node_type, final_layer)
    node = Node(
        type=node_type,
        layer=final_layer,
        scope=scope,
        project=project,
        source_system="manual",
        title=title,
        content=content,
        importance=importance,
        confidence=confidence,
    )
    return db.upsert_node(node)

