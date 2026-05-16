from __future__ import annotations

from pathlib import Path

from rgm.graph.schema import make_edge
from rgm.models import Chunk, Node
from rgm.storage.jsonl_store import import_jsonl_bundle, read_jsonl, write_jsonl, export_store
from rgm.storage.sqlite_store import SQLiteStore


def _seed_store(store: SQLiteStore) -> tuple[Node, Node]:
    store.init_db()
    claim = Node(
        id="claim:roundtrip",
        type="Claim",
        layer="research",
        project="roundtrip",
        content="Round-trip claim content.",
        extraction_confidence=0.81,
    )
    evidence = Node(
        id="evidence:roundtrip",
        type="Evidence",
        layer="research",
        project="roundtrip",
        content="Round-trip evidence content.",
    )
    chunk = Chunk(id="chunk:roundtrip", doc_id="doc:roundtrip", text="Round-trip chunk text.")
    store.upsert_node(claim)
    store.upsert_node(evidence)
    store.upsert_chunk(chunk)
    store.upsert_edge(make_edge(claim.id, "SUPPORTED_BY", evidence.id, layer="research", source_rule="manual_roundtrip"))
    return claim, evidence


def test_jsonl_export_import_preserves_node_fields(tmp_path):
    source = SQLiteStore(tmp_path / "source.sqlite")
    _seed_store(source)
    export_dir = tmp_path / "export"
    export_store(source, export_dir)

    target = SQLiteStore(tmp_path / "target.sqlite")
    target.init_db()
    import_jsonl_bundle(target, export_dir)

    source_nodes = {node.id: node for node in source.iter_nodes(include_inactive=True)}
    target_nodes = {node.id: node for node in target.iter_nodes(include_inactive=True)}
    assert set(target_nodes) == set(source_nodes)
    for node_id, source_node in source_nodes.items():
        target_node = target_nodes[node_id]
        assert target_node.content == source_node.content
        assert target_node.type == source_node.type
        assert target_node.layer == source_node.layer
        assert target_node.project == source_node.project


def test_jsonl_import_is_idempotent(tmp_path):
    source = SQLiteStore(tmp_path / "source.sqlite")
    _seed_store(source)
    export_dir = tmp_path / "export"
    export_store(source, export_dir)

    target = SQLiteStore(tmp_path / "target.sqlite")
    target.init_db()
    import_jsonl_bundle(target, export_dir)
    first_count = len(target.iter_nodes(include_inactive=True))
    import_jsonl_bundle(target, export_dir)

    assert len(target.iter_nodes(include_inactive=True)) == first_count


def test_jsonl_edge_metadata_roundtrip(tmp_path):
    source = SQLiteStore(tmp_path / "source.sqlite")
    _seed_store(source)
    edge = source.iter_edges()[0]
    export_dir = tmp_path / "export"
    export_store(source, export_dir)

    target = SQLiteStore(tmp_path / "target.sqlite")
    target.init_db()
    import_jsonl_bundle(target, export_dir)
    imported = target.get_edge(edge.id)

    assert imported is not None
    assert imported.reasoning_allowed is True
    assert imported.metadata["owner"] == "rgm"
    assert imported.metadata["edge_strength"] == "strong"


def test_extraction_confidence_roundtrip(tmp_path):
    source = SQLiteStore(tmp_path / "source.sqlite")
    claim, _ = _seed_store(source)
    export_dir = tmp_path / "export"
    export_store(source, export_dir)

    target = SQLiteStore(tmp_path / "target.sqlite")
    target.init_db()
    import_jsonl_bundle(target, export_dir)
    imported = target.get_node(claim.id)

    assert imported is not None
    assert imported.extraction_confidence == 0.81


def test_import_old_node_jsonl_without_extraction_confidence(tmp_path):
    export_dir = tmp_path / "old"
    old_node = {
        "id": "node:old",
        "type": "SessionNote",
        "layer": "lightweight",
        "scope": "global",
        "project": None,
        "source_system": "test",
        "title": None,
        "content": "Old JSONL node without extraction confidence.",
        "importance": 0.5,
        "confidence": 1.0,
        "status": "active",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": None,
        "metadata": {},
    }
    write_jsonl(export_dir / "nodes.jsonl", [old_node])
    write_jsonl(export_dir / "edges.jsonl", [])
    write_jsonl(export_dir / "chunks.jsonl", [])
    store = SQLiteStore(tmp_path / "target.sqlite")
    store.init_db()

    import_jsonl_bundle(store, export_dir)
    imported = store.get_node("node:old")

    assert imported is not None
    assert imported.extraction_confidence is None
    assert read_jsonl(export_dir / "nodes.jsonl")[0]["id"] == "node:old"
