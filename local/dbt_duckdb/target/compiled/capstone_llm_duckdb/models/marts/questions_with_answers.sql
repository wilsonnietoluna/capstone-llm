select
    q.question_id,
    q.title,
    q.question,
    q.link,
    a.answers

from "capstone"."main"."stg_questions" as q

inner join "capstone"."main"."int_answers_per_question" as a
    on q.question_id = a.question_id