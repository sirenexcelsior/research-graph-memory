from rgm.adapters.markdown import ingest_markdown
from rgm.storage.sqlite_store import SQLiteStore


def test_markdown_ingest_creates_document_chunks_and_concepts(tmp_path):
    db = SQLiteStore(tmp_path / "rgm.sqlite")
    note = tmp_path / "note.md"
    note.write_text(
        "# Graph Memory\n\nThis note links to [[Holographic Memory]] and discusses evidence retrieval.\n",
        encoding="utf-8",
    )

    result = ingest_markdown(note, db, project="research-graph-memory")
    nodes = db.iter_nodes()
    edges = db.iter_edges()

    assert result["documents"] == 1
    assert result["chunks"] >= 1
    assert any(node.type == "Document" for node in nodes)
    assert any(node.type == "Chunk" for node in nodes)
    assert any(node.id == "concept:holographic-memory" for node in nodes)
    mentions = [edge for edge in edges if edge.relation == "MENTIONS"]
    assert mentions
    assert all(edge.reasoning_allowed is False for edge in mentions)

