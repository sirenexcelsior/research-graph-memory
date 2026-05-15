from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from rgm.models import Chunk, Edge, Node


class ExtractionResult(BaseModel):
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ExtractorProvider(Protocol):
    name: str

    def extract(self, *, chunk: Chunk, chunk_node: Node, document: Node) -> ExtractionResult:
        ...

