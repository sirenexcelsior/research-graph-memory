from __future__ import annotations

from typing import Any

from rgm.storage.sqlite_store import SQLiteStore


def fts_search(query: str, store: SQLiteStore | None = None, *, limit: int = 8, project: str | None = None) -> dict[str, Any]:
    db = store or SQLiteStore()
    nodes = db.search_nodes(query, limit=limit, project=project)
    chunks = db.search_chunks(query, limit=limit, project=project)
    seed_ids: list[str] = []
    for row in nodes:
        seed_ids.append(row["node"].id)
    for row in chunks:
        seed_ids.append(row["chunk"].id)
    return {
        "nodes": nodes,
        "chunks": chunks,
        "seed_ids": list(dict.fromkeys(seed_ids)),
    }
