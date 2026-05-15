from rgm.adapters.markdown import ingest_markdown
from rgm.graph.validation import validate_graph
from rgm.memory.recall import recall
from rgm.storage.sqlite_store import SQLiteStore


def test_rule_based_research_extraction_creates_claim_evidence_edges(tmp_path):
    db = SQLiteStore(tmp_path / "rgm.sqlite")
    note = tmp_path / "theorem.md"
    note.write_text(
        """---
title: Sample theorem
book_ref:
  - kb:sample
---

# Sample theorem

## 定理：Perfect codes

> A code is perfect when its Hamming balls partition the ambient space.

The Hamming code is a standard perfect code example.

## Question: open direction

Question: Can this construction be generalized?

TODO: compare with BCH codes.
""",
        encoding="utf-8",
    )

    result = ingest_markdown(note, db, project="GenMath", extractor_provider="rule_based")
    nodes = db.iter_nodes()
    edges = db.iter_edges()

    assert result["claims"] >= 1
    assert result["evidence"] >= 1
    assert result["questions"] >= 1
    assert result["tasks"] >= 1
    assert any(node.type == "Claim" for node in nodes)
    assert any(node.type == "Evidence" for node in nodes)
    assert any(edge.relation == "SUPPORTED_BY" and edge.reasoning_allowed for edge in edges)
    assert any(edge.relation == "EVIDENCE_FOR" and edge.reasoning_allowed for edge in edges)
    assert validate_graph(db)["ok"] is True

    context = recall("What evidence supports Hamming perfect codes?", project="GenMath", store=db)
    assert context.intent == "research_evidence"
    assert context.evidence

