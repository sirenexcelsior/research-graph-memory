# Research Graph Memory 测试方法论

本文档定义 RGM 的长期评测框架。目标不是证明“代码能跑”，而是验证它作为通用外部记忆系统是否可靠，并持续证明它具备普通 RAG 不具备的 Research Graph Memory 能力。

## 核心原则

每个测试案例都必须回答三件事：

- 用户问了什么：`query` 与可选 `intent`。
- 系统应该召回、更新或连接什么：`expected_positive`。
- 系统不应该召回、连接或推理什么：`expected_negative`。

因此评测关注正确节点、正确 chunk、正确边、正确证据路径，以及不相关内容是否被排除。单纯“有结果返回”不算通过。

## 两层测试

### 1. 通用外部记忆系统能力

- `ingestion correctness`：文档、chunk、metadata、原始 Holographic content 是否完整保留；重复导入是否幂等。
- `search correctness`：精确关键词、同义表达、跨语言 query、多轮上下文 query 是否能召回目标记忆。
- `update correctness`：新事实是否覆盖旧版本；冲突是否保留为 conflict；删除/归档后是否退出 active recall；`content_hash` 是否避免重复嵌入。
- `retrieval regression`：固定 query 集合的 Recall@K、MRR、Forbidden Leakage Rate 不应随代码更新退化。
- `API/CLI contract`：CLI 和 FastAPI 返回结构稳定，`RecallContext` 可被 Hermes/OpenClaw 消费。

### 2. RGM 独有能力

- `graph-aware recall`：召回 Concept / Claim / Evidence / Decision / Hypothesis / Task 等结构化节点，而不是只返回相似 chunk。
- `edge governance`：`MENTIONS` 不能作为推理证据；`RELATED_TO` 默认不是强证据；只有 `SUPPORTED_BY`、`CONTRADICTED_BY`、`TESTED_BY`、`PRODUCES`、`EVIDENCE_FOR` 等强边进入 reasoning path。
- `research memory semantics`：能区分 Claim、Hypothesis、Evidence、Decision、Question、Experiment、Result，并能追踪研究状态。
- `hybrid retrieval advantage`：比较 `fts5`、`dense`、`hybrid`、`hybrid_graph` 四种模式。V0.1.3 的 `dense` 与 `hybrid` 是预留 sidecar 模式，当前回退到 FTS5。
- `hallucination-resistance`：语义相近但项目不同、主题不同、没有 `reasoning_allowed` 路径的内容不能进入 evidence。

## JSONL Schema

测试文件位于 `tests/eval/*.jsonl`。每行是一个 case：

```json
{
  "id": "rgm_001",
  "category": "graph_reasoning",
  "project": "demo",
  "query": "为什么 BGE-M3 应该作为 sidecar 而不是替代 FTS5？",
  "mode": "hybrid_graph",
  "intent": "project_state",
  "evaluation_target": "验证 sidecar 决策被召回，且不把弱边当成研究证据。",
  "expected_positive": {
    "nodes": [],
    "node_expectations": [
      {"type": "ProjectDecision", "content_contains": "BGE-M3 as an optional sidecar"}
    ],
    "chunks": [],
    "chunk_expectations": [],
    "edge_types": ["AFFECTS"],
    "paths": []
  },
  "expected_negative": {
    "node_expectations": [
      {"content_contains": "tarot_analysis"},
      {"content_contains": "macbook_price"}
    ],
    "edge_types": ["MENTIONS"]
  },
  "metrics": {
    "recall_at_k": 10,
    "require_reasoning_path": false,
    "max_context_tokens": 3000
  }
}
```

`nodes` 和 `chunks` 支持精确 ID。公开样例更多使用 `node_expectations` 和 `chunk_expectations`，因为 Markdown 导入生成的稳定 ID 会包含本地路径，跨机器不适合作为 golden ID。

## 测试集组织

- `smoke_queries.jsonl`：最小冒烟集，代码更新后必须先跑。
- `regression_queries.jsonl`：核心回归集，每次提交都应跑。
- `lexical_queries.jsonl`：FTS5 精确术语、人名、公式、文件名。
- `semantic_queries.jsonl`：BGE-M3 未来负责的同义、间接表述、概念等价。
- `semantic_gap_queries.jsonl`：真正的 dense gap 集合，query 刻意避开目标关键词；V0.1.3 下 FTS5-only 预期低分，V0.2 接入 BGE-M3 后应显著提升。
- `multilingual_queries.jsonl`：中文、英文、俄文 query 指向同一记忆。
- `graph_reasoning_queries.jsonl`：Claim/Evidence/Decision/Hypothesis/Task 图语义。
- `negative_queries.jsonl`：禁止误召回、禁止跨项目泄漏、禁止弱边变强证据。
- `update_queries.jsonl`：更新、去重、冲突、归档。
- `hermes_contract_queries.jsonl`：面向 Hermes/OpenClaw 的 JSON contract。

私有生产评测素材放在 `tests/eval/private/`，该目录已被 `.gitignore` 忽略。建议从 Hermes memory facts 和 GenMath LLM-Wiki Markdown 中抽取“结构和目标”，不要提交原始生产内容。

## 指标

`rgm eval` 输出每条 query 的结果和 summary：

- `recall_at_k`：目标节点或 chunk 的命中率。
- `mrr`：第一个正确目标出现得越靠前越高。
- `evidence_hit`：是否召回 Evidence/Result。
- `reasoning_path_hit`：需要证据链时，是否存在 `reasoning_allowed=true` 的路径。
- `forbidden_leakage_rate`：负例节点、chunk、边是否进入最终上下文。
- `cross_project_leakage_rate`：是否召回了其他 project 的内容。
- `avg_context_tokens`：达到召回所需的大致上下文成本。

RGM 的 recall JSON 包含 `document_context`，用于承载 `Document` / `Chunk` 这类文档层记忆。project-scoped recall 默认不允许跨项目 chunk seed 或 graph expansion；如果测试中出现跨项目内容，应视为泄漏，除非 case 明确要求 `debug_explore`。

## 运行方式

准备公开 demo corpus：

```bash
RGM_DB_PATH=/private/tmp/rgm-eval-demo.sqlite rgm init
RGM_DB_PATH=/private/tmp/rgm-eval-demo.sqlite rgm import-holographic examples/synthetic_holographic.json
RGM_DB_PATH=/private/tmp/rgm-eval-demo.sqlite rgm ingest examples/synthetic_notes --project demo --extractor rule_based
```

运行评测：

```bash
RGM_DB_PATH=/private/tmp/rgm-eval-demo.sqlite rgm eval tests/eval/smoke_queries.jsonl --project demo --mode hybrid_graph
RGM_DB_PATH=/private/tmp/rgm-eval-demo.sqlite rgm eval tests/eval/regression_queries.jsonl --project demo --mode hybrid_graph
```

V0.1.3 的当前必过门槛是 `smoke_queries.jsonl` 和 `regression_queries.jsonl`。`semantic_queries.jsonl`、`semantic_gap_queries.jsonl` 与 `multilingual_queries.jsonl` 已经定义了 BGE-M3 sidecar 应该改善的目标，但在 dense index 真正实现前，它们更适合作为未来 A/B baseline，而不是硬性 CI gate。

运行 semantic gap baseline：

```bash
RGM_DB_PATH=/private/tmp/rgm-eval-demo.sqlite rgm eval tests/eval/semantic_gap_queries.jsonl --project demo --mode fts5
```

该集合的设计目标不是让 V0.1.3 通过，而是记录“FTS5 找不到但 dense 应该找得到”的目标。每条 case 的 `metadata.semantic_gap=true`，并包含 `fts5_expected_recall_at_k` 与 `dense_expected_recall_at_k`，用于 V0.2 做 A/B 对比。

## 从真实素材构造 Golden Queries

不要凭空写 query。先选择重要记忆节点，再反推测试。

示例：

- target：`decision:bge_m3_as_sidecar`
- 精确问法：`BGE-M3 在 RGM 中应该扮演什么角色？`
- 同义问法：`为什么 dense retrieval 不应该替代 FTS5？`
- 跨语言问法：`Why should BGE-M3 be used as a sidecar?`
- 因果/反向问法：`如果取消 FTS5，只保留 BGE-M3，会损失什么？`

每条 query 都要写出 expected positives 和 expected negatives。

## 通过标准

- smoke：所有 case 必须通过，无 forbidden leakage。
- regression：Recall@10 不低于上一版本 95%；Forbidden Leakage Rate 不高于上一版本 105%；Reasoning Path Hit Rate 不低于上一版本 95%。
- graph reasoning：至少 70% query 命中 reasoning_allowed path。
- negative：Forbidden Leakage Rate 低于 5%。
- update：幂等导入 100%；已归档内容不得进入 active recall，除非 query 显式要求历史版本。

## 当前 V0.1.3 状态

- 已实现：FTS5、graph expansion、intent edge allowlist、context budget、weak edge policy、project boundary guard、公开 JSONL eval runner。
- 预留：BGE-M3 dense sidecar、dense-only/hybrid A/B 实测、LLM strong-edge proposal review。
- 原则：弱边由规则/BGE 维护；强边由 LLM 提议；强边最终所有权属于 RGM。
