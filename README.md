# Домашнее задание: работа с JOIN

## Цель работы

Изучить и применить разные виды соединений таблиц в PostgreSQL: `INNER JOIN`, `LEFT JOIN`, `CROSS JOIN`, `FULL JOIN`, а также запросы со смешанными типами соединений. Дополнительно необходимо уметь анализировать структуру таблиц, понимать результаты соединений и использовать `EXPLAIN` / `EXPLAIN ANALYZE` для изучения плана выполнения запроса.

## Структура таблиц

В работе использовались две таблицы: `test` и `test2`.

```sql
CREATE TABLE test (
    key int,
    value text
);

CREATE TABLE test2 (
    key int,
    value text
);
```

### Таблица `test`

| Поле | Тип | Назначение |
|---|---|---|
| key | int | Ключ для соединения |
| value | text | Текстовое значение |

### Таблица `test2`

| Поле | Тип | Назначение |
|---|---|---|
| key | int | Ключ для соединения |
| value | text | Текстовое значение |

## Заполнение таблиц

В таблицу `test` были добавлены ключи от `1` до `10`, после чего для поля `value` были сгенерированы случайные строковые значения. В таблицу `test2` были добавлены ключи `1..3` и `10..13`, после чего аналогично заполнено поле `value`.

```sql
INSERT INTO test(key)
SELECT generate_series(1, 10);

UPDATE test
SET value = md5(random()::text);

INSERT INTO test2(key)
SELECT generate_series(1, 3);

INSERT INTO test2(key)
SELECT generate_series(10, 13);

UPDATE test2
SET value = md5(random()::text);
```

## Прямое соединение

Прямое соединение реализовано через `INNER JOIN`. Оно возвращает только те строки, у которых ключи совпадают в обеих таблицах.

```sql
SELECT *
FROM test
JOIN test2 USING(key);
```

### Результат

Совпадающие ключи: `1, 2, 3, 10`.

| key | test.value | test2.value |
|---|---|---|
| 1 | e7aad9e8757aecac6b9b22911461918a | a0bbbee7246f3ce679181f86f78733b7 |
| 2 | d5520826ecd1dcb78e9709f73b259afc | 5d7abe8a15ac60c455bef4c928b08d6d |
| 3 | 23a4053c67b8f0c99607a32b5802edc5 | d6bd060f1ddc6e1b46f9977c87e9ce99 |
| 10 | 947a0b0a3b3ccc1233dfd1a91371dfad | 5c4e8262190b9d15b24b19cf2f9c5e2b |

## Левостороннее соединение

Левостороннее соединение возвращает все строки из левой таблицы и совпавшие строки из правой. Если совпадения нет, поля правой таблицы заполняются `NULL`.

```sql
SELECT *
FROM test
LEFT JOIN test2 USING(key);
```

### Результат

Все строки из `test` были сохранены, а для ключей `4..9` значения из `test2` отсутствуют.

| key | test.value | test2.value |
|---|---|---|
| 1 | e7aad9e8757aecac6b9b22911461918a | a0bbbee7246f3ce679181f86f78733b7 |
| 2 | d5520826ecd1dcb78e9709f73b259afc | 5d7abe8a15ac60c455bef4c928b08d6d |
| 3 | 23a4053c67b8f0c99607a32b5802edc5 | d6bd060f1ddc6e1b46f9977c87e9ce99 |
| 4 | 370260027487cae8f5698cee71d790cb | NULL |
| 5 | d8da2c08f6f79526a69a16affd7b7e9f | NULL |
| 6 | 947b90f1eaab3f0bce78752f377b2722 | NULL |
| 7 | 0090f8dbb1f9edf99bc4004eaf2b0a5a | NULL |
| 8 | df856a69a28057d065538ce3513a769c | NULL |
| 9 | 502352f046433a685e5a4c8777636137 | NULL |
| 10 | 947a0b0a3b3ccc1233dfd1a91371dfad | 5c4e8262190b9d15b24b19cf2f9c5e2b |

## Кросс соединение

`CROSS JOIN` формирует декартово произведение таблиц: каждая строка первой таблицы соединяется с каждой строкой второй таблицы.

```sql
SELECT *
FROM test
CROSS JOIN test2
LIMIT 20;
```

### Результат

Поскольку в `test` 10 строк, а в `test2` 7 строк, полный результат содержал бы 70 строк. Ниже приведены первые 20 строк результата.

| test.key | test.value | test2.key | test2.value |
|---|---|---|---|
| 1 | e7aad9e8757aecac6b9b22911461918a | 1 | a0bbbee7246f3ce679181f86f78733b7 |
| 1 | e7aad9e8757aecac6b9b22911461918a | 2 | 5d7abe8a15ac60c455bef4c928b08d6d |
| 1 | e7aad9e8757aecac6b9b22911461918a | 3 | d6bd060f1ddc6e1b46f9977c87e9ce99 |
| 1 | e7aad9e8757aecac6b9b22911461918a | 10 | 5c4e8262190b9d15b24b19cf2f9c5e2b |
| 1 | e7aad9e8757aecac6b9b22911461918a | 11 | bbbe9bc3bc6d53b5430a2d3251db7518 |
| 1 | e7aad9e8757aecac6b9b22911461918a | 12 | fb37e0cb67acfefc41a60fc35eeabe20 |
| 1 | e7aad9e8757aecac6b9b22911461918a | 13 | e1ddce6c7000741f4c1b914fd71b4a7a |
| 2 | d5520826ecd1dcb78e9709f73b259afc | 1 | a0bbbee7246f3ce679181f86f78733b7 |
| 2 | d5520826ecd1dcb78e9709f73b259afc | 2 | 5d7abe8a15ac60c455bef4c928b08d6d |
| 2 | d5520826ecd1dcb78e9709f73b259afc | 3 | d6bd060f1ddc6e1b46f9977c87e9ce99 |
| 2 | d5520826ecd1dcb78e9709f73b259afc | 10 | 5c4e8262190b9d15b24b19cf2f9c5e2b |
| 2 | d5520826ecd1dcb78e9709f73b259afc | 11 | bbbe9bc3bc6d53b5430a2d3251db7518 |
| 2 | d5520826ecd1dcb78e9709f73b259afc | 12 | fb37e0cb67acfefc41a60fc35eeabe20 |
| 2 | d5520826ecd1dcb78e9709f73b259afc | 13 | e1ddce6c7000741f4c1b914fd71b4a7a |
| 3 | 23a4053c67b8f0c99607a32b5802edc5 | 1 | a0bbbee7246f3ce679181f86f78733b7 |
| 3 | 23a4053c67b8f0c99607a32b5802edc5 | 2 | 5d7abe8a15ac60c455bef4c928b08d6d |
| 3 | 23a4053c67b8f0c99607a32b5802edc5 | 3 | d6bd060f1ddc6e1b46f9977c87e9ce99 |
| 3 | 23a4053c67b8f0c99607a32b5802edc5 | 10 | 5c4e8262190b9d15b24b19cf2f9c5e2b |
| 3 | 23a4053c67b8f0c99607a32b5802edc5 | 11 | bbbe9bc3bc6d53b5430a2d3251db7518 |
| 3 | 23a4053c67b8f0c99607a32b5802edc5 | 12 | fb37e0cb67acfefc41a60fc35eeabe20 |

## Полное соединение

Полное соединение `FULL JOIN` возвращает все строки из обеих таблиц: совпавшие строки объединяются, а несовпавшие дополняются `NULL`.

```sql
SELECT *
FROM test
FULL JOIN test2 USING(key);
```

### Результат

В результате получены все ключи из обеих таблиц: `1..13`, при этом для несовпадающих строк одна из сторон заполнена `NULL`.

| key | test.value | test2.value |
|---|---|---|
| 1 | e7aad9e8757aecac6b9b22911461918a | a0bbbee7246f3ce679181f86f78733b7 |
| 2 | d5520826ecd1dcb78e9709f73b259afc | 5d7abe8a15ac60c455bef4c928b08d6d |
| 3 | 23a4053c67b8f0c99607a32b5802edc5 | d6bd060f1ddc6e1b46f9977c87e9ce99 |
| 4 | 370260027487cae8f5698cee71d790cb | NULL |
| 5 | d8da2c08f6f79526a69a16affd7b7e9f | NULL |
| 6 | 947b90f1eaab3f0bce78752f377b2722 | NULL |
| 7 | 0090f8dbb1f9edf99bc4004eaf2b0a5a | NULL |
| 8 | df856a69a28057d065538ce3513a769c | NULL |
| 9 | 502352f046433a685e5a4c8777636137 | NULL |
| 10 | 947a0b0a3b3ccc1233dfd1a91371dfad | 5c4e8262190b9d15b24b19cf2f9c5e2b |
| 11 | NULL | bbbe9bc3bc6d53b5430a2d3251db7518 |
| 12 | NULL | fb37e0cb67acfefc41a60fc35eeabe20 |
| 13 | NULL | e1ddce6c7000741f4c1b914fd71b4a7a |

## Смешанные соединения

В одном запросе можно использовать несколько соединений одновременно. В примере ниже одна таблица `test` соединяется с двумя разными алиасами `test2`, что позволяет показать использование нескольких `JOIN` в одном запросе.

```sql
SELECT *
FROM test
LEFT JOIN test2 t2 USING(key)
JOIN test2 t22 USING(key);
```

### Результат

Запрос вернул только строки с совпадающими ключами `1, 2, 3, 10`.

| key | test.value | t2.value | t22.value |
|---|---|---|---|
| 1 | e7aad9e8757aecac6b9b22911461918a | a0bbbee7246f3ce679181f86f78733b7 | a0bbbee7246f3ce679181f86f78733b7 |
| 2 | d5520826ecd1dcb78e9709f73b259afc | 5d7abe8a15ac60c455bef4c928b08d6d | 5d7abe8a15ac60c455bef4c928b08d6d |
| 3 | 23a4053c67b8f0c99607a32b5802edc5 | d6bd060f1ddc6e1b46f9977c87e9ce99 | d6bd060f1ddc6e1b46f9977c87e9ce99 |
| 10 | 947a0b0a3b3ccc1233dfd1a91371dfad | 5c4e8262190b9d15b24b19cf2f9c5e2b | 5c4e8262190b9d15b24b19cf2f9c5e2b |

## Анализ плана выполнения

Для анализа плана выполнения запроса в PostgreSQL используется `EXPLAIN`, а для получения фактических статистик выполнения — `EXPLAIN ANALYZE`.

Пример:

```sql
EXPLAIN ANALYZE
SELECT *
FROM test
JOIN test2 USING(key);
```

### Что позволяет увидеть план

- Тип соединения.
- Способ сканирования таблиц.
- Оценку и фактическое число строк.
- Время выполнения каждого шага.

## Вывод

В ходе работы были реализованы все требуемые виды соединений: прямое, левостороннее, кросс-соединение, полное соединение и запрос со смешанными `JOIN`. Также была рассмотрена структура таблиц, результаты выполнения запросов и способ анализа плана через `EXPLAIN ANALYZE`.