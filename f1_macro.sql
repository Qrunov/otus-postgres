CREATE OR REPLACE FUNCTION compare_f1_macro(
    baseline_run_id INTEGER,
    test_run_id INTEGER,
    query_limit	INTEGER DEFAULT NULL,
    rank_threshold INTEGER DEFAULT 0,
    top_k INTEGER DEFAULT 0
)
RETURNS TABLE(
    macro_precision NUMERIC,
    macro_recall NUMERIC,
    macro_f1 NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH 
    query_lim AS (
        SELECT
            id 
        FROM query
        ORDER BY id 
        LIMIT query_limit
    ),
    baseline AS (
        SELECT 
            r.query_id,
            r.news_id,
            r.rank,
            ROW_NUMBER() OVER (PARTITION BY r.query_id ORDER BY r.rank ASC) AS row_num
        FROM result r
        INNER JOIN query_lim ON query_lim.id = r.query_id
        WHERE r.run_id = baseline_run_id
          AND (rank_threshold = 0 OR r.rank <= rank_threshold)
    ),
    test AS (
        SELECT 
            r.query_id,
            r.news_id,
            r.rank,
            ROW_NUMBER() OVER (PARTITION BY r.query_id ORDER BY r.rank ASC) AS row_num
        FROM result r
        INNER JOIN query_lim ON query_lim.id = r.query_id
        WHERE r.run_id = test_run_id
          AND (rank_threshold = 0 OR r.rank <= rank_threshold)
    ),
    baseline_filtered AS (
        SELECT b.query_id, b.news_id
        FROM baseline b
        WHERE (top_k = 0 OR b.row_num <= top_k)
    ),
    test_filtered AS (
        SELECT t.query_id, t.news_id
        FROM test t
        WHERE (top_k = 0 OR t.row_num <= top_k)
    ),
    query_stats AS (
        SELECT 
            COALESCE(bf.query_id, tf.query_id) AS query_id,
            COUNT(DISTINCT bf.news_id)::INTEGER AS baseline_count,
            COUNT(DISTINCT tf.news_id)::INTEGER AS test_count,
            COUNT(DISTINCT CASE 
                WHEN tf.news_id IS NOT NULL AND bf.news_id IS NOT NULL 
                THEN tf.news_id 
            END)::INTEGER AS intersection_count
        FROM baseline_filtered bf
        FULL OUTER JOIN test_filtered tf 
            ON bf.query_id = tf.query_id AND bf.news_id = tf.news_id
        GROUP BY COALESCE(bf.query_id, tf.query_id)
    ),
    calculated_metrics AS (
        SELECT
            qs.query_id,
            qs.baseline_count,
            qs.test_count,
            qs.intersection_count,
            CASE WHEN qs.test_count > 0 
                 THEN qs.intersection_count::NUMERIC / qs.test_count 
                 ELSE 0 END AS precision_val,
            CASE WHEN qs.baseline_count > 0 
                 THEN qs.intersection_count::NUMERIC / qs.baseline_count 
                 ELSE 0 END AS recall_val,
            CASE 
                WHEN (CASE WHEN qs.test_count > 0 
                         THEN qs.intersection_count::NUMERIC / qs.test_count 
                         ELSE 0 END) 
                     + (CASE WHEN qs.baseline_count > 0 
                         THEN qs.intersection_count::NUMERIC / qs.baseline_count 
                         ELSE 0 END) > 0 
                THEN 2 * (CASE WHEN qs.test_count > 0 
                             THEN qs.intersection_count::NUMERIC / qs.test_count 
                             ELSE 0 END) 
                     * (CASE WHEN qs.baseline_count > 0 
                             THEN qs.intersection_count::NUMERIC / qs.baseline_count 
                             ELSE 0 END) 
                     / ((CASE WHEN qs.test_count > 0 
                             THEN qs.intersection_count::NUMERIC / qs.test_count 
                             ELSE 0 END) 
                        + (CASE WHEN qs.baseline_count > 0 
                             THEN qs.intersection_count::NUMERIC / qs.baseline_count 
                             ELSE 0 END))
                ELSE 0 
            END AS f1_val
        FROM query_stats qs
    )
    SELECT 
        AVG(precision_val)::NUMERIC AS macro_precision,
        AVG(recall_val)::NUMERIC AS macro_recall,
        AVG(f1_val)::NUMERIC AS macro_f1
    FROM calculated_metrics;
END;
$$ LANGUAGE plpgsql;