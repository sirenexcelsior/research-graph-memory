from __future__ import annotations

from rgm.graph.schema import LIGHTWEIGHT_TYPES, RESEARCH_TYPES, layer_for_type


def normalize_layer(node_type: str, requested_layer: str | None = None) -> str:
    inferred = layer_for_type(node_type)
    if requested_layer:
        return requested_layer
    return inferred


def validate_manual_write(node_type: str, layer: str) -> None:
    if layer == "lightweight" and node_type not in LIGHTWEIGHT_TYPES:
        raise ValueError(f"{node_type} is not a lightweight memory type")
    if layer == "research" and node_type not in RESEARCH_TYPES:
        raise ValueError(f"{node_type} is not a research memory type")

