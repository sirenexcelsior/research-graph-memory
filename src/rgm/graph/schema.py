from __future__ import annotations

from rgm.models import Edge, stable_id

DOCUMENT_TYPES = {"Document", "Chunk"}
LIGHTWEIGHT_TYPES = {
    "Preference",
    "WorkflowHint",
    "ToolConfig",
    "ProjectState",
    "ProjectDecision",
    "Todo",
    "SessionNote",
}
RESEARCH_TYPES = {
    "Concept",
    "Claim",
    "Hypothesis",
    "Evidence",
    "Experiment",
    "Result",
    "Question",
    "Task",
}
NODE_TYPES = DOCUMENT_TYPES | LIGHTWEIGHT_TYPES | RESEARCH_TYPES
LAYERS = {"document", "lightweight", "research", "cross"}

REASONING_RELATIONS = {
    "SUPPORTED_BY",
    "CONTRADICTED_BY",
    "TESTED_BY",
    "PRODUCES",
    "EVIDENCE_FOR",
}
NON_REASONING_RELATIONS = {"MENTIONS", "RELATED_TO"}

RELATION_DEFAULTS = {
    "HAS_CHUNK": {"reasoning_allowed": False, "semantic_strength": 0.7},
    "PART_OF": {"reasoning_allowed": False, "semantic_strength": 0.7},
    "MENTIONS": {"reasoning_allowed": False, "semantic_strength": 0.4},
    "RELATED_TO": {"reasoning_allowed": False, "semantic_strength": 0.3},
    "STATES": {"reasoning_allowed": False, "semantic_strength": 0.6},
    "SUGGESTS": {"reasoning_allowed": False, "semantic_strength": 0.6},
    "SUPPORTED_BY": {"reasoning_allowed": True, "semantic_strength": 0.8},
    "CONTRADICTED_BY": {"reasoning_allowed": True, "semantic_strength": 0.8},
    "TESTED_BY": {"reasoning_allowed": True, "semantic_strength": 0.8},
    "PRODUCES": {"reasoning_allowed": True, "semantic_strength": 0.8},
    "EVIDENCE_FOR": {"reasoning_allowed": True, "semantic_strength": 0.8},
    "APPLIES_TO": {"reasoning_allowed": False, "semantic_strength": 0.6},
    "USED_BY": {"reasoning_allowed": False, "semantic_strength": 0.6},
    "AFFECTS": {"reasoning_allowed": False, "semantic_strength": 0.6},
    "NEXT_STEP_FOR": {"reasoning_allowed": False, "semantic_strength": 0.6},
    "PROMOTED_TO": {"reasoning_allowed": False, "semantic_strength": 0.9},
    "MOTIVATES": {"reasoning_allowed": True, "semantic_strength": 0.7},
    "GENERATES": {"reasoning_allowed": True, "semantic_strength": 0.7},
}

NON_EVIDENCE_TYPES = {"Preference", "ToolConfig", "WorkflowHint"}


def layer_for_type(node_type: str) -> str:
    if node_type in DOCUMENT_TYPES:
        return "document"
    if node_type in LIGHTWEIGHT_TYPES:
        return "lightweight"
    if node_type in RESEARCH_TYPES:
        return "research"
    return "lightweight"


def make_edge(
    source: str,
    relation: str,
    target: str,
    *,
    layer: str | None = None,
    source_rule: str | None = None,
    confidence: float = 1.0,
    metadata: dict | None = None,
) -> Edge:
    defaults = RELATION_DEFAULTS.get(relation, {"reasoning_allowed": False, "semantic_strength": 0.5})
    return Edge(
        id=stable_id("edge", source, relation, target, source_rule or ""),
        source=source,
        relation=relation,
        target=target,
        layer=layer,
        confidence=confidence,
        semantic_strength=defaults["semantic_strength"],
        reasoning_allowed=defaults["reasoning_allowed"],
        source_rule=source_rule,
        metadata=metadata or {},
    )


def enforce_edge_rules(edge: Edge) -> Edge:
    defaults = RELATION_DEFAULTS.get(edge.relation)
    if defaults:
        edge.reasoning_allowed = bool(defaults["reasoning_allowed"])
        edge.semantic_strength = float(defaults["semantic_strength"])
    if edge.relation in NON_REASONING_RELATIONS:
        edge.reasoning_allowed = False
    return edge

