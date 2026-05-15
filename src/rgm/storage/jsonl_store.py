from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel

from rgm.models import Chunk, Edge, Node
from rgm.storage.sqlite_store import SQLiteStore


def write_jsonl(path: str | Path, rows: Iterable[dict]) -> int:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with target.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def read_jsonl(path: str | Path) -> list[dict]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def model_dict(model: BaseModel) -> dict:
    return model.model_dump(mode="json")


def export_store(store: SQLiteStore, output_dir: str | Path) -> dict[str, int]:
    output = Path(output_dir)
    counts = {
        "nodes": write_jsonl(output / "nodes.jsonl", (model_dict(node) for node in store.iter_nodes(include_inactive=True))),
        "edges": write_jsonl(output / "edges.jsonl", (model_dict(edge) for edge in store.iter_edges())),
        "chunks": write_jsonl(output / "chunks.jsonl", (model_dict(chunk) for chunk in store.iter_chunks())),
    }
    return counts


def import_jsonl_bundle(store: SQLiteStore, input_dir: str | Path) -> dict[str, int]:
    source = Path(input_dir)
    counts = {"nodes": 0, "edges": 0, "chunks": 0}
    nodes_path = source / "nodes.jsonl"
    edges_path = source / "edges.jsonl"
    chunks_path = source / "chunks.jsonl"
    if nodes_path.exists():
        for row in read_jsonl(nodes_path):
            store.upsert_node(Node(**row))
            counts["nodes"] += 1
    if chunks_path.exists():
        for row in read_jsonl(chunks_path):
            store.upsert_chunk(Chunk(**row))
            counts["chunks"] += 1
    if edges_path.exists():
        for row in read_jsonl(edges_path):
            store.upsert_edge(Edge(**row))
            counts["edges"] += 1
    return counts

