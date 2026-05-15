from __future__ import annotations

from pathlib import Path

from rgm.storage.sqlite_store import SQLiteStore


def import_experiment(path: str | Path, store: SQLiteStore | None = None) -> dict[str, int]:
    """Reserved V0.1 adapter for future structured experiment logs."""
    _ = path
    _ = store
    return {"experiments": 0, "results": 0, "edges": 0}

