```markdown
# Реализация гибридного поиска в СУБД PostgreSQL

## 1. Назначение проекта

Система предназначена для загрузки датасета `wikifacts-window_5` (вопросы и документы), построения поисковых индексов, выполнения экспериментов по ранжированию и их сравнения с эталонными данными (qrels) по метрике macro F1.

## 2. Компоненты системы

### 2.1. Файлы конфигурации

| Файл | Назначение |
|------|------------|
| `config.py` | Подключение к БД, имена датасетов, параметры загрузки |
| `config_vector.py` | Модель эмбеддингов (`intfloat/multilingual-e5-large`), размер батча |

### 2.2. Скрипты загрузки данных

| Файл | Функция |
|------|---------|
| `load_dataset.py` | Загрузка корпуса, запросов и qrels из Hugging Face |
| `save_qrels.py` | Вставка qrels в таблицу `result` с использованием маппинга|
| `load_qrels.py` | Заполнение `dataset_id` реальными идентификаторами из датасета |

### 2.3. Вычисление эмбеддингов

| Файл | Функция |
|------|---------|
| `vector.py` | Вычисление и сохранение эмбеддингов для документов (модель E5-large) |

### 2.4. Поисковые функции (SQL)

| Файл | Метод | Описание |
|------|-------|----------|
| `fts.sql` | Полнотекстовый | `ts_rank` + GIN индекс |
| `do_vector_.sql` | Векторный | Косинусное расстояние (pgvector) |
| `rrf.sql` | Комбинированный (RRF) | Взвешенное объединение FT + векторного |

### 2.5. Оценка качества

| Файл | Функция |
|------|---------|
| `f1_macro.sql` | `compare_f1_macro()` – macro precision/recall/F1 |

## 3. Схема базы данных

```sql
-- Основные таблицы
news     (id, dataset_id, article, fts_article, embedding)
query    (id, dataset_id, query_text, embedding)
run      (id, description, created_at)
result   (query_id, news_id, run_id, rank)

-- Индексы
idx_news_fts          ON news USING GIN(fts_article)
idx_result_score_rank ON result(run_id, query_id, score DESC, rank)
```

## 4. Порядок выполнения

### Шаг 1: Создание БД
```bash
psql -d postgres -f db.sql
```

### Шаг 2: Загрузка сырых данных
```bash
python load_dataset.py
```

### Шаг 3: Нормализация идентификаторов
```bash
python insert_qrels.py
# Создаёт id_mapping.csv
```

### Шаг 4: Вычисление эмбеддингов
```bash
python vector.py
# Заполняет news.embedding
```

### Шаг 5: Загрузка эталонных qrels
```bash
python do_id_maps.py 1
# run_id=1 содержит gold standard
```

### Шаг 6: Запуск экспериментов (в SQL)
```sql
-- Полнотекстовый поиск
SELECT compute_fulltext_results('fulltext', 500);
-- Возвращает run_id, например 2

-- Векторный поиск
SELECT compute_vector_results_('vector (e5-large)', 500, NULL);
-- Возвращает run_id, например 3

-- RRF (full_text_weight=0.1, semantic_weight=0.9)
SELECT compute_rrf_results('RRF k=60', 500, NULL);
-- Возвращает run_id, например 4
```

### Шаг 7: Оценка качества
```sql
-- Сравнение эксперимента (run_id=2) с эталоном (run_id=1)
SELECT * FROM compare_f1_macro(1, 2, NULL, 0, 10);
```

## 5. Входные данные

| Датасет | Описание |
|---------|----------|
| `kaengreg/wikifacts-window_5` (corpus) | Документы с полем `text` |
| `kaengreg/wikifacts-window_5` (queries) | Запросы с полем `text` |
| `kaengreg/wikifacts-window_5-qrels` | Релевантность: `query-id`, `corpus-id`, `score` |

## 6. Выходные данные

| Выход | Формат |
|-------|--------|
| `id_mapping.csv` | `table, db_id, dataset_id` |
| Таблица `result` | Связи `(query_id, news_id, run_id, rank)` |
| Результат `compare_f1_macro()` | `(macro_precision, macro_recall, macro_f1)` |

## 7. Зависимости

**Python:**
```
psycopg2
datasets
sentence-transformers
torch
tqdm
numpy
```

**PostgreSQL:**
- Расширение `pgvector`
- Русский словарь для полнотекстового поиска


```