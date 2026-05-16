from __future__ import annotations

from pathlib import Path

from rgm.adapters.holographic import import_holographic
from rgm.adapters.markdown import ingest_markdown
from rgm.eval.runner import load_eval_cases, run_eval_file
from rgm.storage.sqlite_store import SQLiteStore


ROOT = Path(__file__).resolve().parents[1]


def test_eval_cases_load() -> None:
    eval_files = sorted((ROOT / "tests" / "eval").glob("*_queries.jsonl"))

    assert len(eval_files) >= 9
    for path in eval_files:
        cases = load_eval_cases(path)
        assert cases, path
        assert all(case.expected_positive is not None for case in cases)
        assert all(case.expected_negative is not None for case in cases)


def test_smoke_eval_runner_scores_demo_corpus(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "eval.sqlite")
    store.init_db()
    import_holographic(ROOT / "examples" / "synthetic_holographic.json", store=store)
    ingest_markdown(ROOT / "examples" / "synthetic_notes", store=store, project="demo", extractor_provider="rule_based")

    summary = run_eval_file(
        ROOT / "tests" / "eval" / "smoke_queries.jsonl",
        store=store,
        project="demo",
        mode="hybrid_graph",
        limit=10,
    )

    assert summary.case_count == 5
    assert summary.recall_at_k >= 0.8
    assert summary.forbidden_leakage_rate == 0
    assert summary.avg_context_tokens > 0
