CREATE OR REPLACE FUNCTION do_query(
	query	text
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_run_id 		INTEGER;
    qrec     		record;
    qid	     		INTEGER;
    rrf_k    		INTEGER;
    semantic_weight 	REAL;
BEGIN
    rrf_k = 60;
    semantic_weight=1 - full_text_weight;

    with
    full_text as (
	select news_id,  rank from 
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
        limit 5;
    END LOOP;

    RETURN v_run_id;
END;
$$;

