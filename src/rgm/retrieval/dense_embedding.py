from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class Embedder(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


@dataclass
class DenseEmbeddingConfig:
    enabled: bool = False
    provider: str = "bge-m3"
    model_path: str | None = None


class DisabledEmbedder:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        _ = texts
        raise RuntimeError("Dense embedding is disabled in V0.1. Configure a BGE-M3 embedder later.")


def get_embedder(config: DenseEmbeddingConfig | None = None) -> Embedder:
    cfg = config or DenseEmbeddingConfig()
    if not cfg.enabled:
        return DisabledEmbedder()
    raise NotImplementedError("BGE-M3 dense retrieval is reserved for a later implementation.")

