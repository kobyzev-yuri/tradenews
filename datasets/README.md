# Датасет tradenews

- **`articles/`** — JSON-массивы статей (формат nyse `serialize_news_article`). На них ссылается `articles_fixture_path` из точек.
- **`tickers_game_universe.txt`** — объединение PREMARKET_STRESS + TICKERS_LONG + TICKERS_FAST из lse `config.env` (для `snapshot_live_dataset.py --tickers-file` и `build_game_dataset_from_kb_dump.sh`).
- **`points/*.jsonl`** — по одной строке JSON на **`DatasetPoint`** (см. `docs/dataset_and_metrics_plan.md`).
- **Чистый датасет под yfinance-метрики:** из KB часто попадают псевдо-тикеры `US_MACRO`, `MACRO`, `CASH`. При сборке из CSV они уже отсекаются флагом **`--exclude-tickers`** (дефолт в `scripts/lse_csv_to_dataset_points.py`). Для уже готового JSONL:  
  `PYTHONPATH=. python scripts/filter_dataset_points_jsonl.py datasets/points/lse_kb_per_row.jsonl --out datasets/points/lse_kb_per_row_equities.jsonl`  
  Для прогона оценки удобно брать **`points/lse_kb_per_row_equities.jsonl`** (без макро-строк).
- Как наращивать объём: **`docs/building_dataset.md`**, скрипт **`scripts/snapshot_live_dataset.py`** (живой снимок по тикерам + дописывание точек).

Пример точки с внешним файлом статей: `points/example_mu.jsonl` — путь `articles_fixture_path` задаётся **относительно каталога файла точек** (`datasets/points/` при дефолтном `--articles-base`), см. `../../fixtures/articles/minimal_example.json` → каноническая фикстура в `fixtures/`. Дубликат для удобства: `datasets/articles/minimal_example.json`.

Сборка оценки для двух моделей (без `--articles-base` база = `datasets/points/`):

```bash
cd tradenews
PYTHONPATH=. python scripts/build_eval_from_points.py datasets/points/example_mu.jsonl \
  --models llama3.2:3b qwen2.5:7b \
  --out runs/example_eval.jsonl
```

Сводный бенчмарк (1d/3d/5d + JSON):

```bash
PYTHONPATH=. python scripts/run_model_benchmark.py runs/example_eval.jsonl --report-json runs/benchmark.json
```
