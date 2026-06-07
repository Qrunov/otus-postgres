<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Отчёт: Настройка миникластера PostgreSQL с репликацией

## Цель работы

Реализовать миникластер на трёх виртуальных машинах с логической репликацией PostgreSQL и настроить физическую репликацию на четвёртую ВМ.

***

## Архитектура кластера

| ВМ | Порт | Роль | Таблица для записи | Таблица для чтения |
| :-- | :-- | :-- | :-- | :-- |
| ВМ1 (ex14_vm1) | 5433 | Публикатор test + Подписчик test2 | test | test2 |
| ВМ2 (ex14_vm2) | 5434 | Публикатор test2 + Подписчик test | test2 | test |
| ВМ3 (ex14_vm3) | 5435 | Подписчик (оба стола) + Резерв | — | test + test2 |
| ВМ4 (ex14_vm4) | 5436 | Физический репликат (от ВМ3) | — | test + test2 |


***

## Пошаговая настройка

### 1. Настройка ВМ1 (порт 5433)

**Создание таблиц:**

```sql
CREATE TABLE test(id int);      -- для записи
CREATE TABLE test2(id int);     -- для чтения
```

**Настройка публикации:**

```sql
CREATE PUBLICATION pub_test FOR TABLE test;
ALTER SYSTEM SET wal_level = 'logical';
```

После изменения `wal_level` выполнен перезапуск кластера:

```bash
pg_ctlcluster restart 15 ex14_vm1
```

**Подтверждение публикации:**

```sql
SELECT * FROM pg_publication_tables;
-- pub_test | public | test
```

**Подписка на test2 с ВМ2:**

```sql
CREATE SUBSCRIPTION test2_sub 
  CONNECTION 'port=5434' 
  PUBLICATION test2_pub;
```


***

### 2. Настройка ВМ2 (порт 5434)

**Создание таблиц:**

```sql
CREATE TABLE test2(id int);     -- для записи
CREATE TABLE test(id int);      -- для чтения
```

**Настройка `wal_level`:**

```sql
ALTER SYSTEM SET wal_level = 'logical';
```

Перезапуск кластера:

```bash
pg_ctlcluster restart 15 ex14_vm2
```

**Создание публикации:**

```sql
CREATE PUBLICATION test2_pub FOR TABLE test2;
```

**Подписка на test с ВМ1:**

```sql
CREATE SUBSCRIPTION test_sub 
  CONNECTION 'port=5433' 
  PUBLICATION pub_test;
```

**Проверка репликации:**

```sql
SELECT * FROM test;
-- id: 1, 2, 3 (данные из ВМ1)
```


***

### 3. Настройка ВМ3 (порт 5435)

**Настройка `wal_level`:**

```sql
ALTER SYSTEM SET wal_level = 'logical';
pg_ctlcluster restart 15 ex14_vm3
```

**Создание таблиц:**

```sql
CREATE TABLE test(id int);
CREATE TABLE test2(id int);
```

**Подписки на обе публикации:**

```sql
CREATE SUBSCRIPTION test_vm3_sub 
  CONNECTION 'port=5433' 
  PUBLICATION pub_test;

CREATE SUBSCRIPTION test2_vm3_sub 
  CONNECTION 'port=5434' 
  PUBLICATION test2_pub;
```

**Проверка данных:**

```sql
SELECT * FROM test;   -- id: 1, 2, 3
SELECT * FROM test2;  -- id: 4, 5, 6
```


***

### 4. Настройка ВМ4 (порт 5436) — физическая репликация

**Подготовка:**

```bash
pg_ctlcluster stop 15 ex14_vm4
rm -fr /var/lib/postgresql/15/ex14_vm4/
```

**Создание физической реплики через pg_basebackup:**

```bash
sudo -u postgres pg_basebackup \
  -D /var/lib/postgresql/15/ex14_vm4 \
  -W -R -p 5435 -U postgres
```

Ключи:

- `-D` — директория для данных
- `-W` — запрос пароля
- `-R` — создать `postgresql.auto.conf` с настройками replication
- `-p 5435` — порт источника (ВМ3)

**Запуск кластера:**

```bash
pg_ctlcluster start 15 ex14_vm4
```

**Подтверждение режима репликации:**

```sql
SELECT * FROM pg_is_in_recovery();
-- true (t) — узел в режиме standby
```

**Проверка данных:**

```sql
SELECT * FROM test;   -- id: 1, 2, 3
SELECT * FROM test2;  -- id: 4, 5, 6
```


***

## Проверка работы системы

### Тест 1: Вставка в `test` на ВМ1

```sql
-- ВМ1
INSERT INTO test SELECT 1 UNION SELECT 2 UNION SELECT 3;
```

**Результат:**

- ВМ2: `SELECT * FROM test;` → 1, 2, 3 ✓
- ВМ3: `SELECT * FROM test;` → 1, 2, 3 ✓
- ВМ4: `SELECT * FROM test;` → 1, 2, 3 ✓


### Тест 2: Вставка в `test2` на ВМ2

```sql
-- ВМ2
INSERT INTO test2 SELECT 4 UNION SELECT 5 UNION SELECT 6;
```

**Результат:**

- ВМ1: `SELECT * FROM test2;` → 4, 5, 6 ✓
- ВМ3: `SELECT * FROM test2;` → 4, 5, 6 ✓
- ВМ4: `SELECT * FROM test2;` → 4, 5, 6 ✓

***

## Итоговая схема репликации

```
ВМ1 (test ⊢ публикация) ──┐
                          ├─► ВМ3 (test подписка) ──┐
ВМ2 (test2 ⊢ публикация) ─┤                        ├─► ВМ4 (физическая реплика)
                          ├─► ВМ3 (test2 подписка) ─┘
                          │
ВМ1 (подписка test2) ◄────┘
ВМ2 (подписка test)  ◄────┘
```


***

## Ключевые моменты

| Параметр | Значение |
| :-- | :-- |
| `wal_level` | `logical` (обязательно для логической репликации) |
| Тип репликации ВМ1–ВМ3 | Логическая (logical replication через publication/subscription) |
| Тип репликации ВМ3–ВМ4 | Физическая (streaming replication через pg_basebackup) |
| Флаг `standby.signal` | Автоматически создан pg_basebackup для ВМ4 |
| Слоты репликации | Автоматически создаются при `CREATE SUBSCRIPTION` |


***

## Выводы

✅ Миникластер из 3 ВМ с двусторонней логической репликацией успешно настроен
✅ ВМ3 работает как объединённая точка чтения для обеих таблиц
✅ Физическая реплика ВМ4 корректно синхронизируется с ВМ3
✅ Все тесты вставки подтверждают работоспособность репликации во всех узлах

Репликация работает в обоих направлениях: данные из `test` на ВМ1 реплицируются на ВМ2 и ВМ3, данные из `test2` на ВМ2 реплицируются на ВМ1 и ВМ3. ВМ4 получает полные данные через физическую репликацию.

