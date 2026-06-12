# Отчет по выполнению задания

## Цель работы

Применить логический бэкап и восстановиться из бэкапа.

## Выполненные действия

### 1. Создание базы данных и схемы

```sql
create database test_db;
```

**Результат:**
```text
CREATE DATABASE
```

```sql
\c test_db;
```

**Результат:**
```text
Вы подключены к базе данных "test_db" как пользователь "postgres".
```

```sql
create schema my_schema;
```

**Результат:**
```text
CREATE SCHEMA
```

```text
SET search_path = my_schema, public;
```

### 2. Создание таблиц

```sql
create table table1(id int);
```

**Результат:**
```text
CREATE TABLE
```

```sql
create table table2 (like table1);
```

**Результат:**
```text
CREATE TABLE
```

### 3. Заполнение таблицы данными

```sql
insert into table1 select generate_series(1, 100);
```

**Результат:**
```text
INSERT 0 100
```

### 4. Бэкап через COPY

Создание каталога для бэкапов под пользователем `postgres`:

```bash
mkdir -p /var/lib/postgresql/backups/
```

Выгрузка данных из `table1` в файл:

```sql
\copy table1 to /var/lib/postgresql/backups/table1
```

**Результат:**
```text
COPY 100
```

### 5. Восстановление из COPY

Загрузка данных из файла в `table2`:

```sql
\copy table2 from /var/lib/postgresql/backups/table1
```

**Результат:**
```text
COPY 100
```

Проверка содержимого `table1`:

```sql
select * from table1 order by id limit 10;
```

**Результат:**
```text
 id
----
  1
  2
  3
  4
  5
  6
  7
  8
  9
 10
(10 строк)
```

Проверка содержимого `table2`:

```sql
select * from table2 order by id limit 10;
```

**Результат:**
```text
 id
----
  1
  2
  3
  4
  5
  6
  7
  8
  9
 10
(10 строк)
```

### 6. Создание дампа через pg_dump

Создание дампа схемы `my_schema` в формате `-Fc`:

```bash
pg_dump -U postgres -p 5433 -Fc --schema my_schema test_db > /var/lib/postgresql/backups/test_db
```

**Результат:**
```text
Команда выполнена успешно.
```

### 7. Создание базы для восстановления

```sql
create database restored_db;
```

**Результат:**
```text
CREATE DATABASE
```

```sql
\c restored_db;
```

**Результат:**
```text
Вы подключены к базе данных "restored_db" как пользователь "postgres".
```

### 8. Подготовка схемы для восстановления

```sql
create schema my_schema;
```

**Результат:**
```text
CREATE SCHEMA
```

### 9. Восстановление через pg_restore

Восстановление только `table2` из дампа:

```bash
pg_restore -U postgres -p 5433 -d restored_db -t table2 /var/lib/postgresql/backups/test_db
```

**Результат:**
```text
Команда выполнена успешно.
```

### 10. Проверка восстановленных данных

```sql
select * from my_schema.table2 order by id limit 20;
```

**Результат:**
```text
 id
----
  1
  2
  3
  4
  5
  6
  7
  8
  9
 10
 11
 12
 13
 14
 15
 16
 17
 18
 19
 20
(20 строк)
```

## Итог

Выполнены логический бэкап через `\copy`, создание дампа схемы через `pg_dump -Fc`, а также восстановление данных в новую базу через `pg_restore`.

Проверка показала, что данные успешно восстановлены.