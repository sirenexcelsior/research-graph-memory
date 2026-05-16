from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from rgm.config import RGMConfig
from rgm.graph.edge_policy import apply_edge_policy
from rgm.graph.schema import NON_EVIDENCE_TYPES, enforce_edge_rules
from rgm.models import Chunk, Edge, Node, utc_now


def _json_dumps(value: dict[str, Any]) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True)


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    return json.loads(value)


def _fts_query(query: str) -> str:
    tokens = re.findall(r"[\w]+", query, flags=re.UNICODE)
    tokens = [token for token in tokens if token.strip()]
    if not tokens:
        return '""'
    return " OR ".join(f'"{token}"' for token in tokens[:12])


class SQLiteStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        config = RGMConfig.load()
        self.db_path = Path(db_path or config.db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS nodes (
                  id TEXT PRIMARY KEY,
                  type TEXT NOT NULL,
                  layer TEXT NOT NULL,
                  scope TEXT,
                  project TEXT,
                  source_system TEXT,
                  title TEXT,
                  content TEXT NOT NULL,
                  importance REAL DEFAULT 0.5,
                  confidence REAL DEFAULT 1.0,
                  extraction_confidence REAL DEFAULT NULL,
                  status TEXT DEFAULT 'active',
                  created_at TEXT,
                  updated_at TEXT,
                  metadata_json TEXT
                );

                CREATE TABLE IF NOT EXISTS edges (
                  id TEXT PRIMARY KEY,
                  source TEXT NOT NULL,
                  relation TEXT NOT NULL,
                  target TEXT NOT NULL,
                  layer TEXT,
                  confidence REAL DEFAULT 1.0,
                  semantic_strength REAL DEFAULT 0.5,
                  traversable INTEGER DEFAULT 1,
                  reasoning_allowed INTEGER DEFAULT 0,
                  source_rule TEXT,
                  created_at TEXT,
                  metadata_json TEXT
                );

                CREATE TABLE IF NOT EXISTS chunks (
                  id TEXT PRIMARY KEY,
                  doc_id TEXT,
                  text TEXT NOT NULL,
                  section TEXT,
                  page INTEGER,
                  token_count INTEGER,
                  metadata_json TEXT
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts
                USING fts5(id UNINDEXED, title, content, type, layer, project);

                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
                USING fts5(id UNINDEXED, text, section);

                CREATE INDEX IF NOT EXISTS idx_nodes_type_layer ON nodes(type, layer);
                CREATE INDEX IF NOT EXISTS idx_nodes_project ON nodes(project);
                CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source);
                CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target);
                CREATE INDEX IF NOT EXISTS idx_edges_relation ON edges(relation);
                """
            )
            self._migrate_nodes_table(conn)

    def _migrate_nodes_table(self, conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(nodes)").fetchall()}
        if "extraction_confidence" not in columns:
            conn.execute("ALTER TABLE nodes ADD COLUMN extraction_confidence REAL DEFAULT NULL")

    def upsert_node(self, node: Node) -> Node:
        node.updated_at = node.updated_at or utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO nodes (
                  id, type, layer, scope, project, source_system, title, content,
                  importance, confidence, extraction_confidence, status, created_at, updated_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  type=excluded.type,
                  layer=excluded.layer,
                  scope=excluded.scope,
                  project=excluded.project,
                  source_system=excluded.source_system,
                  title=excluded.title,
                  content=excluded.content,
                  importance=excluded.importance,
                  confidence=excluded.confidence,
                  extraction_confidence=excluded.extraction_confidence,
                  status=excluded.status,
                  updated_at=excluded.updated_at,
                  metadata_json=excluded.metadata_json
                """,
                (
                    node.id,
                    node.type,
                    node.layer,
                    node.scope,
                    node.project,
                    node.source_system,
                    node.title,
                    node.content,
                    node.importance,
                    node.confidence,
                    node.extraction_confidence,
                    node.status,
                    node.created_at,
                    node.updated_at,
                    _json_dumps(node.metadata),
                ),
            )
            conn.execute("DELETE FROM nodes_fts WHERE id = ?", (node.id,))
            if node.status == "active":
                conn.execute(
                    "INSERT INTO nodes_fts(id, title, content, type, layer, project) VALUES (?, ?, ?, ?, ?, ?)",
                    (node.id, node.title or "", node.content, node.type, node.layer, node.project or ""),
                )
        return node

    def upsert_nodes(self, nodes: Iterable[Node]) -> int:
        count = 0
        for node in nodes:
            self.upsert_node(node)
            count += 1
        return count

    def upsert_edge(self, edge: Edge) -> Edge:
        edge = enforce_edge_rules(edge)
        edge = apply_edge_policy(edge)
        self._validate_edge_endpoints(edge)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO edges (
                  id, source, relation, target, layer, confidence, semantic_strength,
                  traversable, reasoning_allowed, source_rule, created_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  relation=excluded.relation,
                  layer=excluded.layer,
                  confidence=excluded.confidence,
                  semantic_strength=excluded.semantic_strength,
                  traversable=excluded.traversable,
                  reasoning_allowed=excluded.reasoning_allowed,
                  source_rule=excluded.source_rule,
                  metadata_json=excluded.metadata_json
                """,
                (
                    edge.id,
                    edge.source,
                    edge.relation,
                    edge.target,
                    edge.layer,
                    edge.confidence,
                    edge.semantic_strength,
                    1 if edge.traversable else 0,
                    1 if edge.reasoning_allowed else 0,
                    edge.source_rule,
                    edge.created_at,
                    _json_dumps(edge.metadata),
                ),
            )
        return edge

    def _validate_edge_endpoints(self, edge: Edge) -> None:
        if edge.relation not in {"SUPPORTED_BY", "CONTRADICTED_BY", "EVIDENCE_FOR"}:
            return
        source = self.get_node(edge.source)
        target = self.get_node(edge.target)
        for role, node in {"source": source, "target": target}.items():
            if node is not None and node.type in NON_EVIDENCE_TYPES:
                raise ValueError(f"{node.type} cannot serve as Evidence in {edge.relation} edge {role}")

    def upsert_chunk(self, chunk: Chunk) -> Chunk:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO chunks (id, doc_id, text, section, page, token_count, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  doc_id=excluded.doc_id,
                  text=excluded.text,
                  section=excluded.section,
                  page=excluded.page,
                  token_count=excluded.token_count,
                  metadata_json=excluded.metadata_json
                """,
                (
                    chunk.id,
                    chunk.doc_id,
                    chunk.text,
                    chunk.section,
                    chunk.page,
                    chunk.token_count,
                    _json_dumps(chunk.metadata),
                ),
            )
            conn.execute("DELETE FROM chunks_fts WHERE id = ?", (chunk.id,))
            conn.execute(
                "INSERT INTO chunks_fts(id, text, section) VALUES (?, ?, ?)",
                (chunk.id, chunk.text, chunk.section or ""),
            )
        return chunk

    def get_node(self, node_id: str) -> Node | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        return self._row_to_node(row) if row else None

    def get_edge(self, edge_id: str) -> Edge | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM edges WHERE id = ?", (edge_id,)).fetchone()
        return self._row_to_edge(row) if row else None

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
        return self._row_to_chunk(row) if row else None

    def iter_nodes(self, include_inactive: bool = False) -> list[Node]:
        sql = "SELECT * FROM nodes"
        params: tuple[Any, ...] = ()
        if not include_inactive:
            sql += " WHERE status = ?"
            params = ("active",)
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_node(row) for row in rows]

    def iter_edges(self) -> list[Edge]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM edges").fetchall()
        return [self._row_to_edge(row) for row in rows]

    def iter_chunks(self) -> list[Chunk]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM chunks").fetchall()
        return [self._row_to_chunk(row) for row in rows]

    def search_nodes(self, query: str, limit: int = 8, project: str | None = None) -> list[dict[str, Any]]:
        fts = _fts_query(query)
        params: list[Any] = [fts]
        sql = """
            SELECT nodes.*, bm25(nodes_fts) AS score
            FROM nodes_fts
            JOIN nodes ON nodes.id = nodes_fts.id
            WHERE nodes_fts MATCH ? AND nodes.status = 'active'
        """
        if project:
            sql += " AND (nodes.project = ? OR nodes.project IS NULL)"
            params.append(project)
        sql += " ORDER BY score LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            try:
                rows = conn.execute(sql, params).fetchall()
            except sqlite3.OperationalError:
                return []
        return [{"node": self._row_to_node(row), "score": row["score"]} for row in rows]

    def search_chunks(self, query: str, limit: int = 8, project: str | None = None) -> list[dict[str, Any]]:
        fts = _fts_query(query)
        params: list[Any] = [fts]
        sql = """
            SELECT chunks.*, bm25(chunks_fts) AS score
            FROM chunks_fts
            JOIN chunks ON chunks.id = chunks_fts.id
        """
        if project:
            sql += " JOIN nodes ON nodes.id = chunks.id"
        sql += " WHERE chunks_fts MATCH ?"
        if project:
            sql += " AND nodes.status = 'active' AND (nodes.project = ? OR nodes.project IS NULL)"
            params.append(project)
        sql += " ORDER BY score LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            try:
                rows = conn.execute(sql, params).fetchall()
            except sqlite3.OperationalError:
                return []
        return [{"chunk": self._row_to_chunk(row), "score": row["score"]} for row in rows]

    def get_incident_edges(self, node_id: str, traversable_only: bool = True) -> list[Edge]:
        sql = "SELECT * FROM edges WHERE (source = ? OR target = ?)"
        params: list[Any] = [node_id, node_id]
        if traversable_only:
            sql += " AND traversable = 1"
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_edge(row) for row in rows]

    def forget_node(self, node_id: str) -> bool:
        timestamp = utc_now()
        with self.connect() as conn:
            result = conn.execute(
                "UPDATE nodes SET status = 'forgotten', updated_at = ? WHERE id = ?",
                (timestamp, node_id),
            )
            conn.execute("DELETE FROM nodes_fts WHERE id = ?", (node_id,))
        return result.rowcount > 0

    def _row_to_node(self, row: sqlite3.Row) -> Node:
        return Node(
            id=row["id"],
            type=row["type"],
            layer=row["layer"],
            scope=row["scope"] or "global",
            project=row["project"],
            source_system=row["source_system"] or "unknown",
            title=row["title"],
            content=row["content"],
            importance=row["importance"],
            confidence=row["confidence"],
            extraction_confidence=row["extraction_confidence"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=_json_loads(row["metadata_json"]),
        )

    def _row_to_edge(self, row: sqlite3.Row) -> Edge:
        return Edge(
            id=row["id"],
            source=row["source"],
            relation=row["relation"],
            target=row["target"],
            layer=row["layer"],
            confidence=row["confidence"],
            semantic_strength=row["semantic_strength"],
            traversable=bool(row["traversable"]),
            reasoning_allowed=bool(row["reasoning_allowed"]),
            source_rule=row["source_rule"],
            created_at=row["created_at"],
            metadata=_json_loads(row["metadata_json"]),
        )

    def _row_to_chunk(self, row: sqlite3.Row) -> Chunk:
        return Chunk(
            id=row["id"],
            doc_id=row["doc_id"],
            text=row["text"],
            section=row["section"],
            page=row["page"],
            token_count=row["token_count"],
            metadata=_json_loads(row["metadata_json"]),
        )
