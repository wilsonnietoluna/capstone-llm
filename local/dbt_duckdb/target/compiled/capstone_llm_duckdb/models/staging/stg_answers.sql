with raw_answers as (

    select *
    from read_json_auto('local/data/raw/dbt/answers.json')
)

select
    answer.answer_id,
    answer.question_id,
    answer.body as answer,
    answer.is_accepted,
    answer.score

from raw_answers,
unnest(items) as t(answer)