# research-graph-memory

**🧠 Гетерогенная многоуровневая исследовательская графовая память для долгоживущих агентов.**

[English](README.md) | [中文](README.zh-CN.md)

`research-graph-memory` — это локальная, тестируемая система долговременной памяти для исследовательских агентов, например Hermes. Она хранит операционную память и исследовательские знания в едином графе, но разделяет смысл через `layer`, `type` и `scope`.

Это не универсальный GraphRAG. SQLite используется как долговременное хранилище, FTS5 — как базовый полнотекстовый поиск, NetworkX — как восстанавливаемый графовый кэш, JSONL — как переносимый формат экспорта и импорта.

## ✨ Возможности

- 🧩 Единый гетерогенный граф для document / lightweight / research memory.
- 🔎 Локальный поиск на SQLite + FTS5.
- 📝 Импорт Holographic Memory JSON/JSONL и Markdown / LLM-Wiki.
- 🧪 Извлечение `Claim`, `Evidence`, `Question`, `Hypothesis`, `Task`.
- 🔌 CLI + FastAPI, готовность к интеграции с Hermes.
- 📦 JSONL импорт/экспорт без привязки к закрытому формату.
- 🚫 Без Neo4j, LangChain, LlamaIndex и обязательных внешних API.

## 🚦 Текущий статус

Стадия: **V0.1.2 sandbox prototype**

Готово:

- Инициализация SQLite.
- Таблицы `nodes`, `edges`, `chunks`.
- FTS5 индексы для узлов и чанков.
- Импорт Holographic Memory из JSON/JSONL.
- Импорт Markdown / LLM-Wiki.
- Построение `Document`, `Chunk`, `Concept`.
- Правиловое извлечение `Claim`, `Evidence`, `Question`, `Hypothesis`, `Task`.
- Команды `remember`, `recall`, `promote`, `forget`.
- CLI и FastAPI.
- Экспорт и импорт JSONL.
- Построение графа NetworkX.
- Проверка правил графа.
- Интерфейс extractor provider для Hermes.
- Заготовка интерфейса для BGE-M3 dense embeddings.
- Политика слабых/сильных ребер и RGM-owned edge metadata.
- Автоматическое построение lightweight weak edges для Holographic Memory.

Проверено на приватном локальном корпусе. Сам корпус не включается в публичный репозиторий.

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

Tests:
- pytest: 11 passed
- graph validation: ok, 0 issues
```

## ⚡ Быстрый старт

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

Публичный репозиторий содержит только синтетические demo-данные в `examples/`.

## 🏗 Принцип управления ребрами

```text
Слабые ребра поддерживаются детерминированными правилами или embedding-сходством.
Сильные ребра могут выводиться LLM.
Каждое принятое ребро принадлежит RGM и проходит его проверку.
```

## 🧭 Основные команды

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

Варианты extractor:

```bash
rgm ingest examples/synthetic_notes --project demo --extractor rule_based
rgm ingest examples/synthetic_notes --project demo --extractor none
rgm ingest examples/synthetic_notes --project demo --extractor hermes
```

Hermes может отдавать кандидатов узлов и ребер, но RGM все равно выполняет schema validation и edge rule enforcement.

## 🌐 FastAPI

```bash
rgm serve --host 127.0.0.1 --port 8000
```

Основные endpoints:

- `GET /health`
- `POST /memory/remember`
- `POST /memory/recall`
- `POST /memory/promote`
- `POST /memory/forget`
- `POST /search`
- `POST /trace`
- `POST /evidence`

`recall` возвращает структурированный JSON: `document_context`, `research_context`, `operational_context`, `preference_context`, `session_context`, `evidence`, `graph_paths` и `debug_info`. По умолчанию project-scoped recall ограничивает chunk FTS seeds и graph expansion текущим project; cross-project expansion оставлен для явного debug exploration.

## 🧪 Оценка качества

RGM включает переиспользуемый framework для golden-query evaluation. Методология описана в [docs/testing-methodology.zh-CN.md](docs/testing-methodology.zh-CN.md).

Каждый case задает не только ожидаемые положительные совпадения, но и то, что не должно попасть в контекст или reasoning path.

```bash
rgm eval tests/eval/smoke_queries.jsonl --project demo --mode hybrid_graph
rgm eval tests/eval/regression_queries.jsonl --project demo --mode hybrid_graph
```

Публичные eval-файлы синтетические. Приватные production cases должны храниться в `tests/eval/private/`; этот путь игнорируется git.

## 🔮 План BGE-M3

V0.1.2 содержит интерфейс, но не требует dense embeddings.

План V0.2:

```text
query
  -> FTS5 keyword seeds
  -> optional BGE-M3 dense semantic seeds
  -> score fusion
  -> layer-aware graph expansion
  -> structured context
```

BGE-M3 должен быть опциональным sidecar index, а не заменой SQLite или FTS5.

## 🗺 План развития

Сделано:

- ✅ V0.1: SQLite, FTS5, CLI, FastAPI, JSONL, импорт Holographic/Markdown.
- ✅ V0.1.1: extractor provider boundary, правиловое исследовательское извлечение, Hermes provider stub, тест на реальных GenMath/Hermes данных.
- ✅ V0.1.2: политика слабых ребер, RGM edge ownership metadata, Holographic lightweight weak edges.
- ✅ V0.1.2 eval extension: переиспользуемый JSONL eval framework для регрессии памяти и графовых возможностей.

Далее:

- 🔜 V0.2: опциональный BGE-M3 dense sidecar index и hybrid search.
- 🔜 V0.2.x: private-corpus eval baseline и метрики качества извлечения.
- 🔜 V0.3: реальный цикл Hermes LLM extraction.
- 🔜 V0.4: инкрементальная индексация и обнаружение изменений.
- 🔜 V0.5: adapter для экспериментов/результатов и более сильный evidence tracing.

## ✅ Тесты

```bash
pytest
```
