# Отчёт по домашнему заданию: базы данных, пользователи и права

## Цель работы

- Создать базу данных, схему и таблицу.
- Настроить роль только для чтения (`readonly`) и пользователя `testread`.
- Разобрать типичные ошибки при выдаче прав (схема, `search_path`, область действия `GRANT`).
- Понять, почему пользователь без явных прав на `INSERT`/`CREATE` иногда всё же может создавать объекты в `public`.
- Закрепить практики, чтобы подобные ситуации не повторялись.

## Окружение

| Параметр | Значение |
|----------|----------|
| СУБД | PostgreSQL 11.22 (Astra) |
| Порт кластера | 5433 |
| Суперпользователь | `postgres` |
| База данных | `testdb` |
| Схема | `testnm` |
| Роль чтения | `readonly` |
| Пользователь | `testread` / пароль `test123` |

---

## 1. Подготовка объектов

Под `postgres` в базе `testdb`:

```sql
CREATE SCHEMA testnm;
CREATE TABLE t1 (c1 integer);
INSERT INTO t1 (c1) VALUES (1);
```

Создана роль `readonly`, пользователь `testread`, выданы права:

```sql
GRANT CONNECT ON DATABASE testdb TO readonly;
GRANT USAGE ON SCHEMA testnm TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA testnm TO readonly;

CREATE USER testread WITH PASSWORD 'test123';
GRANT readonly TO testread;
```

---

## 2. Первый вход под `testread`: `SELECT * FROM t1` — не сработало

```text
testdb=> SELECT * FROM t1;
ОШИБКА:  нет доступа к таблице t1
```

Список таблиц (`\d`):

```text
 Схема  | Имя |   Тип   | Владелец
--------+-----+---------+----------
 public | t1  | таблица | postgres
```

### Что произошло

Команда `CREATE TABLE t1 (...)` **без указания схемы** создала таблицу в схеме **`public`**, а не в `testnm`. Права выдавались только на таблицы **в схеме `testnm`**, поэтому `readonly` / `testread` к `public.t1` доступа не имели.

### Почему так, хотя «права дали»

Права были выданы корректно, но **на другой объект**: на таблицы схемы `testnm`, а фактическая таблица лежала в `public`. PostgreSQL различает объекты по полному имени `(схема, таблица)`.

### Как не повторять

- Всегда указывать схему явно: `CREATE TABLE testnm.t1 (...)`.
- Либо перед созданием объектов выставить `search_path`, например: `SET search_path TO testnm;`.
- После создания таблицы проверять размещение: `\d`, `\dt testnm.*`, `\dt public.*`.

---

## 3. Пересоздание таблицы в нужной схеме

Под `postgres`:

```sql
DROP TABLE t1;
CREATE TABLE testnm.t1 (c1 integer);
INSERT INTO testnm.t1 (c1) VALUES (1);
```

Повторный вход `testread`:

```sql
SELECT * FROM testnm.t1;
```

Снова **ошибка доступа**, пока суперпользователь не выполнил повторную выдачу прав на уже существующие таблицы.

### Что произошло

`GRANT SELECT ON ALL TABLES IN SCHEMA testnm` действует **только на таблицы, которые уже есть на момент выполнения команды**. После `DROP` / `CREATE` появилась **новая** таблица `testnm.t1` — для неё привилегии нужно выдать заново (или настроить `ALTER DEFAULT PRIVILEGES` для будущих таблиц).

Повторная выдача привелегий:

```sql
GRANT SELECT ON ALL TABLES IN SCHEMA testnm TO readonly;
```

### Почему `testread` не может сам выполнить `GRANT`

Выдать права на чужую таблицу может владелец таблицы, суперпользователь или роль с нужными правами `GRANT OPTION`. Обычный пользователь `testread` этого сделать не может.

---

## 4. Успешное чтение

После выдачи `SELECT` суперпользователем:

```sql
SELECT * FROM testnm.t1;
```

```text
 c1
----
  1
(1 строка)
```

Чтение по полному имени схемы заработало: таблица в `testnm`, права на `SELECT` есть.

---

## 5. `search_path` и неполное имя `t1`

Для удобства на уровне базы задан путь поиска:

```sql
ALTER DATABASE testdb SET search_path TO testnm;
```

После переподключения `testread`:

```sql
SELECT * FROM t1;
```

```text
 c1
----
  1
```

Теперь неполное имя `t1` разрешается в `testnm.t1`, а не в `public.t1`.

## 6. Попытка `CREATE TABLE` и `INSERT` под `testread`

После настройки `search_path` на `testnm` и без прав `CREATE` на эту схему:

```text
CREATE TABLE t2 (c2 integer);
ОШИБКА:  нет доступа к схеме testnm
```

Создание в целевой схеме без `GRANT CREATE ON SCHEMA testnm` корректно запрещено.

### Как убрать «лишние» права на `public` 

Под `postgres` в `testdb`:

```sql
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
```

При необходимости явно выдать `USAGE` только тем, кому нужен доступ к `public`.

Дополнительно для будущих таблиц в `testnm` (чтобы новые таблицы сразу читались ролью `readonly`):

```sql
ALTER DEFAULT PRIVILEGES IN SCHEMA testnm
  GRANT SELECT ON TABLES TO readonly;
```

(Выполнять от имени роли, которая создаёт таблицы — обычно `postgres` или владелец схемы.)

---

## 7. Вторая проверка: `CREATE TABLE t3` и `INSERT INTO t2`

```sql
CREATE TABLE t3 (c1 integer);
INSERT INTO t2 VALUES (2);
```

| Команда | Ожидаемое поведение после ужесточения `public` |
|---------|--------------------------------------------------|
| `CREATE TABLE t3` | Ошибка: нет `CREATE` на схему (часто `testnm` или `public` — в зависимости от `search_path`) |
| `INSERT INTO t2` | Ошибка, если `t2` не существует или нет прав `INSERT`; если `t2` — чужая таблица в `testnm`, только `SELECT` у `readonly` недостаточно |

