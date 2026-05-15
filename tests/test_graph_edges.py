from rgm.graph.schema import make_edge
from rgm.graph.validation import validate_graph
from rgm.models import Node
from rgm.storage.sqlite_store import SQLiteStore


def test_graph_validation_rejects_reasoning_mentions(tmp_path):
    db = SQLiteStore(tmp_path / "rgm.sqlite")
    db.init_db()
    chunk = Node(id="chunk:test", type="Chunk", layer="document", content="mentions Alpha")
    concept = Node(id="concept:alpha", type="Concept", layer="research", content="Alpha")
    db.upsert_node(chunk)
    db.upsert_node(concept)
    edge = make_edge(chunk.id, "MENTIONS", concept.id, layer="research")
    edge.reasoning_allowed = True
    db.upsert_edge(edge)

    stored = db.get_edge(edge.id)
    assert stored.reasoning_allowed is False
    assert validate_graph(db)["ok"] is True

