from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from rgm.extraction.base import ExtractionResult
from rgm.models import Chunk, Edge, Node


@dataclass
class HermesExtractor:
    config: dict
    name: str = "hermes"

    def extract(self, *, chunk: Chunk, chunk_node: Node, document: Node) -> ExtractionResult:
        endpoint = self.config.get("endpoint")
        if not endpoint:
            raise RuntimeError("Hermes extractor endpoint is not configured")
        timeout = float(self.config.get("timeout_seconds", 30))
        max_chars = int(self.config.get("max_chunk_chars", 4000))
        payload = {
            "chunk": chunk.model_dump(mode="json") | {"text": chunk.text[:max_chars]},
            "chunk_node": chunk_node.model_dump(mode="json"),
            "document": {
                "id": document.id,
                "type": document.type,
                "layer": document.layer,
                "scope": document.scope,
                "project": document.project,
                "source_system": document.source_system,
                "title": document.title,
                "metadata": document.metadata,
            },
            "expected_schema": {
                "nodes": ["Claim", "Evidence", "Hypothesis", "Question", "Task"],
                "edges": ["STATES", "SUGGESTS", "SUPPORTED_BY", "CONTRADICTED_BY", "EVIDENCE_FOR", "MOTIVATES", "GENERATES", "NEXT_STEP_FOR"],
            },
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data: Any = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"Hermes extractor request failed: {exc}") from exc

        nodes = [Node(**row) for row in data.get("nodes", [])]
        edges = [Edge(**row) for row in data.get("edges", [])]
        return ExtractionResult(nodes=nodes, edges=edges, metadata={"provider": self.name, "raw": data.get("metadata", {})})

