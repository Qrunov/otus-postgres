#!/usr/bin/env python3
"""
Скрипт для загрузки qrels из kaengreg/wikifacts-window_5-qrels
и добавления связей в таблицу result под заданным run_id
"""

import csv
import psycopg2
import argparse
from datasets import load_dataset

# === КОНФИГУРАЦИЯ ===
DB_CONFIG = {
    "port": 5433,
    "database": "postgres",
    "user": "postgres",
}

QRELS_DATASET_NAME = "kaengreg/wikifacts-window_5-qrels"
MAPPING_CSV = "id_mapping.csv"

QUERY_TABLE = "query"
NEWS_TABLE = "news"
RESULT_TABLE = "result"


def load_mapping_csv(csv_path):
    """Загрузить маппинг из CSV: dataset_id -> db_id для query и news"""
    query_map = {}
    news_map = {}
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            table = row["table"]
            db_id = int(row["db_id"])
            dataset_id = row["dataset_id"]
            
            if table == "query":
                query_map[dataset_id] = db_id
            elif table == "news":
                news_map[dataset_id] = db_id
    
    return query_map, news_map


def load_qrels_dataset(dataset_name):
    """Загрузить датасет qrels"""
    print(f"Загрузка датасета qrels {dataset_name}...")
    qrels_ds = load_dataset(dataset_name)
    
    # Получить данные (поддержать разные версии датасетов)
    if "train" in qrels_ds:
        qrels_data = qrels_ds["train"]
    else:
        qrels_data = list(qrels_ds.values())[0]
    
    print(f"qrels rows: {len(qrels_data)}")
    print(f"qrels columns: {qrels_data.column_names}")
    
    return qrels_data


def main(run_id):
    # 1. Загрузить маппинг
    print(f"Загрузка маппинга из {MAPPING_CSV}...")
    query_map, news_map = load_mapping_csv(MAPPING_CSV)
    print(f"query_map size: {len(query_map)}")
    print(f"news_map size: {len(news_map)}")
    
    # 2. Загрузить qrels
    qrels_data = load_qrels_dataset(QRELS_DATASET_NAME)
    
    # 3. Подключение к PostgreSQL
    print(f"Подключение к PostgreSQL: {DB_CONFIG['database']}...")
    conn = psycopg2.connect(**DB_CONFIG)
    
    inserted_count = 0
    skipped_query = 0
    skipped_news = 0
    
    try:
        with conn.cursor() as cur:
            # 4. Для каждой строки qrels найти db_id и добавить в result
            for i in range(len(qrels_data)):
                query_id_hf = str(qrels_data["query-id"][i])
                corpus_id_hf = str(qrels_data["corpus-id"][i])
                score = qrels_data["score"][i]
                
                # Найти query_id в БД
                if query_id_hf not in query_map:
                    skipped_query += 1
                    continue
                query_id_db = query_map[query_id_hf]
                
                # Найти news_id в БД
                if corpus_id_hf not in news_map:
                    skipped_news += 1
                    continue
                news_id_db = news_map[corpus_id_hf]
                
                # Определить rank (используем score как rank)
                rank = score
                
                # Проверить, есть ли уже запись
                cur.execute(
                    """
                    SELECT 1
                    FROM result
                    WHERE query_id = %s AND news_id = %s AND run_id = %s
                    """,
                    (query_id_db, news_id_db, run_id)
                )
                
                if cur.fetchone() is None:
                    # Добавить запись
                    cur.execute(
                        """
                        INSERT INTO result (query_id, news_id, run_id, rank)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (query_id_db, news_id_db, run_id, rank)
                    )
                    inserted_count += 1
            
            conn.commit()
        
        print(f"✅ Добавлено записей: {inserted_count}")
        print(f"⚠️ Пропущено (нет query_id): {skipped_query}")
        print(f"⚠️ Пропущено (нет news_id): {skipped_news}")
        
        # 5. Проверка результата
        print("\n=== Проверка результата ===")
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT query_id, news_id, run_id, rank
                FROM result
                WHERE run_id = %s
                ORDER BY query_id, rank
                LIMIT 10
                """,
                (run_id,)
            )
            
            print(f"Первые 10 записей result для run_id={run_id}:")
            for row in cur.fetchall():
                print(f"  query_id={row[0]}, news_id={row[1]}, run_id={row[2]}, rank={row[3]}")
        
    except Exception:
        print("❌ Ошибка, откат изменений...")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Загрузить qrels и добавить в result под заданным run_id"
    )
    parser.add_argument(
        "run_id",
        type=int,
        help="run_id для записи в таблицу result"
    )
    
    args = parser.parse_args()
    main(args.run_id)