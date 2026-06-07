# Отчёт: Настройка миникластера PostgreSQL с репликацией

## Цель работы

Реализовать миникластер на трёх виртуальных машинах с логической репликацией PostgreSQL и настроить физическую репликацию на четвёртую ВМ.

***

## Хронология выполнения

### Этап 1: Настройка ВМ1 (порт 5433)

**1.1. Проверка наличия кластеров:**

```bash
pg_lsclusters
```

Подтверждено: кластер `ex14_vm1` работает на порту 5433.

**1.2. Создание таблиц:**

```sql
psql -U postgres -p 5433
CREATE TABLE test(id int);      -- для записи
CREATE TABLE test2(id int);     -- для чтения
```

**1.3. Создание публикации:**

```sql
CREATE PUBLICATION pub_test FOR TABLE test;
```

**1.4. Настройка wal_level:**

```sql
ALTER SYSTEM SET wal_level = 'logical';
```

**1.5. Перезапуск кластера:**

```bash
pg_ctlcluster restart 15 ex14_vm1
```

**1.6. Проверка публикации:**

```sql
SELECT * FROM pg_publication_tables;
-- pub_test | public | test
```


***

### Этап 2: Настройка ВМ2 (порт 5434)

**2.1. Проверка кластеров:**

```bash
pg_lsclusters
```

Подтверждено: кластер `ex14_vm2` работает на порту 5434.

**2.2. Настройка wal_level:**

```sql
psql -U postgres -p 5434
ALTER SYSTEM SET wal_level = 'logical';
```

**2.3. Перезапуск кластера:**

```bash
pg_ctlcluster restart 15 ex14_vm2
```

**2.4. Создание таблиц:**

```sql
CREATE TABLE test2(id int);     -- для записи
CREATE TABLE test(id int);      -- для чтения
```

**2.5. Создание публикации:**

```sql
CREATE PUBLICATION test2_pub FOR TABLE test2;
```


***

### Этап 3: Подписка ВМ2 на публикацию ВМ1

**3.1. Создание подписки:**

```sql
CREATE SUBSCRIPTION test_sub 
  CONNECTION 'port=5433' 
  PUBLICATION pub_test;
```

✓ Слот репликации `test_sub` создан на сервере публикации.

**3.2. Проверка репликации:**

```sql
SELECT * FROM test;
-- id: 1, 2, 3
```


***

### Этап 4: Подписка ВМ1 на публикацию ВМ2

**4.1. Создание подписки на ВМ1:**

```sql
psql -U postgres -p 5433
CREATE SUBSCRIPTION test2_sub 
  CONNECTION 'port=5434' 
  PUBLICATION test2_pub;
```

✓ Слот репликации `test2_sub` создан на сервере публикации.

***

### Этап 5: Проверка логической репликации (ВМ1 ↔ ВМ2)

**5.1. Вставка в `test` на ВМ1:**

```sql
INSERT INTO test SELECT 1 UNION SELECT 2 UNION SELECT 3;
-- INSERT 0 3
```

**5.2. Проверка на ВМ2:**

```sql
psql -U postgres -p 5434
SELECT * FROM test;
-- id: 1, 2, 3 ✓
```

**5.3. Вставка в `test2` на ВМ2:**

```sql
INSERT INTO test2 SELECT 4 UNION SELECT 5 UNION SELECT 6;
-- INSERT 0 3
```

**5.4. Проверка на ВМ1:**

```sql
psql -U postgres -p 5433
SELECT * FROM test2;
-- id: 4, 5, 6 ✓
```


***

### Этап 6: Настройка ВМ3 (порт 5435)

**6.1. Проверка кластеров:**

```bash
pg_lsclusters
```

Подтверждено: кластер `ex14_vm3` работает на порту 5435.

**6.2. Настройка wal_level:**

```sql
psql -U postgres -p 5435
ALTER SYSTEM SET wal_level = 'logical';
```

**6.3. Перезапуск кластера:**

```bash
pg_ctlcluster restart 15 ex14_vm3
```

**6.4. Создание таблиц:**

```sql
CREATE TABLE test2(id int);
CREATE TABLE test(id int);
```

**6.5. Создание подписки на ВМ1 (test):**

```sql
CREATE SUBSCRIPTION test_vm3_sub 
  CONNECTION 'port=5433' 
  PUBLICATION pub_test;
```

✓ Слот репликации `test_vm3_sub` создан.

**6.6. Создание подписки на ВМ2 (test2):**

```sql
CREATE SUBSCRIPTION test2_vm3_sub 
  CONNECTION 'port=5434' 
  PUBLICATION test2_pub;
```

✓ Слот репликации `test2_vm3_sub` создан.

***

### Этап 7: Проверка репликации на ВМ3

**7.1. Проверка `test`:**

```sql
SELECT * FROM test;
-- id: 1, 2, 3 ✓
```

**7.2. Проверка `test2`:**

```sql
SELECT * FROM test2;
-- id: 4, 5, 6 ✓
```

✓ ВМ3 успешно получает данные из обоих источников.

***

### Этап 8: Настройка физической репликации ВМ4 (порт 5436)

**8.1. Проверка входа:**

```bash
sudo su
```

**8.2. Проверка кластеров:**

```bash
pg_lsclusters
```

Подтверждено: кластер `ex14_vm4` на порту 5436.

**8.3. Остановка кластера:**

```bash
pg_ctlcluster stop 15 ex14_vm4
```

**8.4. Удаление старых данных:**

```bash
rm -fr /var/lib/postgresql/15/ex14_vm4/
```

**8.5. Создание физического репликата:**

```bash
sudo -u postgres pg_basebackup \
  -D /var/lib/postgresql/15/ex14_vm4 \
  -W -R -p 5435 -U postgres
```

✓ Backup выполнен успешно, слот репликации создан, `standby.signal` создан автоматически.

**8.6. Запуск кластера:**

```bash
pg_ctlcluster start 15 ex14_vm4
```


***

### Этап 9: Проверка физической репликации ВМ4

**9.1. Проверка режима репликации:**

```sql
psql -U postgres -p 5436
SELECT * FROM pg_is_in_recovery();
-- true (t) ✓
```

**9.2. Проверка `test`:**

```sql
SELECT * FROM test;
-- id: 1, 2, 3 ✓
```

**9.3. Проверка `test2`:**

```sql
SELECT * FROM test2;
-- id: 4, 5, 6 ✓
```

✓ ВМ4 успешно синхронизируется с ВМ3 через физическую репликацию.

***

## Финальная проверка всей системы

### Тест 1: Вставка в `test` на ВМ1

```sql
-- ВМ1 (порт 5433)
INSERT INTO test SELECT 1 UNION SELECT 2 UNION SELECT 3;
```

| Узел | Проверка | Результат |
| :-- | :-- | :-- |
| ВМ1 | `SELECT * FROM test;` | 1, 2, 3 |
| ВМ2 | `SELECT * FROM test;` | 1, 2, 3 ✓ |
| ВМ3 | `SELECT * FROM test;` | 1, 2, 3 ✓ |
| ВМ4 | `SELECT * FROM test;` | 1, 2, 3 ✓ |

### Тест 2: Вставка в `test2` на ВМ2

```sql
-- ВМ2 (порт 5434)
INSERT INTO test2 SELECT 4 UNION SELECT 5 UNION SELECT 6;
```

| Узел | Проверка | Результат |
| :-- | :-- | :-- |
| ВМ2 | `SELECT * FROM test2;` | 4, 5, 6 |
| ВМ1 | `SELECT * FROM test2;` | 4, 5, 6 ✓ |
| ВМ3 | `SELECT * FROM test2;` | 4, 5, 6 ✓ |
| ВМ4 | `SELECT * FROM test2;` | 4, 5, 6 ✓ |


***

## Архитектура кластера

```
┌─────────────────────────────────────────────────────────────┐
│                    МИККЛАСТЕР PostgreSQL                     │
├──────────────┬──────────────┬──────────────┬───────────────┤
│   ВМ1        │   ВМ2        │   ВМ3        │   ВМ4         │
│  порт 5433   │  порт 5434   │  порт 5435   │  порт 5436    │
├──────────────┼──────────────┼──────────────┼───────────────┤
│ pub: test    │ pub: test2   │ sub: test    │ физ. реплика  │
│ sub: test2   │ sub: test    │ sub: test2   │ от ВМ3        │
│ ЗАПИСЬ: test │ ЗАПИСЬ: test2│ ЧТЕНИЕ: оба  │ ЧТЕНИЕ: оба   │
└──────────────┴──────────────┴──────────────┴───────────────┘

Логическая репликация (publication/subscription):
  ВМ1.test ──► ВМ2.test, ВМ3.test
  ВМ2.test2 ─► ВМ1.test2, ВМ3.test2

Физическая репликация (streaming replication):
  ВМ3 ──► ВМ4
```


***

## Использованные ключевые команды

| Задача | Команда |
| :-- | :-- |
| Проверка кластеров | `pg_lsclusters` |
| Создание таблицы | `CREATE TABLE name(id int);` |
| Создание публикации | `CREATE PUBLICATION pub_name FOR TABLE table_name;` |
| Настройка wal_level | `ALTER SYSTEM SET wal_level = 'logical';` |
| Перезапуск кластера | `pg_ctlcluster restart 15 ex14_vmX` |
| Создание подписки | `CREATE SUBSCRIPTION sub_name CONNECTION 'port=XXX' PUBLICATION pub_name;` |
| Физическая реплика | `pg_basebackup -D /path -W -R -p PORT -U postgres` |
| Проверка репликации | `SELECT * FROM pg_is_in_recovery();` |


***

## Выводы

✅ Настроен миникластер из 3 ВМ с двусторонней логической репликацией
✅ ВМ3 работает как объединённая точка чтения для таблиц `test` и `test2`
✅ ВМ4 успешно настроена как физическая реплика от ВМ3
✅ Все тесты вставки подтверждают работоспособность репликации на всех узлах
✅ Логическая репликация работает в обоих направлениях (ВМ1↔ВМ2)
✅ Физическая репликация ВМ3→ВМ4 синхронизирует все данные корректно

