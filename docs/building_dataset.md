# Как собрать датасет побольше

Цель — много строк **`DatasetPoint`** (JSONL) + файлы **`articles/*.json`**, затем `build_eval_from_points.py` → метрики.

---

## 1. Накопление «живыми» снимками (рекомендуется)

Каждый снимок = **момент времени `decision_ts`** + **лента на этот момент** (как видит nyse `NewsSource`).

**Ограничение:** провайдеры отдают новости относительно **сейчас**, а не «как было 1 марта». Исторический бэкап дат без архива — отдельная задача (§4).

### Один вызов на несколько тикеров

```bash
export NYSE_PROJECT_ROOT=/path/to/nyse
cd tradenews
PYTHONPATH=. python scripts/snapshot_live_dataset.py \
  --tickers MU,NBIS,QQQ,SMH \
  --articles-dir datasets/articles \
  --append-points datasets/points/live_accum.jsonl \
  --lookback-hours 48 \
  --max-per-ticker 10 \
  --event-tag regular
```

- В `datasets/articles/` появятся файлы вида `MU_20260409T143022Z.json`.
- В `datasets/points/live_accum.jsonl` **добавятся** строки с `articles_fixture_path` и `decision_ts_utc = UTC сейчас`.

Запускай **по расписанию** (cron/systemd) 1–2 раза в день или после важных сессий — за неделю получите десятки точек.

### Вручную на конкретную дату «как сейчас в ленте»

Разовая выгрузка + правка точки руками:

```bash
PYTHONPATH=. python scripts/fetch_nyse_articles_fixture.py MU \
  --out datasets/articles/MU_manual.json \
  --lookback-hours 72 --max-per-ticker 15
```

Добавьте строку в `datasets/points/my.jsonl` с нужным `decision_ts_utc` и `"articles_fixture_path": "articles/MU_manual.json"`.

---

## 2. Несколько точек из одного файла статей (только для отладки метрик)

Можно добавить в JSONL **несколько строк** с **разными** `decision_ts_utc`, но **одним и тем же** `articles_fixture_path`, чтобы быстро получить `n ≥ 3` для Spearman в **песочнице**.

Это **не** проверка предсказательной силы (новости и цены согласованы плохо), только проверка конвейера.

---

## 3. Объединение файлов точек

```bash
cat datasets/points/part_a.jsonl datasets/points/part_b.jsonl datasets/points/live_accum.jsonl \
  > datasets/points/all.jsonl
```

Удаляйте дубликаты (одинаковые ticker+decision_ts+fixture) при необходимости.

---

## 4. Длинная история и «как было в тот день»

Варианты:

- **Экспорт из PostgreSQL (lse)** — таблицы `knowledge_base` (новости) и `quotes` (дневные свечи); план выгрузки и SQL-примеры: **[`docs/EXPORT_DATASET_POSTGRES_TRADENEWS.md`](../../docs/EXPORT_DATASET_POSTGRES_TRADENEWS.md)** (от корня репозитория `lse/`). После `export_lse_gcp_kb_quotes.sh` конвертер **CSV → JSONL точек**: **`scripts/lse_csv_to_dataset_points.py`**.
- **Архив снимков** — если вы месяц гоняли `snapshot_live_dataset.py`, уже есть панель во времени.
- **Править `NewsSource` / Yahoo** под окно «до даты» — отдельная доработка nyse (если API позволяет).

---

## 5. Прогон оценки на большом файле

```bash
PYTHONPATH=. python scripts/build_eval_from_points.py datasets/points/all.jsonl \
  --articles-base datasets \
  --models llama3.2:3b qwen2.5:7b \
  --out runs/eval_all.jsonl

PYTHONPATH=. python scripts/run_compare.py runs/eval_all.jsonl
```

Проверяйте **`n_with_return`**: если мало, сдвигайте `decision_ts` в **более раннее** прошлое (см. `dataset_and_metrics_plan.md`).

---

## Кратко

| Способ | Плюс | Минус |
|--------|------|--------|
| `snapshot_live_dataset.py` по cron | Реальные ленты, растёт сам | Не «история задним числом» |
| Ручные `fetch_nyse_articles_fixture` + JSONL | Полный контроль | Долго |
| Один fixture × много дат | Быстрый тест метрик | Не научная оценка модели |
| Postgres / архив | Настоящая история | Нужна инфраструктура |
