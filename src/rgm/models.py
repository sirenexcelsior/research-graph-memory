from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join(str(part) for part in parts)
    digest = sha256(payload.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}:{digest}"


def random_id(prefix: str) -> str:
    return f"{prefix}:{uuid4().hex}"


class Node(BaseModel):
    id: str = Field(default_factory=lambda: random_id("node"))
    type: str
    layer: str
    scope: str = "global"
    project: str | None = None
    source_system: str = "manual"
    title: str | None = None
    content: str
    importance: float = 0.5
    confidence: float = 1.0
    status: str = "active"
    created_at: str = Field(default_factory=utc_now)
    updated_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    id: str = Field(default_factory=lambda: random_id("edge"))
    source: str
    relation: str
    target: str
    layer: str | None = None
    confidence: float = 1.0
    semantic_strength: float = 0.5
    traversable: bool = True
    reasoning_allowed: bool = False
    source_rule: str | None = None
    created_at: str = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    id: str = Field(default_factory=lambda: random_id("chunk"))
    doc_id: str
    text: str
    section: str | None = None
    page: int | None = None
    token_count: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecallRequest(BaseModel):
    query: str
    intent: str | None = None
    project: str | None = None
    debug: bool = False
    limit: int = 8


class RecallContext(BaseModel):
    query: str
    intent: str
    document_context: list[dict[str, Any]] = Field(default_factory=list)
    research_context: list[dict[str, Any]] = Field(default_factory=list)
    operational_context: list[dict[str, Any]] = Field(default_factory=list)
    preference_context: list[dict[str, Any]] = Field(default_factory=list)
    session_context: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    graph_paths: list[dict[str, Any]] = Field(default_factory=list)
    debug_info: dict[str, Any] = Field(default_factory=dict)
