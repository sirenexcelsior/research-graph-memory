from __future__ import annotations

from rgm.adapters.markdown import ingest_markdown
from rgm.graph.schema import make_edge
from rgm.memory.recall import recall
from rgm.memory.remember import remember
from rgm.models import Node
from rgm.storage.sqlite_store import SQLiteStore


def _all_context_items(context):
    payload = context.model_dump(mode="json")
    for bucket in [
        "document_context",
        "research_context",
        "operational_context",
        "preference_context",
        "session_context",
        "evidence",
    ]:
        yield from payload[bucket]


def test_recall_does_not_leak_across_projects(tmp_path):
    store = SQLiteStore(tmp_path / "rgm.sqlite")
    a_note = tmp_path / "a.md"
    b_note = tmp_path / "b.md"
    a_note.write_text("# Alpha\n\nProjectAlphaOnly isolation token.\n", encoding="utf-8")
    b_note.write_text("# Beta\n\nProjectBetaOnly isolation token.\n", encoding="utf-8")
    ingest_markdown(a_note, store=store, project="project_a")
    ingest_markdown(b_note, store=store, project="project_b")

    context = recall("isolation token", project="project_a", intent="research_evidence", store=store)

    assert any(item["project"] == "project_a" for item in _all_context_items(context))
    assert all(item["project"] in {None, "project_a"} for item in _all_context_items(context))
    assert all("ProjectBetaOnly" not in item.get("content", "") for item in _all_context_items(context))


def test_remember_sets_project_field(tmp_path):
    store = SQLiteStore(tmp_path / "rgm.sqlite")

    node = remember("Project-specific decision.", node_type="ProjectDecision", project="foo", store=store)

    saved = store.get_node(node.id)
    assert saved is not None
    assert saved.project == "foo"


def test_debug_explore_env_false_still_blocks_cross_project_expansion(tmp_path, monkeypatch):
    monkeypatch.setenv("RGM_ENABLE_DEBUG_EXPLORE", "false")
    store = SQLiteStore(tmp_path / "rgm.sqlite")
    a = Node(id="concept:a", type="Concept", layer="research", project="project_a", content="SharedDebugAlpha")
    b = Node(id="concept:b", type="Concept", layer="research", project="project_b", content="SharedDebugBeta")
    store.init_db()
    store.upsert_node(a)
    store.upsert_node(b)
    store.upsert_edge(make_edge(b.id, "RELATED_TO", a.id, layer="research"))

    context = recall("SharedDebugBeta", project="project_b", intent="debug_explore", debug=True, store=store)

    assert any(item["id"] == b.id for item in _all_context_items(context))
    assert all(item["id"] != a.id for item in _all_context_items(context))
    assert context.debug_info["cross_project_allowed"] is False


def test_debug_explore_env_true_allows_explicit_cross_project_expansion(tmp_path, monkeypatch):
    monkeypatch.setenv("RGM_ENABLE_DEBUG_EXPLORE", "true")
    store = SQLiteStore(tmp_path / "rgm.sqlite")
    a = Node(id="concept:a", type="Concept", layer="research", project="project_a", content="SharedDebugAlpha")
    b = Node(id="concept:b", type="Concept", layer="research", project="project_b", content="SharedDebugBeta")
    store.init_db()
    store.upsert_node(a)
    store.upsert_node(b)
    store.upsert_edge(make_edge(b.id, "RELATED_TO", a.id, layer="research"))

    context = recall("SharedDebugBeta", project="project_b", intent="debug_explore", debug=True, store=store)

    assert any(item["id"] == a.id for item in _all_context_items(context))
    assert context.debug_info["cross_project_allowed"] is True
