# Дамп LSE PostgreSQL (новости + котировки)

CSV выгружаются скриптом из корня репозитория **`lse/`**:

```bash
# Из корня репозитория lse/. SSH alias gcp-lse — см. lse/docs/GCP_LSE_SSH.md
export SSH_TARGET=gcp-lse    # дефолт в скрипте; можно не задавать
export DAYS=90               # окно по ts / date
./scripts/export_lse_gcp_kb_quotes.sh
```

Файлы появятся здесь с меткой времени в имени. В **`knowledge_base`** колонка **`embedding`** не выгружается (pgvector, тяжёлая).

Рядом создаётся **`quotes_last${DAYS}d_*.csv`** — дневные котировки из таблицы **`quotes`** (то же окно дат, что и у KB).

## Датасет под метрики: game universe (FAST + LONG + premarket)

Список тикеров из `config.env` (**PREMARKET_STRESS_TICKERS**, **TICKERS_LONG**, **TICKERS_FAST**) сведён в **`../tickers_game_universe.txt`** (без дубликатов).

После успешного `export_lse_gcp_kb_quotes.sh`, из **`tradenews/`**:

```bash
./scripts/build_game_dataset_from_kb_dump.sh
# опционально: KB_CSV=.../knowledge_base_last90d_XXX.csv DATASET_MODE=daily MAX_POINTS=5000
```

Получите **`datasets/points/lse_kb_game_daily_*.jsonl`** с встроенным `articles_snapshot` → дальше `build_eval_from_points.py` (forward returns пока через yfinance).

## Конвертер CSV → JSONL (`DatasetPoint`)

Из каталога **`tradenews/`**:

```bash
# Быстрый тест: по одной точке на новость
PYTHONPATH=. python scripts/lse_csv_to_dataset_points.py \
  --kb datasets/lse_gcp_dump/knowledge_base_last90d_20260409_192327Z.csv \
  --out datasets/points/lse_kb_per_row.jsonl \
  --mode per_row \
  --max-points 400
# По умолчанию строки с US_MACRO, MACRO, CASH отфильтровываются (--exclude-tickers).

# Все новости тикера за день UTC в одном snapshot
PYTHONPATH=. python scripts/lse_csv_to_dataset_points.py \
  --kb datasets/lse_gcp_dump/knowledge_base_last90d_20260409_192327Z.csv \
  --out datasets/points/lse_kb_daily.jsonl \
  --mode daily \
  --tickers MU,QQQ,SMH
```

Статьи в `articles_snapshot` совместимы с nyse `serialize_news_article` (`provider_id=lse_kb`, заголовок = первая строка `content`).

Дальше оценка: `build_eval_from_points.py` подхватывает встроенный `articles_snapshot` (каталог `articles/` для этих строк не нужен).

В корневом **`tradenews/.gitignore`** каталог **`datasets/lse_gcp_dump/*`** игнорируется, кроме этого **`README.md`** (CSV в git не коммитятся).
