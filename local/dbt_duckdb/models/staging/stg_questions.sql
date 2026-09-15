with raw_questions as (
    select *
    from read_json_auto('{{var("raw_root")}}/{{var("tag")}}/questions.json')
)

select
    question.question_id,
    question.title,
    question.body as question,
    question.link

from raw_questions,
unnest(items) as t(question)