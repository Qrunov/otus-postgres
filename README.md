# Отчёт по выполнению домашнего задания: «Триггеры, поддержка заполнения витрин»

## Цель задания

Создать триггер для поддержки витрины данных (`good_sum_mart`) в актуальном состоянии при изменениях в таблице продаж (`sales`).

## Исходная структура БД

### Создание схемы и настройка пути поиска

```sql
CREATE SCHEMA pract_functions;
SET search_path = pract_functions, public;
```

### Таблица товаров (`goods`)

```sql
CREATE TABLE goods (
    goods_id    integer PRIMARY KEY,
    good_name   varchar(63) NOT NULL,
    good_price  numeric(12, 2) NOT NULL CHECK (good_price > 0.0)
);
```

**Заполнение таблицы товаров:**

```sql
INSERT INTO goods (goods_id, good_name, good_price)
VALUES  (1, 'Спички хозяйственные', 0.50),
        (2, 'Автомобиль Ferrari FXX K', 185000000.01);
```

**Результат:** `INSERT 0 2` (добавлено 2 записи).

### Таблица продаж (`sales`)

```sql
CREATE TABLE sales (
    sales_id    integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    good_id     integer REFERENCES goods (goods_id),
    sales_time  timestamp with time zone DEFAULT now(),
    sales_qty   integer CHECK (sales_qty > 0)
);
```

**Заполнение таблицы продаж:**

```sql
INSERT INTO sales (good_id, sales_qty) VALUES (1, 10), (1, 1), (1, 120), (2, 1);
```

**Результат:** `INSERT 0 4` (добавлено 4 записи).

### Витрина данных (`good_sum_mart`)

```sql
CREATE TABLE good_sum_mart (
    good_name   varchar(63) NOT NULL,
    sum_sale    numeric(16, 2) NOT NULL
);
```

**Инициализация витрины данными:**

```sql
insert into good_sum_mart
SELECT G.good_name, sum(G.good_price * S.sales_qty)
FROM goods G
INNER JOIN sales S ON S.good_id = G.goods_id
GROUP BY G.good_name;
```

**Результат:** `INSERT 0 2` (заполнено 2 записи в витрине).

**Содержимое витрины после инициализации:**

| good_name | sum |
|----------|---------|
| Автомобиль Ferrari FXX K | 185 000 000,01 |
| Спички хозяйственные | 65,50 |

## Реализация триггера

### Функция-триггер

```sql
create or replace function sales_trigger()
returns trigger as
$BODY$
DECLARE
    good_ record;
BEGIN
    if TG_OP = 'DELETE' then
        select into good_ * from goods where goods_id = old.good_id;
        update good_sum_mart set sum_sale = sum_sale - old.sales_qty * good_.good_price where good_name = good_.good_name;
        return old;
    else
        select into good_ * from goods where goods_id = new.good_id;
        if TG_OP = 'INSERT' then
            perform good_name from good_sum_mart where good_name = good_.good_name;
            if NOT FOUND then
                insert into good_sum_mart values(good_.good_name, new.sales_qty * good_.good_price);
            else
                update good_sum_mart set sum_sale = sum_sale + coalesce(new.sales_qty, 0) * good_.good_price where good_.good_name = good_name;
            end if;
        else
            update good_sum_mart set sum_sale = sum_sale + (coalesce(new.sales_qty, 0) - old.sales_qty) * good_.good_price where good_.good_name = good_name;
        end if;
        return new;
    end if; 
END;
$BODY$
LANGUAGE 'plpgsql';
```

**Результат создания функции:** `CREATE FUNCTION`.

### Привязка триггера к таблице

```sql
create or replace trigger sales_trg after update or delete or insert on sales
for each row
execute function sales_trigger();
```

**Результат создания триггера:** `CREATE TRIGGER`.

## Тестирование работы триггера

### Сценарий 1: Добавление новых продаж

**Команда:**

```sql
INSERT INTO sales (good_id, sales_qty) VALUES (2, 5), (1, 50);
```

**Результат выполнения:** `INSERT 0 2`.

**Проверка содержимого витрины после вставки:**

```sql
select * from good_sum_mart;
```

**Результат:**

| good_name | sum_sale |
|----------|-------------|
| Автомобиль Ferrari FXX K | 1 110 000 000,06 |
| Спички хозяйственные | 90,50 |

### Сценарий 2: Обновление количества продаж

**Команда:**

```sql
update sales set sales_qty = 3 where sales_id = 5;
```

**Результат выполнения:** `UPDATE 1`.

**Проверка содержимого витрины после обновления:**

```sql
select * from good_sum_mart;
```

**Результат:**

| good_name | sum_sale |
|----------|-------------|
| Спички хозяйственные | 90,50 |
| Автомобиль Ferrari FXX K | 740 000 000,04 |

### Сценарий 3: Удаление продажи

**Команда:**

```sql
delete from sales where sales_id = 1;
```

**Результат выполнения:** `DELETE 1`.

**Проверка содержимого витрины после удаления:**

```sql
select * from good_sum_mart;
```

**Результат:**

| good_name | sum_sale |
|----------|-------------|
| Автомобиль Ferrari FXX K | 740 000 000,04 |
| Спички хозяйственные | 85,50 |

### Сценарий 4: Продажа нового товара

**Добавление нового товара в справочник:**

```sql
INSERT INTO goods (goods_id, good_name, good_price)
VALUES (3, 'Молоко', 100);
```

**Результат:** `INSERT 0 1`.

**Продажа нового товара:**

```sql
INSERT INTO sales (good_id, sales_qty) VALUES (3, 3);
```

**Результат:** `INSERT 0 1`.

**Проверка итогового состояния витрины:**

```sql
select * from good_sum_mart;
```

**Результат:**

| good_name | sum_sale |
|----------|-------------|
| Автомобиль Ferrari FXX K | 740 000 000,04 |
| Спички хозяйственные | 85,50 |
| Молоко | 300,00 |

## Проверка содержимого таблиц после всех операций

### Содержимое таблицы `sales`

```sql
select * from sales;
```

**Результат:**

| sales_id | good_id | sales_time | sales_qty |
|----------|---------|-------------|-----------|
| 2 | 1 | 2026-06-12 10:12:49.749934+03 | 1 |
| 3 | 1 | 2026-06-12 10:12:49.749934+03 | 120 |
| 4 | 2 | 2026-06-12 10:12:49.749934+03 | 1 |
| 6 | 1 | 2026-06-12 10:12:49.752514+03 | 50 |
| 5 | 2 | 2026-06-12 10:12:49.752514+03 | 3 |
| 7 | 3 | 2026-06-12 10:12:49.754031+03 | 3 |

## Ответ на задание со звёздочкой

**Преимущества схемы «витрина + триггер» перед отчётом «по требованию»:**

1. **Актуальность данных.** Витрина всегда содержит актуальные данные, не требует пересчёта при каждом запросе.
2. **Учёт изменений цен.** При изменении цены товара в будущем исторические продажи остаются корректными, так как в витрине хранится итоговая сумма, а не расчёт «на лету».
3. **Упрощение запросов.** Для получения отчёта достаточно простого `SELECT * FROM good_sum_mart`, без сложных `JOIN` и агрегаций.

## Вывод

Триггер `sales_trg`, привязанный к функции `sales_trigger()`, успешно выполняет свою задачу — поддерживает витрину данных `good_sum_mart` в актуальном состоянии.