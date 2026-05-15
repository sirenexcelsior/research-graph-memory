# research-graph-memory

**🧠 Heterogeneous Multi-Layer Research Graph Memory for long-lived research agents.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](#-install)
[![Storage](https://img.shields.io/badge/Storage-SQLite%20%2B%20FTS5-lightgrey)](#-architecture)
[![API](https://img.shields.io/badge/API-FastAPI-green)](#-fastapi)
[![Status](https://img.shields.io/badge/Status-V0.1.2%20sandbox-orange)](#-status)

Translations: [中文](README.zh-CN.md) | [Русский](README.ru.md)

`research-graph-memory` is a local, testable memory substrate for agents such as Hermes. It stores lightweight operational memory and research-grade knowledge in one graph, while keeping semantics separated by `layer`, `type`, and `scope`.

It is intentionally **not** a generic GraphRAG framework. SQLite is the durable store, SQLite FTS5 handles keyword retrieval, NetworkX provides a rebuildable graph cache, JSONL keeps the system portable, and optional dense retrieval is planned as a sidecar layer.

## ✨ Highlights

- 🧩 Unified heterogeneous graph for document, lightweight, and research memory.
- 🔎 Local-first retrieval with SQLite FTS5 and graph expansion.
- 📝 Imports Holographic Memory JSON/JSONL and Markdown / LLM-Wiki notes.
- 🧪 Extracts research structure: `Claim`, `Evidence`, `Question`, `Hypothesis`, `Task`.
- 🔌 CLI + FastAPI, ready for Hermes integration.
- 📦 JSONL import/export to avoid data lock-in.
- 🚫 No Neo4j, LangChain, LlamaIndex, external API dependency, or heavy UI.

## 📚 Contents

- [Status](#-status)
- [Quick Demo](#-quick-demo)
- [Architecture](#-architecture)
- [Install](#-install)
- [Core Commands](#-core-commands)
- [FastAPI](#-fastapi)
- [BGE-M3 Plan](#-bge-m3-plan)
- [Hermes Integration](#-hermes-integration)
- [Roadmap](#-roadmap)

## 🚦 Status

Current stage: **V0.1.2 sandbox prototype**

Implemented:

- SQLite database initialization.
- `nodes`, `edges`, `chunks` tables.
- FTS5 indexes for nodes and chunks.
- Holographic memory JSON/JSONL import.
- Markdown / LLM-Wiki import.
- Document, Chunk, Concept graph construction.
- Rule-based research extraction for `Claim`, `Evidence`, `Question`, `Hypothesis`, and `Task`.
- `remember`, `recall`, `promote`, `forget`.
- CLI and FastAPI.
- JSONL export/import.
- NetworkX graph build.
- Graph validation rules.
- Hermes extraction provider boundary.
- BGE-M3 dense embedding interface stub.
- Weak/strong edge policy with RGM-owned edge metadata.
- Holographic Memory weak operational edge generation.

Validated on a private local corpus. The corpus itself is not included in this public repository.

```text
Hermes facts:
- records: 15

GenMath Markdown corpus:
- documents: 79
- chunks: 947
- concepts: 1168
- claims: 303
- evidence: 648
- hypotheses: 40
- questions: 103
- tasks: 21
- edges: 6271

Graph:
- nodes: 3324
- edges: 6271

Tests:
- pytest: 6 passed
- graph validation: ok, 0 issues
```

## ⚡ Quick Demo

```bash
cd GraphMemory/research-graph-memory
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

rgm init
rgm import-holographic examples/synthetic_holographic.json
rgm ingest examples/synthetic_notes --project demo --extractor rule_based
rgm recall "What evidence supports keyword search?" --project demo
```

The demo uses only synthetic data under `examples/`.

## 🏗 Architecture

```text
raw data
  -> adapters
  -> extraction providers
  -> schema validation
  -> SQLite + FTS5
  -> graph expansion
  -> structured recall context
  -> Hermes / API consumers
```

Edge governance principle:

```text
Weak edges are maintained by deterministic rules or embedding similarity.
Strong edges may be inferred by LLMs.
Every accepted edge is owned, validated, and governed by RGM.
```

Layers:

- `document`: `Document`, `Chunk`
- `lightweight`: `Preference`, `WorkflowHint`, `ToolConfig`, `ProjectState`, `ProjectDecision`, `Todo`, `SessionNote`
- `research`: `Concept`, `Claim`, `Hypothesis`, `Evidence`, `Experiment`, `Result`, `Question`, `Task`

Important edge rules:

- `MENTIONS` is never reasoning-allowed.
- `RELATED_TO` is not reasoning-allowed by default.
- `SUPPORTED_BY`, `CONTRADICTED_BY`, `TESTED_BY`, `PRODUCES`, and `EVIDENCE_FOR` are reasoning-allowed.
- `Preference`, `ToolConfig`, and `WorkflowHint` cannot be used as `Evidence`.

## 🛠 Install

```bash
cd GraphMemory/research-graph-memory
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 🧭 Core Commands

Initialize:

```bash
rgm init
```

Import synthetic Holographic Memory:

```bash
rgm import-holographic examples/synthetic_holographic.json
```

Import Markdown notes:

```bash
rgm ingest examples/synthetic_notes --project demo --extractor rule_based
```

Extractor options:

```bash
rgm ingest examples/synthetic_notes --project demo --extractor rule_based
rgm ingest examples/synthetic_notes --project demo --extractor none
rgm ingest examples/synthetic_notes --project demo --extractor hermes
```

Remember, recall, promote, forget:

```bash
rgm remember "Use SQLite FTS5 as the baseline search layer." \
  --type ProjectDecision \
  --layer lightweight \
  --scope project \
  --project research-graph-memory

rgm recall "What evidence supports keyword search?" --project demo

rgm promote <node_id> --to Hypothesis

rgm forget <node_id>
```

Export and import JSONL:

```bash
rgm export data/processed
rgm import-jsonl data/processed
```

Recall returns structured JSON:

- `research_context`
- `operational_context`
- `preference_context`
- `session_context`
- `evidence`
- `graph_paths`
- `debug_info`

## 🌐 FastAPI

```bash
rgm serve --host 127.0.0.1 --port 8000
```

Endpoints:

- `GET /health`
- `POST /memory/remember`
- `POST /memory/recall`
- `POST /memory/promote`
- `POST /memory/forget`
- `POST /search`
- `POST /trace`
- `POST /evidence`

## 🔮 BGE-M3 Plan

V0.1.2 includes the interface but does not require dense embeddings.

Planned V0.2 hybrid retrieval:

```text
query
  -> FTS5 keyword seeds
  -> optional BGE-M3 dense semantic seeds
  -> score fusion
  -> layer-aware graph expansion
  -> structured context
```

BGE-M3 should be implemented as an optional sidecar dense index, not as a replacement for SQLite or FTS5.

## 🤝 Hermes Integration

RGM is designed to integrate with Hermes over HTTP:

- Hermes writes memories with `/memory/remember`.
- Hermes asks for structured context with `/memory/recall`.
- Hermes promotes useful memories with `/memory/promote`.
- Hermes can provide LLM extraction candidates through the `hermes` extraction provider.
- RGM remains responsible for storage, validation, edge rules, and JSON portability.

Principle:

```text
Hermes does semantic understanding.
RGM does memory governance.
```

## 🗺 Roadmap

Done:

- ✅ V0.1: SQLite + FTS5 + CLI + FastAPI + JSONL + Holographic/Markdown import.
- ✅ V0.1.1: extraction provider boundary, rule-based research extraction, Hermes provider stub, real GenMath/Hermes smoke test.
- ✅ V0.1.2: weak edge policy, RGM edge ownership metadata, Holographic lightweight weak edges.

Next:

- 🔜 V0.2: optional BGE-M3 dense sidecar index and hybrid search.
- 🔜 V0.2.x: better extraction evaluation metrics on real corpora.
- 🔜 V0.3: real Hermes LLM extraction loop.
- 🔜 V0.4: incremental indexing and update detection.
- 🔜 V0.5: experiment/result adapter and stronger evidence tracing.

## ✅ Test

```bash
pytest
```
