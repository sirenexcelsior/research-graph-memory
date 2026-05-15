# research-graph-memory

**🧠 面向长期研究 Agent 的异构多层科研图记忆系统。**

[English](README.md) | [Русский](README.ru.md)

`research-graph-memory` 是一个面向 Hermes 等长期运行研究 Agent 的本地图记忆系统。它不是通用 GraphRAG，而是一个可独立运行、可测试、可导入导出、未来可通过 HTTP API 接入 Hermes 的长期记忆底座。

核心思想：

```text
Hermes 负责语义理解。
RGM 负责记忆治理。
```

## ✨ 特性

- 🧩 用统一异构图存储 document / lightweight / research memory。
- 🔎 使用 SQLite + FTS5 做本地关键词检索。
- 📝 支持 Holographic Memory JSON/JSONL 和 Markdown / LLM-Wiki 导入。
- 🧪 可抽取 `Claim`、`Evidence`、`Question`、`Hypothesis`、`Task`。
- 🔌 提供 CLI + FastAPI，预留 Hermes 接入边界。
- 📦 支持 JSONL 导入导出，避免数据锁死。
- 🚫 不依赖 Neo4j / LangChain / LlamaIndex / 外部 API。

## 🚦 当前进度

当前阶段：**V0.1.1 沙盒原型**

已完成：

- SQLite 初始化。
- `nodes`、`edges`、`chunks` 表。
- FTS5 节点/分块检索。
- Holographic Memory JSON/JSONL 导入。
- Markdown / LLM-Wiki 导入。
- `Document`、`Chunk`、`Concept` 建图。
- 规则抽取 `Claim`、`Evidence`、`Question`、`Hypothesis`、`Task`。
- `remember`、`recall`、`promote`、`forget`。
- CLI 与 FastAPI。
- JSONL 导入导出。
- NetworkX 图缓存构建。
- 图验证规则。
- Hermes extractor provider 边界。
- BGE-M3 dense embedding 接口占位。

已在本地私有真实语料上验证。真实语料不会包含在公开仓库中。

```text
Hermes facts:
- records: 15

GenMath Markdown:
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

测试:
- pytest: 6 passed
- graph validation: ok, 0 issues
```

## ⚡ 快速开始

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

公开仓库只包含 `examples/` 下的 synthetic demo 数据。

## 🧭 常用命令

```bash
rgm remember "Use SQLite FTS5 as the baseline search layer." \
  --type ProjectDecision \
  --layer lightweight \
  --scope project \
  --project research-graph-memory

rgm promote <node_id> --to Hypothesis
rgm forget <node_id>
rgm export data/processed
rgm import-jsonl data/processed
```

抽取器选项：

```bash
rgm ingest examples/synthetic_notes --project demo --extractor rule_based
rgm ingest examples/synthetic_notes --project demo --extractor none
rgm ingest examples/synthetic_notes --project demo --extractor hermes
```

注意：Hermes 只提供候选节点和候选边，RGM 仍会执行 schema validation 和 edge rule enforcement。

## 🌐 FastAPI

```bash
rgm serve --host 127.0.0.1 --port 8000
```

核心接口：

- `GET /health`
- `POST /memory/remember`
- `POST /memory/recall`
- `POST /memory/promote`
- `POST /memory/forget`
- `POST /search`
- `POST /trace`
- `POST /evidence`

## 🔮 BGE-M3 计划

V0.1.1 只保留接口，不强依赖 dense embedding。

V0.2 计划：

```text
query
  -> FTS5 keyword seeds
  -> optional BGE-M3 dense semantic seeds
  -> score fusion
  -> layer-aware graph expansion
  -> structured context
```

BGE-M3 是可选 sidecar index，不替代 SQLite 或 FTS5。

## 🗺 项目计划

已完成：

- ✅ V0.1：SQLite、FTS5、CLI、FastAPI、JSONL、Holographic/Markdown 导入。
- ✅ V0.1.1：抽取器边界、规则研究语义抽取、Hermes provider stub、真实 GenMath/Hermes 测试。

下一步：

- 🔜 V0.2：加入可选 BGE-M3 dense sidecar index，实现 hybrid search。
- 🔜 V0.2.x：加入真实语料上的抽取质量评估。
- 🔜 V0.3：接入真实 Hermes LLM extraction loop。
- 🔜 V0.4：增量索引和变更检测。
- 🔜 V0.5：实验/结果 adapter 与更强 evidence tracing。

## ✅ 测试

```bash
pytest
```

