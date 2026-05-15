from __future__ import annotations

from rgm.storage.sqlite_store import SQLiteStore


def forget(node_id: str, store: SQLiteStore | None = None) -> dict:
    db = store or SQLiteStore()
    db.init_db()
    return {"node_id": node_id, "forgotten": db.forget_node(node_id)}

