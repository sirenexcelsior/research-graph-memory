from __future__ import annotations

from dataclasses import dataclass

from rgm.graph.schema import NODE_TYPES, NON_EVIDENCE_TYPES
from rgm.storage.sqlite_store import SQLiteStore


@dataclass
class ValidationIssue:
    severity: str
    message: str
    object_id: str


def validate_graph(store: SQLiteStore | None = None) -> dict:
    db = store or SQLiteStore()
    db.init_db()
    issues: list[ValidationIssue] = []
    nodes = {node.id: node for node in db.iter_nodes(include_inactive=True)}

    for node in nodes.values():
        if node.type not in NODE_TYPES:
            issues.append(ValidationIssue("warning", f"Unknown node type {node.type}", node.id))
        if node.type in NON_EVIDENCE_TYPES and node.layer == "research":
            issues.append(ValidationIssue("error", f"{node.type} cannot be research evidence", node.id))

    for edge in db.iter_edges():
        source = nodes.get(edge.source)
        target = nodes.get(edge.target)
        if source is None:
            issues.append(ValidationIssue("error", "Edge source is missing", edge.id))
        if target is None:
            issues.append(ValidationIssue("error", "Edge target is missing", edge.id))
        if edge.relation == "MENTIONS" and edge.reasoning_allowed:
            issues.append(ValidationIssue("error", "MENTIONS cannot allow reasoning", edge.id))
        if edge.relation == "RELATED_TO" and edge.reasoning_allowed:
            issues.append(ValidationIssue("error", "RELATED_TO cannot allow reasoning by default", edge.id))
        if edge.relation in {"SUPPORTED_BY", "CONTRADICTED_BY", "EVIDENCE_FOR"}:
            if target and target.type in NON_EVIDENCE_TYPES:
                issues.append(ValidationIssue("error", f"{target.type} cannot serve as Evidence", edge.id))
            if source and source.type in NON_EVIDENCE_TYPES:
                issues.append(ValidationIssue("error", f"{source.type} cannot serve as Evidence", edge.id))

    errors = [issue for issue in issues if issue.severity == "error"]
    return {
        "ok": len(errors) == 0,
        "issue_count": len(issues),
        "issues": [issue.__dict__ for issue in issues],
    }
