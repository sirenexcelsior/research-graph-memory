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

    assert result == {"records": 1, "nodes": 1}
    assert nodes[0].source_system == "holographic"
    assert nodes[0].layer == "lightweight"
    assert nodes[0].confidence == 1.0
    assert nodes[0].content == records[0]["content"]
    assert nodes[0].metadata["holographic_category"] == "user_pref"
    assert nodes[0].metadata["raw_record"] == records[0]

