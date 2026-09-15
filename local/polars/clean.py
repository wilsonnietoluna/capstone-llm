import argparse
import logging
import os
import polars as pl
from pathlib import Path


logger = logging.getLogger(__name__)

def clean(tag: str):

        ###Function cleans the data, joins answers and wuestions via the question id, for now keeps all the answers, maybe better to feed only accepted answer?
    ###Another question: Should I clean the httml code?->Would be nice, maybe if I have extra time, for now lets just move on.
    
    ###Local path to find input and path to output cleaned version.
    
    questions_path = f"local/data/raw/{tag}/questions.json"
    answers_path = f"local/data/raw/{tag}/answers.json"
    output_path = f"local/data/cleaned/polars/{tag}"
    
    ##Cleaning of questions according to requested columns.
    raw_questions = pl.read_json(questions_path) 
    questions = (
        raw_questions
        .explode("items")
        .unnest("items")
        .select(
            "question_id", 
            "title", 
            pl.col("body").alias("question"), 
            "link",
        )
    )
    
    ##Cleaning of answers according to the columns of questions.
    raw_answers = pl.read_json(answers_path)       
    answers = (
        raw_answers
        .explode("items")
        .unnest("items")
        .select(
            "answer_id", 
            "question_id", 
            pl.col("body").alias("answer"), 
            "is_accepted", 
            "score",
        )
    )
    
    ##Join of all answers per one question.
    answers_per_question = (
        answers
        .group_by("question_id")
        .agg(
             pl.struct(
                    "answer_id", 
                    "answer", 
                    "is_accepted", 
                    "score",
            ).alias("answers")
        )
    )
    cleaned_data = questions.join(answers_per_question, on="question_id", how="inner")
    
    print("Questions:", questions.height)
    print("Answers:", answers.height)
    print("Cleaned questions:", cleaned_data.height)

    ##Output cleaned data to local path.
    output_dir = Path(f"local/data/cleaned/polars/{tag}")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "cleaned.ndjson"

    cleaned_data.write_ndjson(output_path)

    



def main():
    parser = argparse.ArgumentParser(description="local Polars cleaning")
    
    parser.add_argument(
        "-t", "--tag", dest="tag", help="the tag to process",
        default="python-polars", required=False
    )
    args = parser.parse_args()
    
    logger.info("starting the local Polars cleaning job")

    
    
    clean(args.tag)


if __name__ == "__main__":
    main()
