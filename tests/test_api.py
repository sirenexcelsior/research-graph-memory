from fastapi.testclient import TestClient

from rgm.api.server import create_app
from rgm.storage.sqlite_store import SQLiteStore


def test_api_memory_round_trip(tmp_path):
    db = SQLiteStore(tmp_path / "rgm.sqlite")
    client = TestClient(create_app(db))

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True

    remembered = client.post(
        "/memory/remember",
        json={
            "content": "Prefer deterministic JSON responses.",
            "type": "Preference",
            "layer": "lightweight",
            "scope": "global",
        },
    )
    assert remembered.status_code == 200
    node_id = remembered.json()["node"]["id"]

    recalled = client.post("/memory/recall", json={"query": "deterministic JSON preference"})
    assert recalled.status_code == 200
    assert recalled.json()["preference_context"]

    promoted = client.post("/memory/promote", json={"node_id": node_id, "to": "Claim"})
    assert promoted.status_code == 200
    assert promoted.json()["promoted"]["type"] == "Claim"

