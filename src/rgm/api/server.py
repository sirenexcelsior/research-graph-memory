from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from rgm.memory.forget import forget
from rgm.memory.promote import promote
from rgm.memory.recall import recall
from rgm.memory.remember import remember
from rgm.retrieval.fts_search import fts_search
from rgm.storage.sqlite_store import SQLiteStore


class RememberPayload(BaseModel):
    content: str
    type: str = "SessionNote"
    layer: str | None = None
    scope: str = "global"
    project: str | None = None
    title: str | None = None
    importance: float = 0.5
    confidence: float = 1.0


class RecallPayload(BaseModel):
    query: str
    intent: str | None = None
    project: str | None = None
    debug: bool = False
    limit: int = 8


class PromotePayload(BaseModel):
    node_id: str
    to: str


class ForgetPayload(BaseModel):
    node_id: str


def create_app(store: SQLiteStore | None = None) -> FastAPI:
    db = store or SQLiteStore()
    db.init_db()
    app = FastAPI(title="Research Graph Memory", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "service": "research-graph-memory", "version": "0.1.0"}

    @app.post("/memory/remember")
    def api_remember(payload: RememberPayload) -> dict[str, Any]:
        try:
            node = remember(
                payload.content,
                node_type=payload.type,
                layer=payload.layer,
                scope=payload.scope,
                project=payload.project,
                title=payload.title,
                importance=payload.importance,
                confidence=payload.confidence,
                store=db,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"node": node.model_dump(mode="json")}

    @app.post("/memory/recall")
    def api_recall(payload: RecallPayload) -> dict[str, Any]:
        context = recall(
            payload.query,
            intent=payload.intent,
            project=payload.project,
            debug=payload.debug,
            limit=payload.limit,
            store=db,
        )
        return context.model_dump(mode="json")

    @app.post("/memory/promote")
    def api_promote(payload: PromotePayload) -> dict[str, Any]:
        try:
            return promote(payload.node_id, payload.to, store=db)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/memory/forget")
    def api_forget(payload: ForgetPayload) -> dict[str, Any]:
        return forget(payload.node_id, store=db)

    @app.post("/search")
    def api_search(payload: RecallPayload) -> dict[str, Any]:
        result = fts_search(payload.query, db, limit=payload.limit, project=payload.project)
        return {
            "nodes": [{"node": row["node"].model_dump(mode="json"), "score": row["score"]} for row in result["nodes"]],
            "chunks": [{"chunk": row["chunk"].model_dump(mode="json"), "score": row["score"]} for row in result["chunks"]],
            "seed_ids": result["seed_ids"],
        }

    @app.post("/trace")
    def api_trace(payload: RecallPayload) -> dict[str, Any]:
        context = recall(payload.query, intent=payload.intent or "hypothesis_trace", project=payload.project, debug=payload.debug, limit=payload.limit, store=db)
        return context.model_dump(mode="json")

    @app.post("/evidence")
    def api_evidence(payload: RecallPayload) -> dict[str, Any]:
        context = recall(payload.query, intent=payload.intent or "research_evidence", project=payload.project, debug=payload.debug, limit=payload.limit, store=db)
        return context.model_dump(mode="json")

    return app


app = create_app()

