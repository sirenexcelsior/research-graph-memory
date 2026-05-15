from __future__ import annotations

from typing import Any

from rgm.graph.traversal import expand_from_seeds
from rgm.storage.sqlite_store import SQLiteStore


def graph_expand(
    seed_ids: list[str],
    store: SQLiteStore | None = None,
    *,
    intent: str,
    debug: bool = False,
) -> dict[str, Any]:
    return expand_from_seeds(seed_ids, store=store, intent=intent, debug=debug)

