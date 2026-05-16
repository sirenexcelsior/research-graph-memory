from __future__ import annotations

from rgm.config import env_flag
from rgm.models import RecallContext
from rgm.retrieval.context_builder import build_context
from rgm.retrieval.fts_search import fts_search
from rgm.retrieval.graph_expand import graph_expand
from rgm.retrieval.intent_router import route_intent
from rgm.storage.sqlite_store import SQLiteStore


def recall(
    query: str,
    *,
    intent: str | None = None,
    project: str | None = None,
    debug: bool = False,
    limit: int = 8,
    store: SQLiteStore | None = None,
) -> RecallContext:
    db = store or SQLiteStore()
    db.init_db()
    final_intent = intent or route_intent(query)
    search_result = fts_search(query, db, limit=limit, project=project)
    cross_project_allowed = final_intent == "debug_explore" and debug and env_flag("RGM_ENABLE_DEBUG_EXPLORE")
    expansion = graph_expand(
        search_result["seed_ids"],
        db,
        intent=final_intent,
        debug=debug,
        project=project,
        cross_project_allowed=cross_project_allowed,
    )
    return build_context(query, final_intent, search_result, expansion, db)
