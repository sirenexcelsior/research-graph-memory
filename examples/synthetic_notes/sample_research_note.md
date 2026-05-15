---
title: Synthetic Research Memory Demo
book_ref:
  - kb:synthetic-handbook
---

# Synthetic Research Memory Demo

## Theorem: Toy Retrieval Claim

> Synthetic source: Example Handbook, Section 1.

Claim: Keyword search is useful for exact-match recall in a local memory system.

Evidence: SQLite FTS5 supports local full-text search without requiring an external service.

Question: When should dense retrieval be added?

TODO: Compare FTS5-only recall with hybrid dense recall.

## Hypothesis: Hybrid Recall

Hypothesis: Adding optional dense retrieval improves recall when the query uses different wording than the stored note.

Evidence: Dense embeddings can retrieve semantically related text even when exact keywords differ.

