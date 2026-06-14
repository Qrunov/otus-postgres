import psycopg2
from datasets import load_dataset
from config import (
    DB_CONFIG,
    DATASET_NAME,
    DATASET_QRELS_NAME,
    CORPUS_SPLIT,
    QUERIES_SPLIT,
    QRELS_SPLIT,
    CACHE_DIR,
    RUN_DESCRIPTION,
    CLEAR_TABLES_BEFORE_LOAD,
    VERBOSE
)

def load_news(cur, dataset):
    """Загружает корпус в news. mapping: индекс (str) -> pg_id."""
    if VERBOSE:
        print("Загрузка документов (news)...")
    mapping = {}
    for idx, item in enumerate(dataset):
        article = item['text']
        cur.execute(
            "INSERT INTO news (dataset_id, article) VALUES (%s, %s) RETURNING id",
            (str(idx), article)
        )
        pg_id = cur.fetchone()[0]
        mapping[str(idx)] = pg_id
    if VERBOSE:
        print(f"✅ Загружено {len(mapping)} документов")
    return mapping

def load_queries(cur, dataset):
    """Загружает запросы в query. mapping: индекс (str) -> pg_id."""
    if VERBOSE:
        print("Загрузка запросов (query)...")
    mapping = {}
    for idx, item in enumerate(dataset):
        query_text = item['text']
        cur.execute(
            "INSERT INTO query (dataset_id, query_text) VALUES (%s, %s) RETURNING id",
            (str(idx), query_text)
        )
        pg_id = cur.fetchone()[0]
        mapping[str(idx)] = pg_id
    if VERBOSE:
        print(f"✅ Загружено {len(mapping)} запросов")
    return mapping

def insert_results_from_mapping(cur, run_id, qrels_dataset, news_mapping, query_mapping):
    """Вставка результатов. qrels: поля query-id, corpus-id, score."""
    if VERBOSE:
        print("Вставка результатов (result)...")
    count = 0
    for item in qrels_dataset:
        qid = str(item['query-id'])
        did = str(item['corpus-id'])
        score = item['score']

        pg_query_id = query_mapping.get(qid)
        pg_news_id = news_mapping.get(did)

        if pg_query_id is None or pg_news_id is None:
            if VERBOSE:
                print(f"⚠️ Пропущена запись: query={qid}, doc={did}")
            continue

        cur.execute("""
            INSERT INTO result (query_id, news_id, run_id, rank)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (query_id, news_id, run_id) 
            DO UPDATE SET rank = EXCLUDED.rank
        """, (pg_query_id, pg_news_id, run_id, score))
        count += 1

    if VERBOSE:
        print(f"✅ Вставлено/обновлено {count} записей в result")

def load_dataset_to_db():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    try:
        if CLEAR_TABLES_BEFORE_LOAD:
            if VERBOSE:
                print("Очистка таблиц...")
            cur.execute("DELETE FROM result")
            cur.execute("DELETE FROM query")
            cur.execute("DELETE FROM news")
            conn.commit()

        if VERBOSE:
            print(f"\nЗагрузка датасета {DATASET_NAME} (corpus, queries)...")
        # Загружаем без split -> получаем DatasetDict, затем берём нужный сплит
        corpus_dataset = load_dataset(DATASET_NAME, "corpus", cache_dir=CACHE_DIR)[CORPUS_SPLIT]
        queries_dataset = load_dataset(DATASET_NAME, "queries", cache_dir=CACHE_DIR)[QUERIES_SPLIT]

        if VERBOSE:
            print(f"Загрузка датасета qrels: {DATASET_QRELS_NAME} (split={QRELS_SPLIT})...")
        qrels_dataset = load_dataset(DATASET_QRELS_NAME, cache_dir=CACHE_DIR)[QRELS_SPLIT]

        if VERBOSE:
            print("✅ Датасеты загружены")

        news_mapping = load_news(cur, corpus_dataset)
        conn.commit()

        query_mapping = load_queries(cur, queries_dataset)
        conn.commit()

        if VERBOSE:
            print("\n Всё загружено успешно!")

    except Exception as e:
        conn.rollback()
        print(f"\n Ошибка: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    load_dataset_to_db()