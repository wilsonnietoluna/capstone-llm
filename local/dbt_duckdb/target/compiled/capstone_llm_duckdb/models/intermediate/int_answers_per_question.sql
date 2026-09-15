select
    question_id,

    list(
        struct_pack(
            answer_id := answer_id,
            answer := answer,
            is_accepted := is_accepted,
            score := score
        )
        order by score desc
    ) as answers

from "capstone"."main"."stg_answers"

group by question_id