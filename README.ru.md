# research-graph-memory

[English](README.md) | [中文](README.zh-CN.md)

---

### Назначение проекта

`research-graph-memory` — это локальная, тестируемая система долговременной памяти для исследовательских агентов, например Hermes. Она хранит операционную память и исследовательские знания в едином графе, но разделяет смысл через `layer`, `type` и `scope`.

Это не универсальный GraphRAG. SQLite используется как долговременное хранилище, FTS5 — как базовый полнотекстовый поиск, NetworkX — как восстанавливаемый графовый кэш, JSONL — как переносимый формат экспорта и импорта.

Главный принцип:

```text
Hermes отвечает за семантическое понимание.
RGM отвечает за управление памятью.
```

### Текущий статус

Стадия: **V0.1.1 sandbox prototype**

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
- pytest: 6 passed
- graph validation: ok, 0 issues
```

### Быстрый старт

```bash
cd GraphMemory/research-graph-memory
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
rgm init
```

Импорт Holographic Memory:

```bash
rgm import-holographic examples/synthetic_holographic.json
```

Импорт Markdown базы знаний:

```bash
rgm ingest examples/synthetic_notes --project demo --extractor rule_based
```

Запрос:

```bash
rgm recall "What evidence supports keyword search?" --project demo
```

Запуск FastAPI:

```bash
rgm serve --host 127.0.0.1 --port 8000
```

### План развития

Сделано:

- V0.1: SQLite, FTS5, CLI, FastAPI, JSONL, импорт Holographic/Markdown.
- V0.1.1: extractor provider boundary, правиловое исследовательское извлечение, Hermes provider stub, тест на реальных GenMath/Hermes данных.

Далее:

- V0.2: опциональный BGE-M3 dense sidecar index и hybrid search.
- V0.2.x: метрики качества извлечения на реальных корпусах.
- V0.3: реальный цикл Hermes LLM extraction.
- V0.4: инкрементальная индексация и обнаружение изменений.
- V0.5: adapter для экспериментов/результатов и более сильный evidence tracing.

Ограничения:

- Без Neo4j.
- Без LangChain.
- Без LlamaIndex.
- Основное ядро не зависит от внешних API.
- Без сложного UI.
- BGE-M3 является опциональным усилением, а не заменой FTS5.
