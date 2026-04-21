# Домашнее задание: Установка и настройка PostgteSQL в контейнере Docker

## Цель

установить PostgreSQL в Docker контейнере;
настроить контейнер для внешнего подключения;

## Условия выполнения

- ОС: Ubuntu `22.04` или `24.04` (или любой хост с установленным Docker Engine)
- PostgreSQL: образ `postgres:18`
- Docker network: `pg-net`
- Каталог для данных на хосте: `/var/lib/postgres`

## 1) Подготовка окружения

Создаем каталог для хранения данных PostgreSQL на хосте:

```bash
mkdir /var/lib/postgres
```

Создаем отдельную Docker-сеть:

```bash
docker network create pg-net
```

Пример результата:

```text
60895251ed6c815538d745a0222487d1156619123a5bf5a336fa9b8184ade314
```

## 2) Запуск контейнера PostgreSQL

Запускаем контейнер с сервером и монтируем хостовый каталог:

```bash
docker run -d --name postgres18 --network pg-net -e POSTGRES_PASSWORD=123 -p 5432:5432 -v /var/lib/postgres:/var/lib/postgresql/18/docker postgres:18
```

Пример результата:

```text
064b07b8df8efe6510ad511e52885a8665c537ea7c898eda5957054ea2ebf27e
```

## 3) Запуск контейнера-клиента и создание тестовых данных

Запускаем `psql` из отдельного контейнера и подключаемся к серверу:

```bash
docker run -it --rm --name pg-client --network pg-net postgres:18 psql -h postgres18 -U postgres
```

Внутри `psql` выполняем:

```sql
create table test(id int4);
insert into test values(1);
insert into test values(2);
insert into test values(3);
```

Пример вывода:

```text
Password for user postgres:
psql (18.3 (Debian 18.3-1.pgdg13+1))
Type "help" for help.

postgres=# create table test(id int4);
CREATE TABLE
postgres=# insert into test values(1);
INSERT 0 1
postgres=# insert into test values(2);
INSERT 0 1
postgres=# insert into test values(3);
INSERT 0 1
```

## 4) Подключение к серверу с хоста (снаружи контейнера)

Проверяем подключение с ноутбука/компьютера (или хоста, где установлен Docker):

```bash
psql -h localhost -U postgres
```

Пример вывода:

```text
Password for user postgres:
psql (17.9 (Ubuntu 17.9-0ubuntu0.25.10.1), server 18.3 (Debian 18.3-1.pgdg13+1))
WARNING: psql major version 17, server major version 18.
         Some psql features might not work.
Type "help" for help.

postgres=#
```

## 5) Удаление контейнера сервера

Останавливаем и удаляем контейнер:

```bash
docker stop postgres18
docker rm postgres18
```

Пример вывода:

```text
postgres18
postgres18
```

## 6) Повторный запуск контейнера сервера

Создаем контейнер снова с тем же монтированием:

```bash
docker run -d --name postgres18 --network pg-net -e POSTGRES_PASSWORD=123 -p 5432:5432 -v /var/lib/postgres:/var/lib/postgresql/18/docker postgres:18
```

Пример результата:

```text
1914b8336ca0eaf0cd9909e20c3d0047ab92bd2cfca9ff517d78e7118df88a48
```

## 7) Проверка сохранности данных

Подключаемся клиентом снова:

```bash
docker run -it --rm --name pg-client --network pg-net postgres:18 psql -h postgres18 -U postgres
```

Проверяем таблицу:

```sql
select * from test;
```

Ожидаемый результат:

```text
 id
----
  1
  2
  3
(3 rows)
```

## Вывод
Данные в PostgreSQL сохраняются между перезапусками/пересозданием контейнера, так как каталог базы данных вынесен в постоянный том на хосте (`/var/lib/postgres`).
