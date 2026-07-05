CREATE OR REPLACE FUNCTION compute_vector_results_(
    run_description TEXT DEFAULT 'Vector search (pgvector)',
    max_results_per_query INTEGER DEFAULT NULL,
    query_limit INTEGER DEFAULT NULL
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_run_id INTEGER;
    qrec     record;
    qid	     INTEGER;
BEGIN
    -- 1. Создаём запись эксперимента (run)
    INSERT INTO run (description) VALUES (run_description)
    RETURNING id INTO v_run_id;

    for qid in (select id from query order by id limit query_limit)
    LOOP
	select into qrec * from query
        where id = qid;
	raise notice 'processing query %', qid;
        INSERT INTO result (query_id, news_id, run_id, rank)
        SELECT query_id, news_id, v_run_id, rn
	FROM (
	SELECT
            qrec.id       AS query_id,
            n.id          AS news_id,
            ROW_NUMBER() OVER (
                PARTITION BY qrec.id
                ORDER BY qrec.embedding <=> n.embedding ASC
            ) AS rn
        FROM news n
        WHERE qrec.embedding IS NOT NULL
          AND n.embedding IS NOT NULL
        ) ranked
	WHERE (max_results_per_query IS NULL OR rn <= max_results_per_query)
	ON CONFLICT (query_id, news_id, run_id) DO NOTHING;
    END LOOP;

    RETURN v_run_id;
END;
$$;


--select * from compute_vector_results_('vv 3 1000', 3, 1000);
