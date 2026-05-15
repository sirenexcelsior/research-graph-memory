from rgm.graph.schema import make_edge
from rgm.memory.promote import promote
from rgm.memory.recall import recall
from rgm.memory.remember import remember
from rgm.models import Node
from rgm.storage.sqlite_store import SQLiteStore


def test_recall_returns_layered_context_and_promotions(tmp_path):
    db = SQLiteStore(tmp_path / "rgm.sqlite")
    decision = remember(
        "Use SQLite FTS5 as the durable keyword search baseline.",
        node_type="ProjectDecision",
        layer="lightweight",
        scope="project",
        project="research-graph-memory",
        store=db,
    )
    promoted = promote(decision.id, "Hypothesis", db)

    evidence = Node(
        id="evidence:test",
        type="Evidence",
        layer="research",
        scope="project",
        project="research-graph-memory",
        source_system="test",
        content="FTS5 is available in the bundled SQLite build.",
    )
    db.upsert_node(evidence)
    db.upsert_edge(make_edge(promoted["promoted"]["id"], "SUPPORTED_BY", evidence.id, layer="research"))

    context = recall("What evidence supports SQLite FTS5?", project="research-graph-memory", store=db)

    assert context.intent == "research_evidence"
    assert context.research_context
    assert context.evidence
    assert context.debug_info["max_hops"] == 2

