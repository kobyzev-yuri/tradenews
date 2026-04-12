# tradenews

**Зачем:** сравнить несколько LLM (Ollama + облако через OpenAI-совместимый API) на **одних и тех же** новостях и времени решения, и посмотреть, совпадает ли **ранг** их сигнала с **рангом** реальной **лог-доходности** вперёд (1d / 3d / 5d). Это офлайн-бенч, не торговый совет.

**Важно про выборку:** метрики считаются по **тому числу точек**, что в вашем JSONL. Мало точек (десятки) — легко получить «красивый» случайный результат; смотрите доверительные интервалы и p-value в отчёте, повторяйте на другом периоде.

## Быстрый старт

```bash
cd tradenews
cp config.env.example config.env   # ключи PROXYAPI / Ollama — см. пример
# Сборка eval + отчёт (модели из TRADENEWS_EVAL_MODEL_SPECS или --models):
PYTHONPATH=. python scripts/run_model_benchmark.py \
  --build datasets/points/example_mu.jsonl \
  --out-jsonl runs/eval.jsonl \
  --report-json runs/benchmark.json
```

Только отчёт по уже собранному JSONL:

```bash
PYTHONPATH=. python scripts/run_model_benchmark.py runs/eval.jsonl --report-json runs/benchmark.json
```

Подробнее по смыслу метрик и ограничениям: **[docs/bench.md](docs/bench.md)**.  
Пример зафиксированного прогона (таблицы без сырых данных): **[docs/reports/benchmark_game_2026-04-12.md](docs/reports/benchmark_game_2026-04-12.md)**.

## Тесты (без сети)

```bash
pytest tests/ -q
```

## Структура

- `tradenews/` — пакет: метрики, valuation, предикторы, `benchmark_report`.
- `scripts/run_model_benchmark.py`, `scripts/build_eval_from_points.py` — CLI бенча и сборки eval.
- `runs/` — локальные артефакты (в `.gitignore`).
