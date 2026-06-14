#!/usr/bin/env python3
"""
Скрипт для заполнения dataset_id в таблицах query и news
используя _id из датасета kaengreg/wikifacts-window_5 на Hugging Face

- Загружает отдельные конфигурации queries и corpus
- Берет реальные id из PostgreSQL (не стартуют с 1)
- Строит маппинг по порядку строк
- Обновляет dataset_id в обеих таблицах
- Сохраняет маппинг в CSV
"""

import csv
import psycopg2
from datasets import load_dataset

# === КОНФИГУРАЦИЯ ===
DB_CONFIG = {
    "port": 5433,
    "database": "postgres",
    "user": "postgres",
}

DATASET_NAME = "kaengreg/wikifacts-window_5"

QUERY_TABLE = "query"
NEWS_TABLE = "news"

# Порядок сортировки в БД (должен совпадать с порядком в HF датасете)
QUERY_ORDER_BY = "id"
NEWS_ORDER_BY = "id"

OUTPUT_CSV = "id_mapping.csv"


def fetch_ids(conn, table_name, order_by):
    """Получить все id из таблицы в указанном порядке"""
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT id
            FROM {table_name}
            ORDER BY {order_by}
        """)
        return [row[0] for row in cur.fetchall()]


def main():
    # 1. Загрузить датасеты из Hugging Face (отдельные конфигурации)
    print(f"Загрузка датасета {DATASET_NAME}...")
    queries_ds = load_dataset(DATASET_NAME, "queries")
    corpus_ds = load_dataset(DATASET_NAME, "corpus")
    
    # Получить данные (поддержать разные версии датасетов)
    if "train" in queries_ds:
        query_data = queries_ds["train"]
    else:
        query_data = list(queries_ds.values())[0]
    
    if "train" in corpus_ds:
        corpus_data = corpus_ds["train"]
    else:
        corpus_data = list(corpus_ds.values())[0]
    
    print(f"query rows: {len(query_data)}")
    print(f"corpus rows: {len(corpus_data)}")
    print(f"query columns: {query_data.column_names}")
    print(f"corpus columns: {corpus_data.column_names}")
    
    # 2. Проверить наличие _id
    if "_id" not in query_data.column_names:
        raise ValueError("В HF queries нет колонки _id")
    if "_id" not in corpus_data.column_names:
        raise ValueError("В HF corpus нет колонки _id")
    
    # 3. Подключение к PostgreSQL
    print(f"Подключение к PostgreSQL: {DB_CONFIG['database']}...")
    conn = psycopg2.connect(**DB_CONFIG)
    
    try:
        # 4. Получить реальные id из таблиц (не начинаются с 1)
        query_db_ids = fetch_ids(conn, QUERY_TABLE, QUERY_ORDER_BY)
        news_db_ids = fetch_ids(conn, NEWS_TABLE, NEWS_ORDER_BY)
        
        print(f"query db ids count: {len(query_db_ids)}")
        print(f"news db ids count: {len(news_db_ids)}")
        
        # 5. Проверить соответствие размеров
        if len(query_db_ids) != len(query_data):
            raise ValueError(
                f"query mismatch: db={len(query_db_ids)} hf={len(query_data)}"
            )
        
        if len(news_db_ids) != len(corpus_data):
            raise ValueError(
                f"news mismatch: db={len(news_db_ids)} hf={len(corpus_data)}"
            )
        
        # 6. Сопоставить БД id с HF _id по позиции
        query_map = []
        for i in range(len(query_data)):
            db_id = query_db_ids[i]
            dataset_id = str(query_data["_id"][i])
            query_map.append((db_id, dataset_id))
        
        news_map = []
        for i in range(len(corpus_data)):
            db_id = news_db_ids[i]
            dataset_id = str(corpus_data["_id"][i])
            news_map.append((db_id, dataset_id))
        
        # 7. Обновить dataset_id в обеих таблицах
        print("Обновление dataset_id в таблице query...")
        with conn.cursor() as cur:
            for db_id, dataset_id in query_map:
                cur.execute(
                    "UPDATE query SET dataset_id = %s WHERE id = %s",
                    (dataset_id, db_id),
                )
        
        print("Обновление dataset_id в таблице news...")
        with conn.cursor() as cur:
            for db_id, dataset_id in news_map:
                cur.execute(
                    "UPDATE news SET dataset_id = %s WHERE id = %s",
                    (dataset_id, db_id),
                )
        
        conn.commit()
        
        print(f"✅ Обновлено query: {len(query_map)} строк")
        print(f"✅ Обновлено news: {len(news_map)} строк")
        
        # 8. Сохранить маппинг в CSV
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["table", "db_id", "dataset_id"])
            for db_id, dataset_id in query_map:
                writer.writerow(["query", db_id, dataset_id])
            for db_id, dataset_id in news_map:
                writer.writerow(["news", db_id, dataset_id])
        
        print(f"📄 Маппинг сохранён в {OUTPUT_CSV}")
        
        # 9. Проверка результата
        print("\n=== Проверка результата ===")
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT id, dataset_id
                FROM {QUERY_TABLE}
                ORDER BY id
                LIMIT 5
            """)
            print("Первые 5 строк query после обновления:")
            for row in cur.fetchall():
                print(f"  query.id={row[0]}, dataset_id={row[1]}")
            
            cur.execute(f"""
                SELECT id, dataset_id
                FROM {NEWS_TABLE}
                ORDER BY id
                LIMIT 5
            """)
            print("Первые 5 строк news после обновления:")
            for row in cur.fetchall():
                print(f"  news.id={row[0]}, dataset_id={row[1]}")
        
    except Exception:
        print("❌ Ошибка, откат изменений...")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()