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
    assert stored.metadata["owner"] == "rgm"
    assert stored.metadata["edge_strength"] == "weak"
    assert validate_graph(db)["ok"] is True


def test_strong_edge_policy_metadata_is_owned_by_rgm(tmp_path):
    db = SQLiteStore(tmp_path / "rgm.sqlite")
    db.init_db()
    claim = Node(id="claim:test", type="Claim", layer="research", content="A claim.")
    evidence = Node(id="evidence:test", type="Evidence", layer="research", content="An evidence item.")
    db.upsert_node(claim)
    db.upsert_node(evidence)
    edge = db.upsert_edge(make_edge(claim.id, "SUPPORTED_BY", evidence.id, layer="research", source_rule="hermes_candidate"))

    assert edge.reasoning_allowed is True
    assert edge.metadata["owner"] == "rgm"
    assert edge.metadata["edge_strength"] == "strong"
    assert edge.metadata["created_by"] == "hermes"
    assert edge.metadata["accepted_by"] == "rgm_policy"
