# Отчёт по домашнему заданию: настройка autovacuum с учётом особенностей производительности

## Цель работы

1. Развернуть инстанс PostgreSQL и подготовить БД для нагрузочного теста (`pgbench -i`).
2. Запустить нагрузочный тест `pgbench`, применить параметры тюнинга из материалов занятия и повторить тест.
3. Создать таблицу с текстовым полем (1 млн строк), наблюдать рост размера и работу autovacuum при массовых `UPDATE`.
4. Отключить autovacuum на таблице, накопить «мёртвые» строки и сравнить размер файла.
5. Восстановить autovacuum и (по заданию со *) оформить цикл обновлений в анонимной процедуре.

---

## Исходные условия

| Параметр | Значение |
|----------|----------|
| ОС | Astra Linux |
| СУБД | PostgreSQL **15** |
| Кластер | `ex6`, порт **5433** |
| Каталог данных | `/var/lib/postgresql/15/ex6` |
| База для тестов | `postgres` |
| Пользователь | `postgres` |

Для изоляции эксперимента остановлен кластер `main` (порт 5432), пересоздан кластер `ex6`:

```bash
pg_ctlcluster stop 15 ex6
pg_dropcluster 15 ex6
pg_createcluster 15 ex6
pg_ctlcluster start 15 ex6
```

Проверка:

```text
Ver Cluster Port Status Owner    Data directory
15  ex6     5433 online postgres /var/lib/postgresql/15/ex6
15  main    5432 down   postgres /var/lib/postgresql/15/main
```

Подключение к тестовому кластеру: `-p 5433 -U postgres`.

---

## 1. Подготовка БД и первый нагрузочный тест

### Инициализация схемы pgbench

```bash
pgbench -i postgres -p 5433 -U postgres
```

Созданы таблицы `pgbench_*`, масштаб 1 (100 000 счетов), время инициализации ~1 с.

### Первый прогон (настройки по умолчанию)

```bash
pgbench -p 5433 -c8 -P 6 -T 60 -U postgres postgres
```

| Метрика | Значение |
|---------|----------|
| Клиенты (`-c`) | 8 |
| Длительность (`-T`) | 60 с |
| Отчёт (`-P`) | каждые 6 с |
| **TPS (итог)** | **53,08** |
| Средняя задержка | 150,5 ms |
| σ задержки | 119,3 ms |
| Транзакций за 60 с | 3193 |

---

## 2. Применение параметров тюнинга

Параметры заданы через `ALTER SYSTEM` (файл `postgresql.auto.conf`), затем кластер перезапущен:

```bash
pg_ctlcluster stop 15 ex6
pg_ctlcluster start 15 ex6
```

| Параметр | Значение |
|----------|----------|
| `max_connections` | 40 |
| `shared_buffers` | 1 GB |
| `effective_cache_size` | 3 GB |
| `maintenance_work_mem` | 512 MB |
| `checkpoint_completion_target` | 0.9 |
| `wal_buffers` | 16 MB |
| `default_statistics_target` | 500 |
| `random_page_cost` | 4 |
| `effective_io_concurrency` | 2 |
| `work_mem` | 6553 kB |
| `min_wal_size` | 4 GB |
| `max_wal_size` | 16 GB |

---
## 3. Повторный нагрузочный тест

```bash
pgbench -p 5433 -c8 -P 6 -T 60 -U postgres postgres
```

| Метрика | До тюнинга | После тюнинга |
|---------|------------|---------------|
| **TPS** | **53,08** | **45,93** |
| Средняя задержка | 150,5 ms | 174,0 ms |
| σ задержки | 119,3 ms | 133,0 ms |
| Транзакций | 3193 | 2762 |

## 4. Таблица с текстовым полем и autovacuum

### Создание и начальный размер

```sql
CREATE TABLE a(b text);
INSERT INTO a(b)
  (SELECT left(md5(random()::text), 8) FROM generate_series(1, 1000000));
```

| Показатель | Значение |
|------------|----------|
| Строк | 1 000 000 |
| `pg_total_relation_size('a')` | **50 MB** |

### Первые 5 массовых обновлений

```sql
UPDATE a SET b = left(md5(random()::text), 8);  -- ×4
UPDATE a SET b = b || left(md5(random()::text), 1);  -- добавление символа
```

Проверка autovacuum:

```sql
SELECT n_dead_tup, last_autovacuum
FROM pg_stat_user_tables WHERE relname = 'a';
```

| Этап | `n_dead_tup` | `last_autovacuum` |
|------|----------------|-------------------|
| До срабатывания AV | 2 999 875 | 2026-05-13 18:02:16+03 |
| После ожидания AV | **0** | 2026-05-13 18:03:13+03 |

**Autovacuum сработал** в течение ~1 минуты: удалил мёртвые версии строк, обновил статистику, `n_dead_tup` обнулён.

### Вторые 5 обновлений (autovacuum включён)

Те же команды (`UPDATE` ×4 + `UPDATE` с конкатенацией).

| Показатель | Значение |
|------------|----------|
| `pg_total_relation_size('a')` | **329 MB** |

Размер вырос из‑за:

- накопления **мёртвых tuple** между проходами vacuum;
- **раздувания** строк (`b || символ` увеличивает длину текста);
- до следующего autovacuum / autovacuum freeze место в файле не возвращается ОС полностью.

---

## 5. Отключение autovacuum на таблице

```sql
ALTER TABLE a SET (autovacuum_enabled = off);
```

### 10 массовых обновлений

```sql
UPDATE a SET b = left(md5(random()::text), 8);  -- ×9
UPDATE a SET b = b || left(md5(random()::text), 1);
```

| Показатель | С AV (после 5+5 UPDATE) | Без AV (после 10 UPDATE) |
|------------|-------------------------|---------------------------|
| Размер таблицы | 329 MB | **597 MB** |

### Объяснение результата

При **отключённом** `autovacuum_enabled`:

- каждый `UPDATE` оставляет старую версию строки в куче (**dead tuples**);
- за 10 полных проходов по 1 млн строк накапливается порядка **10 млн** мёртвых версий (плюс bloat от удлинения `text`);
- при этом наблидается рост файла в ~10 раз относительно начального(после начального заполнения) размера, используется свободное пространство предыдущего этапа

Восстановление:

```sql
ALTER TABLE a SET (autovacuum_enabled = on);
```
---

## 6. Задание со *: анонимная процедура (10 итераций UPDATE)

```sql
CREATE OR REPLACE FUNCTION public.insert_x_10()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    i int4;
BEGIN
    i := 0;
    WHILE i < 10 LOOP
        i := i + 1;
        RAISE NOTICE 'iter = %', i;
        UPDATE a SET b = left(md5(random()::text), 8);
    END LOOP;
END;
$$;
```

Вызов:

```sql
SELECT public.insert_x_10();
```

---

## Выводы

1. Кластер **15/ex6** на порту 5433 успешно использован для `pgbench` и экспериментов с таблицей `a`.
2. **Autovacuum** при массовых `UPDATE` заметен по `pg_stat_user_tables`: рост `n_dead_tup` до миллионов и обнуление после срабатывания AV.
3. **Отключение autovacuum** на таблице приводит к быстрому раздуванию размера файла таблицы.
---
