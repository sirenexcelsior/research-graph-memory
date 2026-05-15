from __future__ import annotations


def route_intent(query: str) -> str:
    text = query.lower()
    if any(word in text for word in ["debug", "explore", "inspect graph", "neighbors"]):
        return "debug_explore"
    if any(word in text for word in ["preference", "prefer", "style", "workflow hint", "how do i like"]):
        return "preference_query"
    if any(word in text for word in ["evidence", "support", "contradict", "citation", "prove", "grounding"]):
        return "research_evidence"
    if any(word in text for word in ["hypothesis", "trace", "why", "tested by", "experiment"]):
        return "hypothesis_trace"
    if any(word in text for word in ["project state", "status", "decision", "todo", "next step", "roadmap"]):
        return "project_state"
    return "general_recall"

