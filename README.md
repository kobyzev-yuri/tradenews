# tradenews

Офлайн-сравнение **моделей новостного сигнала** (`news.predict`) с **рыночным исходом** (`news.val` — обычно forward log-returns) на фиксированном наборе точек `(ticker, decision_time)`.

Проект задуман как **надстройка над [nyse](../nyse)** (тот же смысл L5 `AggregatedNewsSignal.bias`, лог-доходности, издержек), но **не требует** импорта nyse для расчёта метрик по уже сохранённым прогонам.

## Быстрый старт

```bash
cd tradenews
pip install -e .
pytest tests/
```

Сравнение моделей по JSONL с колонками `model_id`, `bias_predict`, `forward_log_return_1d` и т.д. — см. `docs/architecture.md`.

Пример сводки по файлу с двумя моделями на одной дате/тикере:

```bash
PYTHONPATH=. python scripts/run_compare.py examples/sample_evaluation.jsonl
```

Фиксированные наборы статей для сравнения моделей на одном входе: см. **`docs/fixtures.md`** и каталог **`fixtures/articles/`**.  
Учёт гипотез (архитектура, модели, критерии приёмки): **`docs/hypothesis_log.md`**.  
Порядок работ: датасет → Ollama → метрики — **`docs/evaluation_workflow.md`**.  
**Спецификация датасета, предикта и формул метрик:** **`docs/dataset_and_metrics_plan.md`**.  
Каталог точек и статей: **`datasets/`** (см. `datasets/README.md`).  
Как **увеличить датасет** (cron, батчи, ограничения API): **`docs/building_dataset.md`**.  
**LSE CSV → JSONL точек:** `scripts/lse_csv_to_dataset_points.py` (модуль `tradenews.lse_kb_converter`).

Локальные модели: `OllamaNewsPredictor("llama3.2:3b")` / `qwen2.5:7b` (сервер `ollama serve`, опционально `OLLAMA_HOST`).  
Длинные прогоны: **`OLLAMA_KEEP_ALIVE=30m`** или **`-1`** (держать модель в VRAM между запросами; иначе `ollama ps` часто пустой между точками — это норма).

Облако (OpenAI-совместимый API): `OpenAINewsPredictor` читает **`OPENAI_API_KEY`** или **`OPENAI_GPT_KEY`**, **`OPENAI_BASE_URL`**, **`OPENAI_MODEL`**, **`OPENAI_TIMEOUT`** — как в корневом **`../config.env`** проекта lse.

Два уровня конфигурации:

| Файл | Назначение |
|------|------------|
| **`../config.env`** (корень **lse**) | Общие ключи: OpenAI, БД, … Запуск: `with_lse_config_env.sh`. |
| **`tradenews/config.env`** (локальный, **не в git**) | Переопределения только для tradenews; шаблон: **`config.env.example`**. Запуск: `with_tradenews_config_env.sh` — **локальный перекрывает lse** для одного ключа. |

```bash
cp config.env.example config.env   # один раз, подставьте значения
```

Запуск с **только lse** (как раньше):

```bash
cd tradenews
./scripts/with_lse_config_env.sh bash -c 'PYTHONUNBUFFERED=1 PYTHONPATH=. python scripts/build_eval_from_points.py \
  datasets/points/ВАШ.jsonl \
  --models llama3.2:3b qwen2.5:7b openai:${OPENAI_MODEL} \
  --out runs/eval_three.jsonl'
./scripts/with_lse_config_env.sh PYTHONPATH=. python scripts/run_compare.py runs/eval_three.jsonl
```

Запуск **lse + локальный `config.env`**:

```bash
./scripts/with_tradenews_config_env.sh bash -c 'PYTHONPATH=. python scripts/run_openai_predict_fixture.py fixtures/articles/minimal_example.json MU'
```

Пути: **`LSE_CONFIG_ENV`**, **`TRADENEWS_CONFIG_ENV`** (явный файл вместо дефолтов `../config.env` и `./config.env`).  
Если провайдер не поддерживает `response_format: json_object`, задайте **`TRADENEWS_OPENAI_JSON_OBJECT=0`**.

### Push в GitHub с `GITHUB_TOKEN`

**`GITHUB_TOKEN`** обычно лежит в **`lse/config.env`**; при необходимости продублируйте или переопределите в **`tradenews/config.env`** — push смотрит **сначала локальный tradenews**, потом lse (см. комментарии в `scripts/push_github_from_config_env.sh`). **`remote origin`** — `https://github.com/owner/repo.git`.

```bash
./scripts/push_github_from_config_env.sh
# ./scripts/push_github_from_config_env.sh main
```

Читается только ключ **`GITHUB_TOKEN`** (`scripts/read_lse_config_key.py`), без `source` всего файла.

## Связь с nyse

| tradenews | nyse |
|-----------|------|
| строка оценки `EvaluationRow` | `AggregatedNewsSignal.bias`, `confidence`, `llm_mode` |
| `forward_log_return_*` | цены через `yfinance`, те же тикеры |
| предиктор `NysePipelinePredictor` (опционально) | `run_news_signal_pipeline` + статьи из кэша/дампа |

Путь к клону nyse задаётся переменной **`NYSE_PROJECT_ROOT`** (или `PYTHONPATH`), если используете адаптер.
