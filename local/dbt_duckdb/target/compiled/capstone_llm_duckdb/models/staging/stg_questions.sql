with raw_questions as (
    select *
    from read_json_auto('local/data/raw/dbt/questions.json')
)

select
    question.question_id,
    question.title,
    question.body as question,
    question.link

from raw_questions,
unnest(items) as t(question)