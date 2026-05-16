# Promote 操作语义

`promote` 用于把已有轻量记忆提升为研究层节点，并保留原始内容与来源。它不是普通编辑，也不是降级操作。

## 状态转换规则

V0.1.3 允许 promote 到 research layer 类型：

- `Concept`
- `Claim`
- `Hypothesis`
- `Evidence`
- `Experiment`
- `Result`
- `Question`
- `Task`

典型路径：

- `SessionNote -> Claim`
- `SessionNote -> Hypothesis`
- `ProjectDecision -> Claim`
- `ProjectDecision -> Hypothesis`
- `ProjectState -> Question`
- `Todo -> Task`
- `Preference -> Question`，用于提出待验证研究问题，而不是把偏好当证据

禁止路径：

- 不能 promote 到 lightweight 类型
- 不能从 research 层降级到 lightweight 层
- 不能把 `Preference`、`ToolConfig`、`WorkflowHint` 静默写成 `Evidence`

当前实现只允许 `--to` 参数属于 research type；其他类型会抛出 `ValueError`。

## 字段变化规则

执行：

```bash
rgm promote <node_id> --to Hypothesis
```

会创建一个新的 research node，而不是覆盖原节点。

字段规则：

- `type`：写为目标类型，例如 `Hypothesis`
- `layer`：自动写为 `research`
- `scope`：继承源节点
- `project`：继承源节点
- `title`：继承源节点
- `content`：完整保留
- `importance`：继承源节点
- `confidence`：以源节点 confidence 为基础略微折扣
- `metadata`：保留源 metadata，并记录 promote 历史

原有 edges 不会被复制到新节点。RGM 会创建一条新的 cross-layer edge：

```text
source --PROMOTED_TO--> promoted
```

`PROMOTED_TO` 不是 reasoning evidence。未来如果需要把 promote 后的新研究节点接入强证据链，必须显式建立 `SUPPORTED_BY`、`CONTRADICTED_BY`、`TESTED_BY`、`PRODUCES` 或 `EVIDENCE_FOR` 等强边，并重新经过 edge governance。

## 历史追踪

Promoted node 的 metadata 包含：

- `promoted_from`：源节点 ID
- `source_type`：源节点 type
- `source_layer`：源节点 layer
- `source_metadata`：源节点 metadata 快照

Promote 时间由 promoted node 的 `created_at` 字段记录。

## 示例

假设存在轻量记忆：

```text
ProjectDecision: keep BGE-M3 as an optional sidecar index.
```

执行：

```bash
rgm promote <node_id> --to Hypothesis
```

结果：

1. 创建新的 `Hypothesis` 节点。
2. 新节点 `layer = research`。
3. 新节点保留原始 content。
4. 新节点 metadata 记录来源。
5. 创建 `PROMOTED_TO` 边。
6. 该边由 RGM 拥有和验证，但不作为 evidence reasoning path。
