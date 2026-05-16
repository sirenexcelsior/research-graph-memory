from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


EvalMode = Literal["fts5", "dense", "hybrid", "hybrid_graph"]


class NodeExpectation(BaseModel):
    id: str | None = None
    type: str | None = None
    layer: str | None = None
    title_contains: str | None = None
    content_contains: str | None = None
    project: str | None = None


class ChunkExpectation(BaseModel):
    id: str | None = None
    text_contains: str | None = None
    section_contains: str | None = None


class PathExpectation(BaseModel):
    from_node: str | None = Field(default=None, alias="from")
    edge: str
    to: str | None = None


class ExpectedPositive(BaseModel):
    nodes: list[str] = Field(default_factory=list)
    chunks: list[str] = Field(default_factory=list)
    edge_types: list[str] = Field(default_factory=list)
    paths: list[PathExpectation] = Field(default_factory=list)
    node_expectations: list[NodeExpectation] = Field(default_factory=list)
    chunk_expectations: list[ChunkExpectation] = Field(default_factory=list)


class ExpectedNegative(BaseModel):
    nodes: list[str] = Field(default_factory=list)
    chunks: list[str] = Field(default_factory=list)
    edge_types: list[str] = Field(default_factory=list)
    node_expectations: list[NodeExpectation] = Field(default_factory=list)
    chunk_expectations: list[ChunkExpectation] = Field(default_factory=list)


class EvalMetricsConfig(BaseModel):
    recall_at_k: int = 10
    require_reasoning_path: bool = False
    max_context_tokens: int | None = None


class EvalCase(BaseModel):
    id: str
    category: str
    project: str | None = None
    query: str
    mode: EvalMode = "hybrid_graph"
    intent: str | None = None
    evaluation_target: str | None = None
    expected_positive: ExpectedPositive = Field(default_factory=ExpectedPositive)
    expected_negative: ExpectedNegative = Field(default_factory=ExpectedNegative)
    metrics: EvalMetricsConfig = Field(default_factory=EvalMetricsConfig)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalCaseResult(BaseModel):
    query_id: str
    category: str
    mode: str
    intent: str
    recall_at_k: float
    mrr: float
    evidence_hit: bool
    reasoning_path_hit: bool
    forbidden_leakage: int
    forbidden_leakage_rate: float
    cross_project_leakage: int
    context_tokens: int
    matched_positive: list[str] = Field(default_factory=list)
    matched_negative: list[str] = Field(default_factory=list)
    missing_positive: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class EvalSummary(BaseModel):
    mode: str
    case_count: int
    recall_at_k: float
    mrr: float
    evidence_hit_rate: float
    reasoning_path_hit_rate: float
    forbidden_leakage_rate: float
    cross_project_leakage_rate: float
    avg_context_tokens: float
    results: list[EvalCaseResult]
