from __future__ import annotations

from rgm.models import Edge

WEAK_RELATIONS = {
    "HAS_CHUNK",
    "PART_OF",
    "MENTIONS",
    "RELATED_TO",
    "STATES",
    "SUGGESTS",
    "APPLIES_TO",
    "USED_BY",
    "AFFECTS",
    "NEXT_STEP_FOR",
    "SIMILAR_TO",
    "SEMANTIC_NEIGHBOR",
}

STRONG_RELATIONS = {
    "SUPPORTED_BY",
    "CONTRADICTED_BY",
    "TESTED_BY",
    "PRODUCES",
    "EVIDENCE_FOR",
    "MOTIVATES",
    "GENERATES",
    "PROMOTED_TO",
}


def edge_strength_for_relation(relation: str) -> str:
    if relation in STRONG_RELATIONS:
        return "strong"
    return "weak"


def created_by_for_source_rule(source_rule: str | None) -> str:
    if not source_rule:
        return "unknown"
    lowered = source_rule.lower()
    if lowered.startswith("hermes"):
        return "hermes"
    if lowered.startswith("bge") or "embedding" in lowered:
        return "bge"
    if lowered.startswith("manual"):
        return "manual"
    return "rule"


def apply_edge_policy(edge: Edge) -> Edge:
    metadata = dict(edge.metadata or {})
    metadata.setdefault("owner", "rgm")
    metadata.setdefault("edge_strength", edge_strength_for_relation(edge.relation))
    metadata.setdefault("created_by", created_by_for_source_rule(edge.source_rule))
    metadata.setdefault("accepted_by", "rgm_policy")
    edge.metadata = metadata
    return edge

