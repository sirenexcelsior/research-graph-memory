import json

from rgm.adapters.holographic import import_holographic
from rgm.storage.sqlite_store import SQLiteStore


def test_holographic_import_preserves_raw_content(tmp_path):
    db = SQLiteStore(tmp_path / "rgm.sqlite")
    source = tmp_path / "holographic.json"
    records = [
        {
            "id": "pref-1",
            "category": "user_pref",
            "content": "User prefers concise engineering updates.",
            "project": "research-graph-memory",
        }
    ]
    source.write_text(json.dumps(records), encoding="utf-8")

    result = import_holographic(source, db)
    nodes = db.iter_nodes()

    assert result == {"records": 1, "nodes": 1, "edges": 0}
    assert nodes[0].source_system == "holographic"
    assert nodes[0].layer == "lightweight"
    assert nodes[0].confidence == 1.0
    assert nodes[0].content == records[0]["content"]
    assert nodes[0].metadata["holographic_category"] == "user_pref"
    assert nodes[0].metadata["raw_record"] == records[0]


def test_holographic_import_builds_lightweight_weak_edges(tmp_path):
    db = SQLiteStore(tmp_path / "rgm.sqlite")
    source = tmp_path / "holographic.json"
    records = [
        {
            "id": "pref-1",
            "category": "user_pref",
            "content": "User prefers structured status updates.",
            "project": "demo",
        },
        {
            "id": "hint-1",
            "category": "user_pref",
            "content": "Workflow hint: provide concise verification output.",
            "project": "demo",
        },
        {
            "id": "tool-1",
            "category": "tool",
            "content": "SQLite FTS5 backend configuration for keyword search.",
            "project": "demo",
        },
        {
            "id": "state-1",
            "category": "general",
            "content": "The demo project is validating recall behavior.",
            "project": "demo",
        },
        {
            "id": "decision-1",
            "category": "project",
            "content": "Decision: keep dense retrieval optional.",
            "project": "demo",
        },
    ]
    source.write_text(json.dumps(records), encoding="utf-8")

    result = import_holographic(source, db)
    edges = db.iter_edges()
    relations = {edge.relation for edge in edges}

    assert result["nodes"] == 5
    assert result["edges"] >= 3
    assert {"APPLIES_TO", "USED_BY", "AFFECTS"} <= relations
    assert all(edge.metadata["owner"] == "rgm" for edge in edges)
    assert all(edge.metadata["edge_strength"] == "weak" for edge in edges)
    assert all(edge.metadata["created_by"] == "rule" for edge in edges)
