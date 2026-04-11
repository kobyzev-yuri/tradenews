# Фиксированные наборы новостей для tradenews

Цель: **один и тот же** список статей гонять через разные предикторы (Ollama, nyse, абляции), не меняя вход.

## Уровень 1 — самый простой (рекомендуется для старта)

Файл **JSON-массив** объектов в формате, совместимом с nyse `pipeline.news_cache.serialize_news_article` (см. ниже). Кладём в `tradenews/fixtures/articles/*.json`, коммитим в git.

Плюсы: не нужен кэш, не нужна БД, воспроизводимо в CI.

Минусы: набор собирается вручную или одним запуском скрипта выгрузки (ниже).

## Уровень 2 — выгрузка из работающего nyse

Разовый запуск (нужен `NYSE_PROJECT_ROOT` и сеть):

```bash
export NYSE_PROJECT_ROOT=/path/to/nyse
PYTHONPATH=tradenews:$NYSE_PROJECT_ROOT python tradenews/scripts/fetch_nyse_articles_fixture.py MU \
  --out tradenews/fixtures/articles/mu_yahoo_48h.json --lookback-hours 48 --max-per-ticker 10
```

Скрипт вызывает тот же `NewsSource`, что бот/CLI, и сохраняет список в каноническом JSON. Этот файл и есть фикстура для отладки предикта.

### Файловый кэш nyse (`.cache/nyse`)

Кэш хранит значения по **SHA256-ключу** (`FileCache`), имена файлов нечитаемы. Для фикстур **не обязателен**: проще один раз выгрузить JSON скриптом выше. Если всё же нужен сырой бинарник из кэша — понадобится знать **точную строку ключа** (провайдер, тикер, extra), что дублирует логику источника; поэтому для «простого начала» кэш не используем.

## Уровень 3 — PostgreSQL (lse), позже

На удалённом сервере можно периодически делать `COPY`/dump таблицы новостей в JSONL и конвертировать в тот же массив статей. Имеет смысл, когда нужна длинная история и единый источник правды вне локального кэша. Формат строки оценки (`EvaluationRow`) от этого не меняется — меняется только способ заполнения `articles_snapshot`.

## Схема одной статьи (минимум полей)

| Поле | Тип | Примечание |
|------|-----|------------|
| `ticker` | string | Как в nyse, например `MU` |
| `title` | string | |
| `timestamp` | string ISO8601 | UTC |
| `summary` | string или null | |
| `link` | string или null | |
| `publisher` | string или null | |
| `provider_id` | string | `yahoo`, `marketaux`, … |
| `raw_sentiment` | number или null | |
| `cheap_sentiment` | number или null | Можно заполнить после прогона sentiment в nyse |

Полный round-trip в nyse: `deserialize_news_article` / `serialize_news_article`.

## Связь с `DatasetPoint`

В `tradenews.schemas.DatasetPoint` поле `articles_snapshot` — это как раз **список dict** в этом формате (один JSON-файл = содержимое для одной точки `(ticker, decision_ts)`).
