from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rgm.models import Node, stable_id
from rgm.storage.sqlite_store import SQLiteStore


def load_holographic_records(path: str | Path) -> list[Any]:
    source = Path(path)
    if source.suffix.lower() == ".jsonl":
        with source.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    data = json.loads(source.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ["memories", "records", "items", "data"]:
            if isinstance(data.get(key), list):
                return data[key]
        return [data]
    return [data]


def record_content(record: Any) -> str:
    if isinstance(record, str):
        return record
    if isinstance(record, dict):
        for key in ["content", "text", "memory", "value", "body", "summary"]:
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return json.dumps(record, ensure_ascii=False, sort_keys=True)
    return str(record)


def record_category(record: Any) -> str:
    if isinstance(record, dict):
        for key in ["category", "type", "namespace", "kind"]:
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return "general"


def map_holographic_type(category: str, content: str) -> str:
    normalized = category.lower().strip()
    lowered = content.lower()
    if normalized == "user_pref":
        if any(word in lowered for word in ["workflow", "when i", "process", "habit"]):
            return "WorkflowHint"
        return "Preference"
    if normalized == "tool":
        if any(word in lowered for word in ["pipeline", "workflow", "use"]):
            return "WorkflowHint"
        return "ToolConfig"
    if normalized == "project":
        if any(word in lowered for word in ["decided", "decision", "choose", "chosen"]):
            return "ProjectDecision"
        return "ProjectState"
    return "ProjectState"


def holographic_to_node(record: Any) -> Node:
    content = record_content(record)
    category = record_category(record)
    node_type = map_holographic_type(category, content)
    project = record.get("project") if isinstance(record, dict) else None
    title = record.get("title") if isinstance(record, dict) else None
    raw_id = record.get("id") if isinstance(record, dict) else None
    node_id = stable_id("holographic", raw_id or category, content)
    return Node(
        id=node_id,
        type=node_type,
        layer="lightweight",
        scope=(record.get("scope") if isinstance(record, dict) else None) or ("project" if project else "global"),
        project=project,
        source_system="holographic",
        title=title,
        content=content,
        confidence=1.0,
        metadata={
            "holographic_category": category,
            "raw_record": record,
        },
    )


def import_holographic(path: str | Path, store: SQLiteStore | None = None) -> dict[str, int]:
    db = store or SQLiteStore()
    db.init_db()
    records = load_holographic_records(path)
    count = 0
    for record in records:
        db.upsert_node(holographic_to_node(record))
        count += 1
    return {"records": len(records), "nodes": count}

