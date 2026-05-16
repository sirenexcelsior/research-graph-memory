from __future__ import annotations

import pytest

from rgm.adapters.holographic import import_holographic
from rgm.graph.schema import make_edge
from rgm.memory.recall import recall
from rgm.models import Node
from rgm.storage.sqlite_store import SQLiteStore


def test_mentions_edge_is_excluded_from_research_reasoning_paths(tmp_path):
    store = SQLiteStore(tmp_path / "rgm.sqlite")
    claim = Node(id="claim:mentions", type="Claim", layer="research", content="Keyword governance needs evidence.")
    concept = Node(id="concept:mentions", type="Concept", layer="research", content="governance")
    store.init_db()
    store.upsert_node(claim)
    store.upsert_node(concept)
    edge = store.upsert_edge(make_edge(claim.id, "MENTIONS", concept.id, layer="research"))

    context = recall("Keyword evidence", intent="research_evidence", store=store)

    assert edge.reasoning_allowed is False
    assert all(edge.id not in path["edges"] for path in context.graph_paths)
    assert all(item["id"] != concept.id for item in context.research_context)


def test_related_to_edge_defaults_to_non_reasoning(tmp_path):
    store = SQLiteStore(tmp_path / "rgm.sqlite")
    source = Node(id="concept:a", type="Concept", layer="research", content="alpha")
    target = Node(id="concept:b", type="Concept", layer="research", content="beta")
    store.init_db()
    store.upsert_node(source)
    store.upsert_node(target)

    edge = store.upsert_edge(make_edge(source.id, "RELATED_TO", target.id, layer="research"))

    assert edge.reasoning_allowed is False
    assert edge.metadata["edge_strength"] == "weak"


@pytest.mark.parametrize("relation", ["SUPPORTED_BY", "CONTRADICTED_BY", "EVIDENCE_FOR"])
def test_strong_evidence_edges_are_reasoning_allowed(tmp_path, relation):
    store = SQLiteStore(tmp_path / "rgm.sqlite")
    claim = Node(id=f"claim:{relation}", type="Claim", layer="research", content=f"{relation} claim")
    evidence = Node(id=f"evidence:{relation}", type="Evidence", layer="research", content=f"{relation} evidence")
    store.init_db()
    store.upsert_node(claim)
    store.upsert_node(evidence)
    source, target = (evidence.id, claim.id) if relation == "EVIDENCE_FOR" else (claim.id, evidence.id)

    edge = store.upsert_edge(make_edge(source, relation, target, layer="research"))

    assert edge.reasoning_allowed is True
    assert edge.metadata["edge_strength"] == "strong"
    assert edge.metadata["owner"] == "rgm"


@pytest.mark.parametrize("node_type", ["Preference", "ToolConfig", "WorkflowHint"])
def test_lightweight_operational_nodes_cannot_serve_as_evidence(tmp_path, node_type):
    store = SQLiteStore(tmp_path / "rgm.sqlite")
    claim = Node(id=f"claim:{node_type}", type="Claim", layer="research", content="A claim needs real evidence.")
    lightweight = Node(id=f"light:{node_type}", type=node_type, layer="lightweight", content="Operational memory.")
    store.init_db()
    store.upsert_node(claim)
    store.upsert_node(lightweight)

    with pytest.raises(ValueError):
        store.upsert_edge(make_edge(lightweight.id, "EVIDENCE_FOR", claim.id, layer="cross"))


def test_holographic_generated_edges_are_marked_weak(tmp_path):
    store = SQLiteStore(tmp_path / "rgm.sqlite")
    records = tmp_path / "holographic.json"
    records.write_text(
        """
        [
          {"id":"p","category":"user_pref","project":"demo","content":"Prefer structured JSON summaries."},
          {"id":"w","category":"tool","project":"demo","content":"Use deterministic workflow exports."}
        ]
        """,
        encoding="utf-8",
    )

    result = import_holographic(records, store=store)
    edges = store.iter_edges()

    assert result["edges"] >= 1
    assert all(edge.metadata["owner"] == "rgm" for edge in edges)
    assert all(edge.metadata["edge_strength"] == "weak" for edge in edges)


def test_manual_non_strong_edge_defaults_to_weak(tmp_path):
    store = SQLiteStore(tmp_path / "rgm.sqlite")
    preference = Node(id="pref:manual", type="Preference", layer="lightweight", content="Prefer concise output.")
    hint = Node(id="hint:manual", type="WorkflowHint", layer="lightweight", content="Use concise summaries.")
    store.init_db()
    store.upsert_node(preference)
    store.upsert_node(hint)

    edge = store.upsert_edge(make_edge(preference.id, "APPLIES_TO", hint.id, layer="lightweight"))

    assert edge.metadata["edge_strength"] == "weak"
    assert edge.metadata["owner"] == "rgm"
