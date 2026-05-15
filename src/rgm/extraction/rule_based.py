from __future__ import annotations

import re
from dataclasses import dataclass

from rgm.extraction.base import ExtractionResult
from rgm.graph.schema import make_edge
from rgm.models import Chunk, Node, stable_id

DEFAULT_CLAIM_MARKERS = [
    "Claim:",
    "Conclusion:",
    "Definition:",
    "Theorem:",
    "Lemma:",
    "Proposition:",
    "Corollary:",
    "定义",
    "定理",
    "引理",
    "命题",
    "推论",
    "公式",
    "判据",
    "核心区分",
]
DEFAULT_EVIDENCE_MARKERS = ["Evidence:", "出处", "引用", "俄文原文", "book_ref"]
DEFAULT_QUESTION_MARKERS = ["Question:", "问题", "待验证", "未知"]
DEFAULT_HYPOTHESIS_MARKERS = ["Hypothesis:", "假设", "猜想", "可能"]
DEFAULT_TASK_MARKERS = ["TODO", "Next:", "下一步", "待补"]

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*", re.DOTALL)
BLOCKQUOTE_RE = re.compile(r"(?:^>.*(?:\n|$))+", re.MULTILINE)
EXPLICIT_LINE_RE = re.compile(
    r"^\s*(Claim|Conclusion|Definition|Theorem|Lemma|Proposition|Corollary|Evidence|Question|Hypothesis|TODO|Task|Next)\s*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


def _contains_any(text: str | None, markers: list[str]) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


def _clean_blockquote(text: str) -> str:
    lines = []
    for line in text.splitlines():
        cleaned = re.sub(r"^\s*>\s?", "", line).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines).strip()


def _first_paragraph(text: str, max_chars: int) -> str:
    cleaned_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if cleaned_lines:
                break
            continue
        if stripped.startswith("---") or stripped.startswith(">") or stripped.startswith("|"):
            continue
        if re.match(r"^\s*[-*]\s+", stripped):
            stripped = re.sub(r"^\s*[-*]\s+", "", stripped)
        cleaned_lines.append(stripped)
    payload = " ".join(cleaned_lines).strip()
    return payload[:max_chars]


def _frontmatter_excerpt(document: Node) -> str | None:
    match = FRONTMATTER_RE.search(document.content)
    if not match:
        return None
    frontmatter = match.group(1).strip()
    source_lines = []
    capture = False
    for line in frontmatter.splitlines():
        if line.startswith("book_ref:"):
            capture = True
            source_lines.append(line)
            continue
        if capture and (line.startswith(" ") or line.startswith("-")):
            source_lines.append(line)
            continue
        if capture:
            break
    return "\n".join(source_lines).strip() or None


@dataclass
class RuleBasedResearchExtractor:
    config: dict
    name: str = "rule_based"

    def __post_init__(self) -> None:
        self.claim_markers = self.config.get("claim_markers") or DEFAULT_CLAIM_MARKERS
        self.evidence_markers = self.config.get("evidence_markers") or DEFAULT_EVIDENCE_MARKERS
        self.question_markers = self.config.get("question_markers") or DEFAULT_QUESTION_MARKERS
        self.hypothesis_markers = self.config.get("hypothesis_markers") or DEFAULT_HYPOTHESIS_MARKERS
        self.task_markers = self.config.get("task_markers") or DEFAULT_TASK_MARKERS
        self.max_claim_chars = int(self.config.get("max_claim_chars", 1200))
        self.max_evidence_chars = int(self.config.get("max_evidence_chars", 1600))

    def extract(self, *, chunk: Chunk, chunk_node: Node, document: Node) -> ExtractionResult:
        result = ExtractionResult(metadata={"provider": self.name})
        explicit_nodes = self._extract_explicit_lines(chunk, chunk_node, document)
        result.nodes.extend(explicit_nodes.nodes)
        result.edges.extend(explicit_nodes.edges)

        evidence_nodes = self._extract_evidence(chunk, chunk_node, document)
        result.nodes.extend(evidence_nodes)
        for evidence in evidence_nodes:
            result.edges.append(make_edge(chunk_node.id, "STATES", evidence.id, layer="research", source_rule=evidence.metadata.get("source_rule", "rule_based_evidence")))

        claim = self._extract_heading_claim(chunk, chunk_node, document)
        if claim is not None:
            result.nodes.append(claim)
            result.edges.append(make_edge(chunk_node.id, "STATES", claim.id, layer="research", source_rule="rule_based_claim"))
            for evidence in evidence_nodes:
                result.edges.append(make_edge(claim.id, "SUPPORTED_BY", evidence.id, layer="research", source_rule="rule_based_local_evidence"))
                result.edges.append(make_edge(evidence.id, "EVIDENCE_FOR", claim.id, layer="research", source_rule="rule_based_local_evidence"))

        question_or_task = self._extract_question_or_task(chunk, chunk_node, document)
        result.nodes.extend(question_or_task.nodes)
        result.edges.extend(question_or_task.edges)

        return result

    def _node(self, *, prefix: str, node_type: str, content: str, chunk: Chunk, document: Node, title: str | None, confidence: float, rule: str) -> Node:
        return Node(
            id=stable_id(prefix, document.id, chunk.id, node_type, title or "", content),
            type=node_type,
            layer="research",
            scope="project" if document.project else "global",
            project=document.project,
            source_system="markdown_extractor",
            title=title,
            content=content,
            confidence=confidence,
            metadata={
                "doc_id": document.id,
                "chunk_id": chunk.id,
                "section": chunk.section,
                "source_rule": rule,
                "document_title": document.title,
                "document_path": document.metadata.get("path"),
            },
        )

    def _extract_explicit_lines(self, chunk: Chunk, chunk_node: Node, document: Node) -> ExtractionResult:
        result = ExtractionResult()
        for match in EXPLICIT_LINE_RE.finditer(chunk.text):
            marker = match.group(1).lower()
            payload = match.group(2).strip()
            if not payload:
                continue
            if marker in {"evidence"}:
                node_type = "Evidence"
                relation = "STATES"
            elif marker in {"question"}:
                node_type = "Question"
                relation = "STATES"
            elif marker in {"hypothesis"}:
                node_type = "Hypothesis"
                relation = "SUGGESTS"
            elif marker in {"todo", "task", "next"}:
                node_type = "Task"
                relation = "STATES"
            else:
                node_type = "Claim"
                relation = "STATES"
            node = self._node(
                prefix=node_type.lower(),
                node_type=node_type,
                content=payload[: self.max_claim_chars],
                chunk=chunk,
                document=document,
                title=chunk.section,
                confidence=0.75,
                rule="rule_based_explicit_marker",
            )
            result.nodes.append(node)
            result.edges.append(make_edge(chunk_node.id, relation, node.id, layer="research", source_rule="rule_based_explicit_marker"))
        return result

    def _extract_evidence(self, chunk: Chunk, chunk_node: Node, document: Node) -> list[Node]:
        _ = chunk_node
        evidence_nodes: list[Node] = []
        for match in BLOCKQUOTE_RE.finditer(chunk.text):
            content = _clean_blockquote(match.group(0))[: self.max_evidence_chars]
            if len(content) < 20:
                continue
            evidence_nodes.append(
                self._node(
                    prefix="evidence",
                    node_type="Evidence",
                    content=content,
                    chunk=chunk,
                    document=document,
                    title=chunk.section,
                    confidence=0.8,
                    rule="rule_based_blockquote",
                )
            )

        frontmatter = _frontmatter_excerpt(document)
        if frontmatter and (_contains_any(chunk.section, self.claim_markers) or _contains_any(chunk.text[:220], self.claim_markers)):
            evidence_nodes.append(
                self._node(
                    prefix="evidence",
                    node_type="Evidence",
                    content=frontmatter[: self.max_evidence_chars],
                    chunk=chunk,
                    document=document,
                    title=f"{document.title} source",
                    confidence=0.7,
                    rule="rule_based_frontmatter_book_ref",
                )
            )

        return evidence_nodes

    def _extract_heading_claim(self, chunk: Chunk, chunk_node: Node, document: Node) -> Node | None:
        _ = chunk_node
        explicit_claim_exists = bool(EXPLICIT_LINE_RE.search(chunk.text))
        if explicit_claim_exists:
            return None
        if not _contains_any(chunk.section, self.claim_markers) and not _contains_any(chunk.text[:220], self.claim_markers):
            return None
        content = _first_paragraph(chunk.text, self.max_claim_chars)
        if len(content) < 20:
            content = chunk.text[: self.max_claim_chars].strip()
        if len(content) < 20:
            return None
        return self._node(
            prefix="claim",
            node_type="Claim",
            content=content,
            chunk=chunk,
            document=document,
            title=chunk.section,
            confidence=0.72,
            rule="rule_based_heading_claim",
        )

    def _extract_question_or_task(self, chunk: Chunk, chunk_node: Node, document: Node) -> ExtractionResult:
        result = ExtractionResult()
        if _contains_any(chunk.text, self.question_markers):
            content = _first_paragraph(chunk.text, self.max_claim_chars) or chunk.text[: self.max_claim_chars]
            node = self._node(
                prefix="question",
                node_type="Question",
                content=content,
                chunk=chunk,
                document=document,
                title=chunk.section,
                confidence=0.65,
                rule="rule_based_question_marker",
            )
            result.nodes.append(node)
            result.edges.append(make_edge(chunk_node.id, "STATES", node.id, layer="research", source_rule="rule_based_question_marker"))
        if _contains_any(chunk.text, self.hypothesis_markers):
            content = _first_paragraph(chunk.text, self.max_claim_chars) or chunk.text[: self.max_claim_chars]
            node = self._node(
                prefix="hypothesis",
                node_type="Hypothesis",
                content=content,
                chunk=chunk,
                document=document,
                title=chunk.section,
                confidence=0.6,
                rule="rule_based_hypothesis_marker",
            )
            result.nodes.append(node)
            result.edges.append(make_edge(chunk_node.id, "SUGGESTS", node.id, layer="research", source_rule="rule_based_hypothesis_marker"))
        if _contains_any(chunk.text, self.task_markers):
            content = _first_paragraph(chunk.text, self.max_claim_chars) or chunk.text[: self.max_claim_chars]
            node = self._node(
                prefix="task",
                node_type="Task",
                content=content,
                chunk=chunk,
                document=document,
                title=chunk.section,
                confidence=0.65,
                rule="rule_based_task_marker",
            )
            result.nodes.append(node)
            result.edges.append(make_edge(node.id, "NEXT_STEP_FOR", chunk_node.id, layer="cross", source_rule="rule_based_task_marker"))
        return result
