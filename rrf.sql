CREATE OR REPLACE FUNCTION compute_rrf_results(
    run_description TEXT DEFAULT 'rrf',
    max_results_per_query INTEGER DEFAULT NULL,
    query_limit INTEGER DEFAULT NULL
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_run_id 		INTEGER;
    qrec     		record;
    qid	     		INTEGER;
    rrf_k    		INTEGER;
    full_text_weight	REAL;
    semantic_weight 	REAL;
BEGIN
    rrf_k = 60;
    full_text_weight= 0.1;
    semantic_weight=1 - full_text_weight;

    -- 1. Создаём запись эксперимента (run)
    INSERT INTO run (description) VALUES (run_description)
    RETURNING id INTO v_run_id;

    if (query_limit is null) then
	select into query_limit count(*) from query;
    end if;

    for qid in (select id from query order by id limit query_limit)
    LOOP
	select into qrec * from query
        where id = qid;
	raise notice 'processing query %', qid;
        INSERT INTO result (query_id, news_id, run_id, rank)
    with
    full_text as (
        select
	    news.id,
	    row_number() over(order by ts_rank_cd(fts_article, plainto_tsquery(qrec.query_text)) desc) as rank_ix
	from
	    news
	where
	    fts_article @@ plainto_tsquery(qrec.query_text)
	order by rank_ix
        limit max_results_per_query
    ),
    semantic as (
	select
	    news.id,
    	    row_number() over (order by embedding <=> qrec.embedding) as rank_ix
	from
    	    news
	order by rank_ix
	limit max_results_per_query
    )
    select
	qrec.id,
        news.id,
	v_run_id,
        coalesce(1.0 / (rrf_k + full_text.rank_ix), 0.0) * full_text_weight +
        coalesce(1.0 / (rrf_k + semantic.rank_ix), 0.0) * semantic_weight
    from
	full_text
        full outer join semantic
	    on full_text.id = semantic.id
	join news
	    on coalesce(full_text.id, semantic.id) = news.id
    order by
	coalesce(1.0 / (rrf_k + full_text.rank_ix), 0.0) * full_text_weight +
        coalesce(1.0 / (rrf_k + semantic.rank_ix), 0.0) * semantic_weight
	desc
        limit max_results_per_query;
    END LOOP;

    RETURN v_run_id;
END;
$$;

