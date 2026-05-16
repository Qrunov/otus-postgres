# Отчёт по домашнему заданию: перенос данных PostgreSQL на отдельный диск

## Исходные условия

| Параметр | Значение |
|----------|----------|
| ОС | Astra 1.7 |
| СУБД | PostgreSQL 11 (пакет из репозитория, `apt`) |
| Кластер | `main`, порт 5432 |
| Каталог данных (до переноса) | `/var/lib/postgresql/11/main` |
| Новый диск | 10 GB, смонтирован в `/mnt/data` |

---

## 1. Установка и проверка кластера

PostgreSQL установлен через `sudo apt`. Состояние кластера:

```text
sudo -u postgres pg_lsclusters

Ver Cluster Port Status Owner    Data directory              Log file
11  main    5432 online postgres /var/lib/postgresql/11/main pg_log/postgresql-%a.log
```

Кластер **online**, данные в стандартном каталоге Astra.

---

## 2. Тестовая таблица в psql

Под пользователем `postgres`:

```sql
CREATE TABLE test(c1 text);
INSERT INTO test VALUES('1');
```

Проверка: одна строка с `c1 = '1'`.

---

## 3. Остановка PostgreSQL

```bash
sudo systemctl stop postgresql@11-main
```

После остановки:

```text
11  main    5432 down   postgres /var/lib/postgresql/11/main ...
```

Кластер **down** — можно безопасно переносить файлы данных.

---

## 4. Подготовка нового диска

1. Создан диск 10 GB и подключён к ВМ (attach existing disk).
2. Разметка и файловая система по [инструкции DigitalOcean](https://www.digitalocean.com/community/tutorials/how-to-partition-and-format-storage-devices-in-linux) (устройство в данном случае — `/dev/sdb`).
3. Точка монтирования: `/mnt/data`.
4. Запись в `/etc/fstab` для автомонтирования после перезагрузки.
5. Владелец каталога данных:

```bash
sudo chown -R postgres:postgres /mnt/data/
```

Проверка:

```text
stat /mnt/data
  Доступ: (0755/drwxr-xr-x)  Uid: (120/postgres)  Gid: (133/postgres)
```

---

## 5. Перенос каталога данных

```bash
sudo mv /var/lib/postgresql/11 /mnt/data/
```

Структура после переноса:

```text
/mnt/data/
└── 11/
    └── main/   # PGDATA
```

Исходный путь `/var/lib/postgresql/11/main` **больше не существует**.

---

## 6. Первая попытка запуска (без изменения конфигурации)

```bash
sudo -u postgres pg_ctlcluster 11 main start
```

**Результат: не получилось.**

**Почему:** `pg_ctlcluster` и служебные скрипты Debian по-прежнему ожидают данные в `/var/lib/postgresql/11/main`. После `mv` этого каталога нет:

```text
Error: /var/lib/postgresql/11/main is not accessible or does not exist
```

Конфигурация кластера в `/etc/postgresql/11/main/` всё ещё указывает на старый `data_directory` (по умолчанию — путь под `/var/lib/postgresql/...`).

---

## 7. Изменение конфигурационного параметра

**Файл:** `/etc/postgresql/11/main/postgresql.conf`

**Параметр:** `data_directory`

**Было (по сути):** `/var/lib/postgresql/11/main`  
**Стало:** `/mnt/data/11/main`

**Почему:** PostgreSQL при старте читает каталог PGDATA из `data_directory`. После переноса файлов на `/mnt/data` сервер должен знать новый абсолютный путь к каталогу с `global/`, `base/`, `pg_wal/` и т.д. Без этого он ищет данные на старом месте и не находит их.

Дополнительно для устойчивой работы на отдельном диске имеет смысл убедиться, что в `fstab` смонтирован `/mnt/data` **до** старта PostgreSQL (зависимости systemd или `RequiresMountsFor`).

---

## 8. Вторая попытка запуска (после смены `data_directory`)

```bash
sudo -u postgres pg_ctlcluster 11 main start
sudo -u postgres pg_lsclusters
```

**Результат: получилось.**

```text
Ver Cluster Port Status Owner    Data directory    Log file
11  main    5432 online postgres /mnt/data/11/main pg_log/postgresql-%a.log
```

Кластер **online**, `pg_lsclusters` показывает новый каталог данных.

---

## 9. Проверка данных в psql

```bash
psql -U postgres
```

```sql
SELECT * FROM test;
```

```text
 c1
----
 1
(1 строка)
```

Таблица `test` и данные **сохранились** — перенос затронул только расположение файлов на диске, не логическое содержимое БД.

---

## 10. Задание со звёздочкой (*)

**Цель:** вторая ВМ с установленным PostgreSQL, данные на внешнем диске с первой ВМ, без удаления первой машины.

**Что сделано:**

1. Создана вторая ВМ, установлен PostgreSQL.
2. На второй машине очищены/не используются локальные данные в стандартном каталоге (подготовка под чужой PGDATA).
3. Внешний диск с первой ВМ подключён ко второй (тот же физический/виртуальный диск с уже размеченной ФС и каталогом `11/main`).
4. В `/etc/fstab` второй ВМ добавлено монтирование, например:

   ```fstab
   /dev/sdb  /var/lib/postgres  ext4  defaults  0  2
   ```

   (точный UUID/LABEL и тип ФС — по факту разметки на первой ВМ.)

5. После монтирования на второй машине путь к данным совпадает с ожидаемым в `postgresql.conf` первой ВМ **или** на второй ВМ в `postgresql.conf` выставлен тот же `data_directory`, что и на диске (например `/mnt/data/11/main` или путь через `/var/lib/postgres`, если туда смонтирован корень данных).

6. Запуск: `sudo -u postgres pg_ctlcluster 11 main start` (версия PG на второй ВМ должна быть **совместима** с major-версией данных на диске — для каталога `11` нужен PostgreSQL 11).

**Ожидаемый итог:** на второй ВМ PostgreSQL поднимается с тем же PGDATA, что был на первой; `SELECT * FROM test` снова возвращает строку `1`. Первая ВМ при этом может оставаться выключенной или с отключённым диском, чтобы не было одновременной записи в один PGDATA с двух хостов.

**Важно:** один PGDATA нельзя одновременно использовать двумя запущенными инстансами — риск повреждения данных.

---
