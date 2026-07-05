drop function fts_query(text);
CREATE OR REPLACE FUNCTION fts_query(
    query 	text
)
RETURNS TABLE(news_id integer, rank integer) AS $$
DECLARE 
    _word	text;
    counter 	INTEGER;
    freq_arr	INTEGER[];
    part_arr	INTEGER[];

BEGIN
	for _word in (select regexp_split_to_table(_text, '\s+'))
	loop
	    select into part_arr array_agg(id) from news where fts_article @@ plainto_tsquery('russian', _word);
	    if cardinality(part_arr) != 0 then 
		freq_arr = freq_arr || part_arr;
		counter = counter + 1;
	    end if;
	end loop;
	return query
	select id, counter - count(id)::int4 as cnt 
	    from unnest(freq_arr) as id 
	    group by id 
	    order by cnt;
END;
$$ LANGUAGE plpgsql;




drop function fts_rank(text, integer, integer);
CREATE OR REPLACE FUNCTION fts_rank(
    run_description TEXT DEFAULT 'fts or search',
    max_results_per_query INTEGER DEFAULT NULL,
    query_limit INTEGER DEFAULT NULL
)
RETURNS int AS $$
DECLARE 
    _id 	INTEGER;
    _text 	text;
    _word	text;
    _count	INTEGER;
    v_run_id 	INTEGER;
    _max	INTEGER;
    freq_arr	INTEGER[];
    part_arr	INTEGER[];
    counter 	INTEGER;
BEGIN
    INSERT INTO run (description) VALUES (run_description)
    RETURNING id INTO v_run_id;

    for _id, _text in(select id, query_text from query order by id fetch first (query_limit) rows only)
    loop
	for _word in (select regexp_split_to_table(_text, '\s+'))
	loop
	    select into part_arr array_agg(id) from news where fts_article @@ plainto_tsquery('russian', _word);
	    if cardinality(part_arr) != 0 then 
		freq_arr = freq_arr || part_arr;
		counter = counter + 1;
	    end if;
	end loop;
	
	INSERT INTO result (query_id, news_id, run_id, rank)
	select _id, id, v_run_id, counter - count(id)::int4 as cnt 
	    from unnest(freq_arr) as id 
	    group by id 
	    fetch first (max_results_per_query) rows only;
	freq_arr = '{}'::integer[];
	counter = 0;
    end loop;
    return v_run_id;
END;
$$ LANGUAGE plpgsql;

--\timing
--select * from fts_rank('fts', 1, 1);