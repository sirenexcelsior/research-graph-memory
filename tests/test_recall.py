from rgm.graph.schema import make_edge
from rgm.adapters.markdown import ingest_markdown
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


def test_recall_context_dedupes_evidence_and_paths(tmp_path):
    db = SQLiteStore(tmp_path / "rgm.sqlite")
    claim = Node(id="claim:test", type="Claim", layer="research", content="Keyword search is useful.")
    evidence = Node(id="evidence:test", type="Evidence", layer="research", content="SQLite FTS5 supports keyword search.")
    db.init_db()
    db.upsert_node(claim)
    db.upsert_node(evidence)
    db.upsert_edge(make_edge(claim.id, "SUPPORTED_BY", evidence.id, layer="research"))
    db.upsert_edge(make_edge(evidence.id, "EVIDENCE_FOR", claim.id, layer="research"))

    context = recall("What evidence supports keyword search?", store=db)

    evidence_ids = [item["id"] for item in context.evidence]
    research_ids = [item["id"] for item in context.research_context]
    path_keys = [(tuple(path["nodes"]), tuple(path["edges"])) for path in context.graph_paths]
    assert evidence_ids == list(dict.fromkeys(evidence_ids))
    assert evidence.id not in research_ids
    assert len(path_keys) == len(set(path_keys))
    assert len(context.graph_paths) <= context.debug_info["context_limits"]["graph_paths"]


def test_recall_document_context_respects_project_boundary(tmp_path):
    db = SQLiteStore(tmp_path / "rgm.sqlite")
    project_a = tmp_path / "project_a.md"
    project_b = tmp_path / "project_b.md"
    project_a.write_text("# Alpha Doc\n\nBoundaryToken belongs to project alpha.\n", encoding="utf-8")
    project_b.write_text("# Beta Doc\n\nBoundaryToken belongs to project beta.\n", encoding="utf-8")
    ingest_markdown(project_a, db, project="alpha")
    ingest_markdown(project_b, db, project="beta")

    context = recall("BoundaryToken", project="alpha", intent="research_evidence", store=db)

    assert context.document_context
    assert any(item["project"] == "alpha" for item in context.document_context)
    assert all(item["project"] in {None, "alpha"} for item in context.document_context)
    assert context.debug_info["cross_project_allowed"] is False
