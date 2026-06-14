CREATE OR REPLACE FUNCTION compute_fulltext_results(
    run_description TEXT DEFAULT 'Fulltext search',
    max_results_per_query INTEGER DEFAULT NULL
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_run_id INTEGER;
BEGIN
    -- 1. Создаём запись эксперимента (run)
    INSERT INTO run (description) VALUES (run_description)
    RETURNING id INTO v_run_id;

    -- 2. Одним запросом вычисляем и вставляем результаты для всех запросов
    INSERT INTO result (query_id, news_id, run_id, rank)
    SELECT query_id, news_id, v_run_id, rn
    FROM (
        SELECT
            q.id          AS query_id,
            n.id          AS news_id,
            ROW_NUMBER() OVER (
                PARTITION BY q.id
                ORDER BY ts_rank(n.fts_article, plainto_tsquery('russian', q.query_text)) DESC
            ) AS rn
        FROM query q
        CROSS JOIN news n
        WHERE q.query_text IS NOT NULL
          AND q.query_text <> ''
          AND n.fts_article @@ plainto_tsquery('russian', q.query_text)
    ) ranked
    WHERE (max_results_per_query IS NULL OR rn <= max_results_per_query)
    ON CONFLICT (query_id, news_id, run_id) DO NOTHING;

    RETURN v_run_id;
END;
$$;

SELECT compute_fulltext_results('fulltext search', 500);