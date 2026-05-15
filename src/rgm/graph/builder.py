from __future__ import annotations

import pickle
from pathlib import Path

import networkx as nx

from rgm.config import RGMConfig
from rgm.storage.sqlite_store import SQLiteStore


def build_networkx_graph(store: SQLiteStore | None = None) -> nx.MultiDiGraph:
    db = store or SQLiteStore()
    db.init_db()
    graph = nx.MultiDiGraph()

    for node in db.iter_nodes(include_inactive=False):
        graph.add_node(node.id, **node.model_dump(mode="json"))

    for edge in db.iter_edges():
        if edge.source in graph and edge.target in graph and edge.traversable:
            graph.add_edge(edge.source, edge.target, key=edge.id, **edge.model_dump(mode="json"))

    return graph


def build_and_save_graph(store: SQLiteStore | None = None, graph_path: str | Path | None = None) -> dict[str, int | str]:
    config = RGMConfig.load()
    output = Path(graph_path or config.graph_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    graph = build_networkx_graph(store)
    with output.open("wb") as handle:
        pickle.dump(graph, handle)
    return {"nodes": graph.number_of_nodes(), "edges": graph.number_of_edges(), "graph_path": str(output)}
