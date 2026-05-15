# research-graph-memory

**Heterogeneous Multi-Layer Research Graph Memory for long-lived research agents.**

`research-graph-memory` is a local, testable memory substrate for agents such as Hermes. It stores lightweight operational memory and research-grade knowledge in one graph, while keeping semantics separated by `layer`, `type`, and `scope`.

It is intentionally **not** a generic GraphRAG framework. SQLite is the durable store, SQLite FTS5 handles keyword retrieval, NetworkX provides a rebuildable graph cache, JSONL keeps the system portable, and optional dense retrieval is planned as a sidecar layer.

Translations: [中文](README.zh-CN.md) | [Русский](README.ru.md)

---

### Status

Current stage: **V0.1.1 sandbox prototype**

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

### Architecture

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

Layers:

- `document`: `Document`, `Chunk`
- `lightweight`: `Preference`, `WorkflowHint`, `ToolConfig`, `ProjectState`, `ProjectDecision`, `Todo`, `SessionNote`
- `research`: `Concept`, `Claim`, `Hypothesis`, `Evidence`, `Experiment`, `Result`, `Question`, `Task`

Important edge rules:

- `MENTIONS` is never reasoning-allowed.
- `RELATED_TO` is not reasoning-allowed by default.
- `SUPPORTED_BY`, `CONTRADICTED_BY`, `TESTED_BY`, `PRODUCES`, and `EVIDENCE_FOR` are reasoning-allowed.
- `Preference`, `ToolConfig`, and `WorkflowHint` cannot be used as `Evidence`.

### Install

```bash
cd GraphMemory/research-graph-memory
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Initialize

```bash
rgm init
```

This creates the SQLite database, FTS5 indexes, and project data directories.

### Import Holographic Memory

```bash
rgm import-holographic examples/synthetic_holographic.json
```

Holographic import preserves original content and stores the raw record in `metadata.raw_record`.

Mapping:

- `general` -> `ProjectState`
- `user_pref` -> `Preference` or `WorkflowHint`
- `project` -> `ProjectState` or `ProjectDecision`
- `tool` -> `ToolConfig` or `WorkflowHint`

### Import Markdown / LLM-Wiki Notes

```bash
rgm ingest examples/synthetic_notes --project demo --extractor rule_based
```

Extractor options:

```bash
rgm ingest examples/synthetic_notes --project demo --extractor rule_based
rgm ingest examples/synthetic_notes --project demo --extractor none
rgm ingest examples/synthetic_notes --project demo --extractor hermes
```

The default `rule_based` extractor is conservative. It detects explicit structure such as theorem/definition headings, blockquotes, `Claim:`, `Evidence:`, `Question:`, and `TODO`.

Hermes can later provide LLM-generated extraction candidates through the `hermes` provider. RGM still validates and enforces graph rules before writing.

### Remember, Recall, Promote, Forget

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

Recall returns structured JSON:

- `research_context`
- `operational_context`
- `preference_context`
- `session_context`
- `evidence`
- `graph_paths`
- `debug_info`

Intent hop limits:

- `general_recall`: 1-hop
- `project_state`: 1-hop
- `preference_query`: 1-hop
- `research_evidence`: 2-hop
- `hypothesis_trace`: 2-hop
- `debug_explore`: 3-hop only with explicit debug mode

### FastAPI

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

### JSONL Portability

```bash
rgm export data/processed
rgm import-jsonl data/processed
```

Exported files:

- `nodes.jsonl`
- `edges.jsonl`
- `chunks.jsonl`

### BGE-M3 Plan

V0.1.1 includes the interface but does not require dense embeddings.

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

### Hermes Integration Plan

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

### Roadmap

Done:

- V0.1: SQLite + FTS5 + CLI + FastAPI + JSONL + Holographic/Markdown import.
- V0.1.1: extraction provider boundary, rule-based research extraction, Hermes provider stub, real GenMath/Hermes smoke test.

Next:

- V0.2: optional BGE-M3 dense sidecar index and hybrid search.
- V0.2.x: better extraction evaluation metrics on real corpora.
- V0.3: real Hermes LLM extraction loop.
- V0.4: incremental indexing and update detection.
- V0.5: experiment/result adapter and stronger evidence tracing.

Boundaries:

- No Neo4j.
- No LangChain.
- No LlamaIndex.
- No external API dependency for core operation.
- No complex UI.
- Dense retrieval remains optional.

### Test

```bash
pytest
```
