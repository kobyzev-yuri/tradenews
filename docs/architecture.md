# tradenews — коротко

Пакет сравнивает **новостные предикторы** на одном датасете: предсказание → строка **EvaluationRow** (JSONL) → **метрики** без повторных вызовов LLM.

- **Поток:** точки `datasets/` → `build_eval_from_points` → `runs/*.jsonl` → `run_model_benchmark` → таблицы + опционально JSON-отчёт.
- **Код:** `tradenews/metrics.py`, `valuation.py`, `benchmark_report.py`, `predictors/*`.
- **Смысл метрик и осторожность с N:** [bench.md](bench.md).
- **Пример отчёта без сырых данных:** [reports/benchmark_game_2026-04-12.md](reports/benchmark_game_2026-04-12.md).

Подробный README и команды: [../README.md](../README.md).
