# Graph Expansion Policy

## Basic Principles

Graph expansion runs during recall after FTS5 has produced seed nodes and chunks.

The V0.1.3 recall pipeline is:

```text
query
  -> intent routing
  -> FTS5 node/chunk seeds
  -> project-scoped graph expansion
  -> structured RecallContext
```

Expansion is intent-aware. It starts from active seed nodes only, follows traversable edges that are allowed for the routed intent, and emits `graph_paths` for explainability.

Reasoning evidence is stricter than traversal. Structural and weak operational edges may be used to collect nearby context, but only `reasoning_allowed=True` edges are reported in `debug_info.reasoning_edges` and treated as reasoning evidence.

Default hop limits:

| Intent | Max hops |
|---|---:|
| `general_recall` | 1 |
| `project_state` | 1 |
| `preference_query` | 1 |
| `research_evidence` | 2 |
| `hypothesis_trace` | 2 |
| `debug_explore` | 3, only when debug exploration is enabled |

## Edge Type Filtering

Reasoning-allowed strong evidence relations:

- `SUPPORTED_BY`
- `CONTRADICTED_BY`
- `TESTED_BY`
- `PRODUCES`
- `EVIDENCE_FOR`
- `MOTIVATES`
- `GENERATES`

Intent allowlists keep expansion bounded. For example, `research_evidence` may traverse structural document edges such as `HAS_CHUNK` and `PART_OF`, plus research statement edges such as `STATES`, but `MENTIONS` is excluded from research evidence expansion and is never reasoning-allowed.

Always excluded from normal reasoning:

- `MENTIONS`
- `RELATED_TO`

`RELATED_TO` is weak by default. It does not participate in normal expansion. It is reserved for explicit debug exploration or future similarity sidecar diagnostics.

## Project Scope Control

Project-scoped recall enforces project boundaries in both stages:

- FTS5 node search filters by `node.project`.
- FTS5 chunk search joins the chunk node and filters by `node.project`.
- Graph expansion rejects neighbor nodes from another project.

Global nodes with `project = NULL` may be included. Nodes from another named project are excluded by default.

Cross-project expansion is allowed only when all of the following are true:

- intent is `debug_explore`
- request debug mode is enabled
- `RGM_ENABLE_DEBUG_EXPLORE=true`

This keeps ordinary Hermes recall from leaking GenMath or other project context unless the caller explicitly asks for debug exploration.

## Output Structure

`RecallContext` is structured JSON with these buckets:

- `document_context`: `Document` and `Chunk` nodes
- `research_context`: research nodes such as `Claim`, `Hypothesis`, `Question`, `Task`
- `operational_context`: lightweight project state and decisions
- `preference_context`: `Preference`, `WorkflowHint`, and `ToolConfig`
- `session_context`: session notes
- `evidence`: `Evidence` and `Result`
- `graph_paths`: explainable paths with `nodes` and `edges`
- `debug_info`: seed IDs, counts, limits, hop settings, and reasoning edges

`graph_paths` entries use this shape:

```json
{
  "nodes": ["claim:...", "evidence:..."],
  "edges": ["edge:..."]
}
```

Evidence is aggregated from expanded active nodes whose type is `Evidence` or `Result`. `MENTIONS` paths do not qualify as evidence.
