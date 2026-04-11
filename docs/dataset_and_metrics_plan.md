# План датасета, предикта и метрик (tradenews)

Документ фиксирует договорённости для сравнения **двух (и более) моделей Ollama** на одном наборе новостей и одной методике метрик.

---

## 1. Два уровня данных

### 1.1 Точка датасета — `DatasetPoint`

Одна гипотетическая сессия «решения в момент времени»:

| Поле | Обязательно | Смысл |
|------|-------------|--------|
| `ticker` | да | Тикер |
| `decision_ts_utc` | да | UTC-время решения: предикт и «прошлое» для статей не должны заглядывать после этой метки по смыслу эксперимента. Для **yfinance** выбирайте момент **достаточно в прошлом**, чтобы после него в выгрузке было ≥6 торговых закрытий (иначе `forward_log_return_*` будут `null`, в сводке `n_with_return=0`). Дневные бары US: индекс часто **naive** — в коде он локализуется в `America/New_York` и переводится в UTC. |
| `articles_snapshot` | нет* | Встроенный JSON-массив статей (формат nyse `serialize_news_article`) |
| `articles_fixture_path` | нет* | Путь к файлу с тем же массивом (удобнее для git и больших лент) |
| `tech_bias` | нет | Запас под end-to-end с техникой |
| `event_tag` | нет | Страта: `geo_hormuz`, `geo_ceasefire`, `fed`, `regular`, … |
| `notes` | нет | Комментарий для лога гипотез |

\* Нужен **ровно один** из вариантов: либо `articles_snapshot`, либо `articles_fixture_path`.

Формат хранения: **JSONL** — одна строка = один `DatasetPoint` (см. `datasets/points/`).

### 1.2 Строка оценки — `EvaluationRow`

Одна строка = **одна точка × одна модель**:

| Поле | Смысл |
|------|--------|
| `ticker`, `decision_ts_utc` | Как в точке |
| `model_id` | Например `ollama:llama3.2:3b`, `ollama:qwen2.5:7b` |
| `bias_predict` | Скаляр новостного предикта (см. §2) |
| `confidence_predict` | Агрегированная уверенность |
| `forward_log_return_1d`, `_3d`, `_5d` | Целевая переменная §3 |
| `llm_mode` | Опционально (если позже свяжете с nyse-гейтом) |
| `extra` | Сюда кладём `event_tag`, `notes` с точки и др. |

Итоговый файл для `run_compare.py` — JSONL из таких строк (на точку с **двумя** моделями будет **две** строки).

---

## 2. Предикт (`news.predict`)

1. В Ollama уходит промпт уровня L5 nyse: по каждой статье — структурированные поля (`sentiment`, `impact_strength`, `relevance`, `surprise`, `time_horizon`, `confidence`).
2. Из ответа извлекается массив **`items`**.
3. **bias_predict** — взвешенное среднее сентимента (как `AggregatedNewsSignal.bias`):

Для статьи \(i\):

\[
w_i = w^{\mathrm{rel}}_i \cdot w^{\mathrm{imp}}_i \cdot w^{\mathrm{hor}}_i \cdot \max(c_i,\,0.05)
\]

\[
\text{bias\_predict} = \frac{\sum_i s_i w_i}{\sum_i w_i}, \qquad
\text{confidence\_predict} = \frac{\sum_i c_i w_i}{\sum_i w_i}
\]

Веса: relevance `mention|related|primary` → 0.4 / 0.7 / 1.0; impact `low|moderate|high` → 0.4 / 0.7 / 1.0; horizon `intraday|1-3d|3-7d|long` → 0.8 / 1.0 / 0.6 / 0.3.

Реализация: `tradenews/signal_aggregate.py`, вызов модели: `OllamaNewsPredictor`.

---

## 3. Цель (`news.val`) — forward log-returns

Для горизонта \(h\) шагов по **adj close** после `decision_ts_utc`:

\[
\text{forward\_log\_return\_}h\text{d} = \ln\frac{P_{t+h}}{P_t}
\]

\(P_t\) — первое закрытие строго после момента решения, далее по ряду yfinance. Реализация: `tradenews/valuation.py`.

---

## 4. Метрики

На таблице строк (после сборки JSONL):

- **Spearman IC** между `bias_predict` и `forward_log_return_1d` (и при необходимости другим горизонтом); пары с NaN отбрасываются.
- **Hit rate (знак)**:
  \[
  \frac{1}{N}\sum_j \mathbf{1}[\mathrm{sign}(\texttt{bias\_predict}_j) = \mathrm{sign}(r_j)]
  \]
  опционально только при \(|\texttt{bias\_predict}_j| \ge \varepsilon\).
- **По `model_id`:** сводка отдельно для каждой модели (`summarize_by_model`).
- **Страты:** те же метрики внутри подвыборки `event_tag == …`.

CLI: `python scripts/run_compare.py <eval.jsonl>`.

---

## 5. Старт: две локальные модели Ollama

У вас уже подняты модели (например **`llama3.2:3b`** и **`qwen2.5:7b`**). Нужен процесс **`ollama serve`** (отдельно от интерактивного `ollama run`).

Сборка строк оценки из точек датасета:

```bash
cd tradenews
# articles-base — каталог, относительно которого резолвятся articles_fixture_path
PYTHONPATH=. python scripts/build_eval_from_points.py \
  datasets/points/example_mu.jsonl \
  --articles-base datasets \
  --models llama3.2:3b qwen2.5:7b \
  --out runs/example_eval.jsonl
```

Сравнение:

```bash
PYTHONPATH=. python scripts/run_compare.py runs/example_eval.jsonl
```

Дальше: добавляйте строки в `datasets/points/*.jsonl` и файлы статей под `datasets/articles/` (или ссылки на `fixtures/articles/`).

---

## 6. Связанные файлы

| Файл | Роль |
|------|------|
| `tradenews/schemas.py` | `DatasetPoint`, `EvaluationRow` |
| `tradenews/valuation.py` | forward log-returns |
| `tradenews/metrics.py`, `compare.py` | IC, hit rate, сводка |
| `tradenews/predictors/ollama.py` | две модели = два вызова с одним `articles_snapshot` |
| `docs/fixtures.md` | формат JSON статей |
| `docs/hypothesis_log.md` | учёт гипотез |
| `docs/evaluation_workflow.md` | порядок работ |
