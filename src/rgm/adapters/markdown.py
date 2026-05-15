from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from rgm.extraction.providers import get_extractor
from rgm.graph.schema import make_edge
from rgm.models import Chunk, Node, stable_id
from rgm.storage.sqlite_store import SQLiteStore

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
STOPWORDS = {
    "about",
    "after",
    "also",
    "because",
    "before",
    "could",
    "from",
    "have",
    "into",
    "more",
    "that",
    "their",
    "there",
    "this",
    "with",
    "would",
    "should",
    "when",
    "where",
    "which",
    "research",
    "memory",
}


def markdown_files(path: str | Path) -> list[Path]:
    source = Path(path)
    if source.is_dir():
        return sorted(source.rglob("*.md"))
    return [source]


def first_heading(markdown: str, fallback: str) -> str:
    match = HEADING_RE.search(markdown)
    return match.group(2).strip() if match else fallback


def split_sections(markdown: str) -> list[tuple[str | None, str]]:
    matches = list(HEADING_RE.finditer(markdown))
    if not matches:
        return [(None, markdown.strip())] if markdown.strip() else []

    sections: list[tuple[str | None, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        title = match.group(2).strip()
        body = markdown[start:end].strip()
        text = f"{title}\n\n{body}".strip()
        if text:
            sections.append((title, text))
    return sections


def chunk_section(section: str | None, text: str, max_words: int = 220) -> list[tuple[str | None, str]]:
    words = text.split()
    if len(words) <= max_words:
        return [(section, text)]
    chunks: list[tuple[str | None, str]] = []
    for start in range(0, len(words), max_words):
        part = " ".join(words[start : start + max_words])
        chunks.append((section, part))
    return chunks


def slug(value: str) -> str:
    cleaned = re.sub(r"[^\w]+", "-", value.lower(), flags=re.UNICODE).strip("-")
    return cleaned[:80] or "concept"


def extract_keywords(text: str, section: str | None) -> list[tuple[str, str]]:
    concepts: list[tuple[str, str]] = []
    for link in WIKILINK_RE.findall(text):
        concepts.append((link.strip(), "markdown_wikilink"))
    if section:
        concepts.append((section.strip(), "markdown_heading"))

    words = [
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]{4,}", text)
        if word.lower() not in STOPWORDS
    ]
    for word, count in Counter(words).most_common(3):
        if count >= 1:
            concepts.append((word, "markdown_keyword"))

    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for name, rule in concepts:
        key = name.lower()
        if key and key not in seen:
            seen.add(key)
            unique.append((name, rule))
    return unique[:8]


def ingest_markdown(
    path: str | Path,
    store: SQLiteStore | None = None,
    project: str | None = None,
    extractor_provider: str | None = None,
) -> dict[str, int]:
    db = store or SQLiteStore()
    db.init_db()
    extractor = get_extractor(extractor_provider)
    counts = {"documents": 0, "chunks": 0, "concepts": 0, "claims": 0, "evidence": 0, "questions": 0, "hypotheses": 0, "tasks": 0, "edges": 0}

    for file_path in markdown_files(path):
        markdown = file_path.read_text(encoding="utf-8")
        title = first_heading(markdown, file_path.stem)
        doc_id = stable_id("doc", str(file_path.resolve()), markdown)
        doc = Node(
            id=doc_id,
            type="Document",
            layer="document",
            scope="document",
            project=project,
            source_system="markdown",
            title=title,
            content=markdown,
            metadata={"path": str(file_path)},
        )
        db.upsert_node(doc)
        counts["documents"] += 1

        chunk_index = 0
        for section, section_text in split_sections(markdown):
            for chunk_section_name, chunk_text in chunk_section(section, section_text):
                chunk_id = stable_id("chunk", doc_id, chunk_index, chunk_text)
                chunk = Chunk(
                    id=chunk_id,
                    doc_id=doc_id,
                    text=chunk_text,
                    section=chunk_section_name,
                    token_count=len(chunk_text.split()),
                    metadata={"path": str(file_path), "chunk_index": chunk_index},
                )
                chunk_node = Node(
                    id=chunk_id,
                    type="Chunk",
                    layer="document",
                    scope="document",
                    project=project,
                    source_system="markdown",
                    title=chunk_section_name,
                    content=chunk_text,
                    metadata={"doc_id": doc_id, "path": str(file_path), "chunk_index": chunk_index},
                )
                db.upsert_chunk(chunk)
                db.upsert_node(chunk_node)
                counts["chunks"] += 1

                for edge in [
                    make_edge(doc_id, "HAS_CHUNK", chunk_id, layer="document", source_rule="markdown_ingest"),
                    make_edge(chunk_id, "PART_OF", doc_id, layer="document", source_rule="markdown_ingest"),
                ]:
                    db.upsert_edge(edge)
                    counts["edges"] += 1

                for concept_name, source_rule in extract_keywords(chunk_text, chunk_section_name):
                    concept_id = f"concept:{slug(concept_name)}"
                    existing = db.get_node(concept_id)
                    if existing is None:
                        concept = Node(
                            id=concept_id,
                            type="Concept",
                            layer="research",
                            scope="project" if project else "global",
                            project=project,
                            source_system="markdown",
                            title=concept_name,
                            content=concept_name,
                            confidence=0.7,
                            metadata={"created_from": source_rule},
                        )
                        db.upsert_node(concept)
                        counts["concepts"] += 1
                    db.upsert_edge(
                        make_edge(
                            chunk_id,
                            "MENTIONS",
                            concept_id,
                            layer="research",
                            source_rule=source_rule,
                            confidence=0.7,
                        )
                    )
                    counts["edges"] += 1

                if extractor is not None:
                    extraction = extractor.extract(chunk=chunk, chunk_node=chunk_node, document=doc)
                    for node in extraction.nodes:
                        db.upsert_node(node)
                        if node.type == "Claim":
                            counts["claims"] += 1
                        elif node.type == "Evidence":
                            counts["evidence"] += 1
                        elif node.type == "Question":
                            counts["questions"] += 1
                        elif node.type == "Hypothesis":
                            counts["hypotheses"] += 1
                        elif node.type == "Task":
                            counts["tasks"] += 1
                    for edge in extraction.edges:
                        db.upsert_edge(edge)
                        counts["edges"] += 1

                chunk_index += 1
    return counts
