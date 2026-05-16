from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from rgm.eval.models import (
    ChunkExpectation,
    EvalCase,
    EvalCaseResult,
    EvalSummary,
    NodeExpectation,
)
from rgm.memory.recall import recall
from rgm.models import Chunk, Edge
from rgm.storage.sqlite_store import SQLiteStore

CONTEXT_BUCKETS = (
    "evidence",
    "research_context",
    "operational_context",
    "preference_context",
    "session_context",
)


def load_eval_cases(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            try:
                cases.append(EvalCase.model_validate_json(raw))
            except Exception as exc:  # pragma: no cover - pydantic message is enough.
                raise ValueError(f"Invalid eval case in {path}:{line_no}: {exc}") from exc
    return cases


def run_eval_file(
    path: Path,
    *,
    store: SQLiteStore | None = None,
    project: str | None = None,
    mode: str | None = None,
    limit: int = 10,
) -> EvalSummary:
    db = store or SQLiteStore()
    db.init_db()
    cases = load_eval_cases(path)
    results = [
        run_eval_case(case, store=db, project=project or case.project, mode=mode or case.mode, limit=limit)
        for case in cases
    ]
    return _summarize(results, mode=mode or (cases[0].mode if cases else "hybrid_graph"))


def run_eval_case(
    case: EvalCase,
    *,
    store: SQLiteStore,
    project: str | None,
    mode: str,
    limit: int,
) -> EvalCaseResult:
    if mode in {"dense", "hybrid"}:
        notes = [f"Mode {mode!r} is a reserved sidecar mode in V0.1.2; falling back to FTS5 recall."]
    else:
        notes = []

    effective_limit = min(limit, case.metrics.recall_at_k)
    context = recall(
        case.query,
        intent=case.intent,
        project=project,
        debug=True,
        limit=effective_limit,
        store=store,
    )
    nodes = _flatten_context_nodes(context.model_dump(mode="json"))
    chunks = _seed_chunks(context.debug_info.get("seed_ids", []), store)
    edges = _context_edges(context.model_dump(mode="json"), store)

    matched_positive, missing_positive, positive_ranks = _positive_matches(case, nodes, chunks, edges)
    matched_negative = _negative_matches(case, nodes, chunks, edges)
    evidence_hit = any(node.get("type") in {"Evidence", "Result"} for node in nodes)
    reasoning_path_hit = _reasoning_path_hit(case, edges)
    context_tokens = _context_tokens(nodes, chunks)
    cross_project_leakage = _cross_project_leakage(nodes, project)
    target_count = max(1, len(matched_positive) + len(missing_positive))

    if case.metrics.max_context_tokens is not None and context_tokens > case.metrics.max_context_tokens:
        notes.append(f"context_tokens exceeded max_context_tokens={case.metrics.max_context_tokens}")

    return EvalCaseResult(
        query_id=case.id,
        category=case.category,
        mode=mode,
        intent=context.intent,
        recall_at_k=len(matched_positive) / target_count,
        mrr=_mrr(positive_ranks),
        evidence_hit=evidence_hit,
        reasoning_path_hit=reasoning_path_hit,
        forbidden_leakage=len(matched_negative),
        forbidden_leakage_rate=len(matched_negative) / max(1, len(_negative_targets(case))),
        cross_project_leakage=cross_project_leakage,
        context_tokens=context_tokens,
        matched_positive=matched_positive,
        matched_negative=matched_negative,
        missing_positive=missing_positive,
        notes=notes,
    )


def _flatten_context_nodes(context: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for bucket in CONTEXT_BUCKETS:
        for node in context.get(bucket, []):
            node_id = node.get("id")
            if node_id and node_id not in seen:
                seen.add(node_id)
                nodes.append(node)
    return nodes


def _seed_chunks(seed_ids: list[str], store: SQLiteStore) -> list[Chunk]:
    chunks: list[Chunk] = []
    seen: set[str] = set()
    for seed_id in seed_ids:
        chunk = store.get_chunk(seed_id)
        if chunk and chunk.id not in seen:
            seen.add(chunk.id)
            chunks.append(chunk)
    return chunks


def _context_edges(context: dict[str, Any], store: SQLiteStore) -> list[Edge]:
    edge_ids: list[str] = []
    for edge in context.get("debug_info", {}).get("reasoning_edges", []):
        edge_ids.append(edge["id"])
    for path in context.get("graph_paths", []):
        edge_ids.extend(path.get("edges", []))

    edges: list[Edge] = []
    seen: set[str] = set()
    for edge_id in edge_ids:
        if edge_id in seen:
            continue
        edge = store.get_edge(edge_id)
        if edge:
            seen.add(edge_id)
            edges.append(edge)
    return edges


def _positive_matches(
    case: EvalCase,
    nodes: list[dict[str, Any]],
    chunks: list[Chunk],
    edges: list[Edge],
) -> tuple[list[str], list[str], list[int]]:
    matched: list[str] = []
    missing: list[str] = []
    ranks: list[int] = []
    node_rank = {node["id"]: rank for rank, node in enumerate(nodes, start=1)}
    chunk_rank = {chunk.id: rank for rank, chunk in enumerate(chunks, start=1)}
    edge_types = {edge.relation for edge in edges}

    for node_id in case.expected_positive.nodes:
        if node_id in node_rank:
            matched.append(f"node:{node_id}")
            ranks.append(node_rank[node_id])
        else:
            missing.append(f"node:{node_id}")

    for expectation in case.expected_positive.node_expectations:
        label, rank = _match_node_expectation(expectation, nodes)
        if rank:
            matched.append(label)
            ranks.append(rank)
        else:
            missing.append(label)

    for chunk_id in case.expected_positive.chunks:
        if chunk_id in chunk_rank:
            matched.append(f"chunk:{chunk_id}")
            ranks.append(chunk_rank[chunk_id])
        else:
            missing.append(f"chunk:{chunk_id}")

    for expectation in case.expected_positive.chunk_expectations:
        label, rank = _match_chunk_expectation(expectation, chunks)
        if rank:
            matched.append(label)
            ranks.append(rank)
        else:
            missing.append(label)

    for edge_type in case.expected_positive.edge_types:
        if edge_type in edge_types:
            matched.append(f"edge_type:{edge_type}")
        else:
            missing.append(f"edge_type:{edge_type}")

    return matched, missing, ranks


def _negative_matches(case: EvalCase, nodes: list[dict[str, Any]], chunks: list[Chunk], edges: list[Edge]) -> list[str]:
    matched: list[str] = []
    node_ids = {node["id"] for node in nodes}
    chunk_ids = {chunk.id for chunk in chunks}
    edge_types = {edge.relation for edge in edges}

    for node_id in case.expected_negative.nodes:
        if node_id in node_ids:
            matched.append(f"node:{node_id}")
    for expectation in case.expected_negative.node_expectations:
        label, rank = _match_node_expectation(expectation, nodes)
        if rank:
            matched.append(label)
    for chunk_id in case.expected_negative.chunks:
        if chunk_id in chunk_ids:
            matched.append(f"chunk:{chunk_id}")
    for expectation in case.expected_negative.chunk_expectations:
        label, rank = _match_chunk_expectation(expectation, chunks)
        if rank:
            matched.append(label)
    for edge_type in case.expected_negative.edge_types:
        if edge_type in edge_types:
            matched.append(f"edge_type:{edge_type}")
    return matched


def _negative_targets(case: EvalCase) -> list[str]:
    return [
        *case.expected_negative.nodes,
        *case.expected_negative.chunks,
        *case.expected_negative.edge_types,
        *[expectation.model_dump_json() for expectation in case.expected_negative.node_expectations],
        *[expectation.model_dump_json() for expectation in case.expected_negative.chunk_expectations],
    ]


def _match_node_expectation(expectation: NodeExpectation, nodes: list[dict[str, Any]]) -> tuple[str, int | None]:
    label = _expectation_label("node", expectation.model_dump(exclude_none=True))
    for rank, node in enumerate(nodes, start=1):
        if expectation.id and node.get("id") != expectation.id:
            continue
        if expectation.type and node.get("type") != expectation.type:
            continue
        if expectation.layer and node.get("layer") != expectation.layer:
            continue
        if expectation.project and node.get("project") != expectation.project:
            continue
        if expectation.title_contains and not _contains_text(node.get("title") or "", expectation.title_contains):
            continue
        if expectation.content_contains and not _contains_text(node.get("content", ""), expectation.content_contains):
            continue
        return label, rank
    return label, None


def _match_chunk_expectation(expectation: ChunkExpectation, chunks: list[Chunk]) -> tuple[str, int | None]:
    label = _expectation_label("chunk", expectation.model_dump(exclude_none=True))
    for rank, chunk in enumerate(chunks, start=1):
        if expectation.id and chunk.id != expectation.id:
            continue
        if expectation.text_contains and not _contains_text(chunk.text, expectation.text_contains):
            continue
        if expectation.section_contains and not _contains_text(chunk.section or "", expectation.section_contains):
            continue
        return label, rank
    return label, None


def _expectation_label(prefix: str, payload: dict[str, Any]) -> str:
    return f"{prefix}:{json.dumps(payload, ensure_ascii=False, sort_keys=True)}"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def _contains_text(haystack: str, needle: str) -> bool:
    return _normalize_text(needle) in _normalize_text(haystack)


def _reasoning_path_hit(case: EvalCase, edges: list[Edge]) -> bool:
    if not case.metrics.require_reasoning_path:
        return any(edge.reasoning_allowed for edge in edges) or not case.expected_positive.paths
    if case.expected_positive.edge_types:
        allowed_types = {edge.relation for edge in edges if edge.reasoning_allowed}
        return bool(allowed_types.intersection(case.expected_positive.edge_types))
    return any(edge.reasoning_allowed for edge in edges)


def _context_tokens(nodes: list[dict[str, Any]], chunks: list[Chunk]) -> int:
    text = "\n".join(
        [str(node.get("title") or "") + "\n" + str(node.get("content") or "") for node in nodes]
        + [chunk.text for chunk in chunks]
    )
    return max(0, len(text) // 4)


def _cross_project_leakage(nodes: list[dict[str, Any]], project: str | None) -> int:
    if not project:
        return 0
    return sum(1 for node in nodes if node.get("project") not in {None, project})


def _mrr(ranks: list[int]) -> float:
    return 0.0 if not ranks else 1 / min(ranks)


def _summarize(results: list[EvalCaseResult], *, mode: str) -> EvalSummary:
    count = max(1, len(results))
    return EvalSummary(
        mode=mode,
        case_count=len(results),
        recall_at_k=sum(result.recall_at_k for result in results) / count,
        mrr=sum(result.mrr for result in results) / count,
        evidence_hit_rate=sum(1 for result in results if result.evidence_hit) / count,
        reasoning_path_hit_rate=sum(1 for result in results if result.reasoning_path_hit) / count,
        forbidden_leakage_rate=sum(result.forbidden_leakage_rate for result in results) / count,
        cross_project_leakage_rate=sum(1 for result in results if result.cross_project_leakage > 0) / count,
        avg_context_tokens=sum(result.context_tokens for result in results) / count,
        results=results,
    )
