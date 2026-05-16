from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from rgm.adapters.holographic import import_holographic as import_holographic_file
from rgm.adapters.markdown import ingest_markdown
from rgm.config import RGMConfig
from rgm.eval.runner import run_eval_file
from rgm.graph.builder import build_and_save_graph
from rgm.graph.validation import validate_graph as validate_graph_store
from rgm.memory.forget import forget as forget_node
from rgm.memory.promote import promote as promote_node
from rgm.memory.recall import recall as recall_memory
from rgm.memory.remember import remember as remember_memory
from rgm.storage.jsonl_store import export_store, import_jsonl_bundle
from rgm.storage.sqlite_store import SQLiteStore

app = typer.Typer(help="Research Graph Memory V0.1.3")


def echo_json(payload: dict) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


@app.command("init")
def init() -> None:
    config = RGMConfig.load()
    config.ensure_dirs()
    store = SQLiteStore(config.db_path)
    store.init_db()
    echo_json({"ok": True, "db_path": str(config.db_path), "graph_path": str(config.graph_path)})


@app.command("import-holographic")
def import_holographic(path: Path) -> None:
    echo_json(import_holographic_file(path))


@app.command("ingest")
def ingest(
    path: Path,
    project: Optional[str] = typer.Option(None, "--project"),
    extractor: Optional[str] = typer.Option(None, "--extractor", help="Extraction provider: rule_based, hermes, or none."),
) -> None:
    echo_json(ingest_markdown(path, project=project, extractor_provider=extractor))


@app.command("build-graph")
def build_graph() -> None:
    echo_json(build_and_save_graph())


@app.command("validate-graph")
def validate_graph() -> None:
    result = validate_graph_store()
    echo_json(result)
    if not result["ok"]:
        raise typer.Exit(code=1)


@app.command("recall")
def recall(
    query: str,
    intent: Optional[str] = typer.Option(None, "--intent"),
    project: Optional[str] = typer.Option(None, "--project"),
    debug: bool = typer.Option(False, "--debug"),
    limit: int = typer.Option(8, "--limit"),
) -> None:
    context = recall_memory(query, intent=intent, project=project, debug=debug, limit=limit)
    echo_json(context.model_dump(mode="json"))


@app.command("eval")
def eval_queries(
    path: Path,
    project: Optional[str] = typer.Option(None, "--project"),
    mode: str = typer.Option("hybrid_graph", "--mode", help="fts5, dense, hybrid, or hybrid_graph."),
    limit: int = typer.Option(10, "--limit"),
) -> None:
    """Run golden-query memory evaluation cases from a JSONL file."""
    result = run_eval_file(path, project=project, mode=mode, limit=limit)
    echo_json(result.model_dump(mode="json"))


@app.command("remember")
def remember(
    content: str,
    memory_type: str = typer.Option("SessionNote", "--type"),
    layer: Optional[str] = typer.Option(None, "--layer"),
    scope: str = typer.Option("global", "--scope"),
    project: Optional[str] = typer.Option(None, "--project"),
    title: Optional[str] = typer.Option(None, "--title"),
) -> None:
    node = remember_memory(
        content,
        node_type=memory_type,
        layer=layer,
        scope=scope,
        project=project,
        title=title,
    )
    echo_json({"node": node.model_dump(mode="json")})


@app.command("promote")
def promote(node_id: str, to: str = typer.Option(..., "--to")) -> None:
    echo_json(promote_node(node_id, to))


@app.command("forget")
def forget(node_id: str) -> None:
    echo_json(forget_node(node_id))


@app.command("export")
def export(output_dir: Path) -> None:
    echo_json(export_store(SQLiteStore(), output_dir))


@app.command("import-jsonl")
def import_jsonl(input_dir: Path) -> None:
    store = SQLiteStore()
    store.init_db()
    echo_json(import_jsonl_bundle(store, input_dir))


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
    reload: bool = typer.Option(False, "--reload"),
) -> None:
    import uvicorn

    uvicorn.run("rgm.api.server:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
