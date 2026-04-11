# Рабочий порядок: датасет → две модели Ollama → метрики

Согласовано с планом: сначала **данные**, затем **две локальные модели** (`llama3.2:3b`, `qwen2.5:7b`), затем **сравнение по метрикам** на одном и том же наборе.

Полная спецификация (структура, предикт, формулы): **`dataset_and_metrics_plan.md`**.

## Шаг 1 — Датасет новостей

- Зафиксировать **список точек** `(ticker, decision_ts_utc)` — момент «решения», до которого допустимы статьи и цены для предикта.
- Для каждой точки — **один JSON-массив статей** (см. `fixtures.md`): выгрузка `scripts/fetch_nyse_articles_fixture.py` или сохранённый снимок.
- При необходимости ручные метки **`event_tag`** (гео, ФРС, обычный день) — в `EvaluationRow.extra` или отдельной таблице.

## Шаг 2 — Свечи и цель `news.val`

- Для каждой точки посчитать **forward log-returns** (`tradenews.valuation.forward_log_returns_from_close`) на горизонтах 1d / 3d / 5d — это основной **`news.val`** для IC и hit rate.
- **Торговый уровень (опционально):** если нужно смотреть не только новости, а **вход/сделку**, добавьте к строке сохранённые из nyse **`tech.bias`**, **`final_bias`**, факт позиции — тогда метрики можно строить end-to-end отдельно; базовая схема tradenews начинается с **пары `bias_predict` ↔ forward return**.

## Шаг 3 — Несколько моделей на одном датасете

- Одинаковый вход (те же фикстуры статей и те же `decision_ts`).
- Разные **`model_id`**: например `ollama:llama3.2:3b`, `ollama:qwen2.5:7b`, `openai:gpt-4o-mini` или `openai:gpt-5.4-mini` (если доступно у провайдера) — связь с `hypothesis_log.md`.
- **Ollama:** `OllamaNewsPredictor("llama3.2:3b")` — нужен **`ollama serve`**, URL **`OLLAMA_HOST`** (по умолчанию `http://127.0.0.1:11434`).
- **OpenAI-совместимый API:** `OpenAINewsPredictor` — **`OPENAI_API_KEY`**, опционально **`OPENAI_BASE_URL`**, имя модели в конструкторе или **`TRADENEWS_OPENAI_MODEL`**. Сборка eval: `scripts/build_eval_from_points.py --models ... openai:<model_id> ...`

## Шаг 4 — Метрики

- Свести строки в один JSONL с колонками `model_id`, `bias_predict`, `forward_log_return_1d` (и др.).
- `PYTHONPATH=. python scripts/run_compare.py <файл>.jsonl`
- Дополнительно: страты по `event_tag`, бакеты `confidence_predict` — см. `metrics.py` и `hypothesis_log.md`.

## Шаг 5 — Вывод

- Зафиксировать результат в логе гипотез: какая модель лучше по согласованным метрикам, что менять в промпте/агрегаторе на следующей итерации.
