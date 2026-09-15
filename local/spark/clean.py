import argparse
import logging
from pyspark.sql import SparkSession
import pyspark.sql.functions as ps


logger = logging.getLogger(__name__)

def clean(tag: str):

    ##Start local Spark session. 

    spark = (SparkSession.builder.appName("capstone-llm-local").getOrCreate())

    ###Function cleans the data, joins answers and wuestions via the question id, for now keeps all the answers, maybe better to feed only accepted answer?
    ###Another question: Should I clean the httml code?->Would be nice, maybe if I have extra time, for now lets just move on.
    
    ###Local path to find input and path to output cleaned version.
    
    questions_path = f"local/data/raw/{tag}/questions.json"
    answers_path = f"local/data/raw/{tag}/answers.json"
    output_path = f"local/data/cleaned/spark/{tag}"
    
    ##Cleaning of questions according to requested columns.
    raw_questions = spark.read.json(questions_path) 
    questions = (
        raw_questions
        .select(
            ps.explode("items").alias("item")
        )
        .select("item.*")
        .select(
            "question_id", 
            "title", 
            ps.col("body").alias("question"), 
            "link",
        )
    )
    
    ##Cleaning of answers according to the columns of questions.
    raw_answers = spark.read.json(answers_path)       
    answers = (
        raw_answers
        .select(
            ps.explode("items").alias("item")
        )
        .select("item.*")
        .select(
            "answer_id", 
            "question_id", 
            ps.col("body").alias("answer"), 
            "is_accepted", 
            "score",
        )
    )
    
    ##Join of all answers per one question.
    answers_per_question = (
        answers
        .groupBy("question_id")
        .agg(
            ps.collect_list(
                ps.struct(
                    "answer_id", 
                    "answer", 
                    "is_accepted", 
                    "score"
                )
            ).alias("answers")
        )
    )
    cleaned_data = questions.join(answers_per_question, on="question_id", how="inner")
    
    print("Questions:", questions.count())
    print("Answers:", answers.count())
    print("Cleaned questions:", cleaned_data.count())

    ##Output the data locally in json format, one record per file, to avoid memory issues when reading the data in the next steps.
    cleaned_data.write.mode("overwrite").option("maxRecordsPerFile", 1).json(output_path)

    spark.stop()
    



def main():
    parser = argparse.ArgumentParser(description="local Spark cleaning")
    
    parser.add_argument(
        "-t", "--tag", dest="tag", help="the tag to process",
        default="python-polars", required=False
    )
    logger.info("starting the local Spark cleaning job")

    args = parser.parse_args()
    
    clean(args.tag)


if __name__ == "__main__":
    main()
