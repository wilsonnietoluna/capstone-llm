import argparse
import logging
from pyspark.sql import SparkSession
from capstonellm.common.catalog import llm_bucket
from capstonellm.common.spark import ClosableSparkSession
import pyspark.sql.functions as ps


logger = logging.getLogger(__name__)

def clean(spark: SparkSession, environment: str, tag: str):

    ###Function cleans the data, joins answers and wuestions via the question id, for now keeps all the answers, maybe better to feed only accepted answer?
    ###Another question: Should I clean the httml code?->Would be nice, maybe if I have extra time, for now lets just move on.
    
    ###AWS path to find input and path to output cleaned version.
    
    questions_path = f"s3a://{llm_bucket}/input/wilsonnietoluna/{tag}/questions.json"
    answers_path = f"s3a://{llm_bucket}/input/wilsonnietoluna/{tag}/answers.json"
    output_path = f"s3a://{llm_bucket}/cleaned/wilsonnietoluna/{tag}"
    
    ##Cleaning of questions according to requested columns.
    raw_questions = spark.read.json(questions_path) 
    questions = (raw_questions.select(ps.explode("items").alias("item")).select("item.*").select("question_id", "title", ps.col("body").alias("question"), "link"))
    
    ##Cleaning of answers according to the columns of questions.
    raw_answers = spark.read.json(answers_path)       
    answers = (raw_answers.select(ps.explode("items").alias("item")).select("item.*").select("answer_id", "question_id", ps.col("body").alias("answer"), "is_accepted", "score"))
    
    ##Join of all answers per one question.
    answers_per_question = (answers.groupBy("question_id").agg(ps.collect_list("answer_id").alias("answer_id"), ps.collect_list("answer").alias("answer")))
    cleaned_data = questions.join(answers_per_question, on="question_id", how="inner")
    
    ##Output the data to AWS
    cleaned_data.write.mode("overwrite").option("maxRecordsPerFile", 1).json(output_path)
    



def main():
    parser = argparse.ArgumentParser(description="capstone_llm")
    parser.add_argument(
        "-e", "--env", dest="env", help="environment we are executing in", required=False, default="local"
    )
    parser.add_argument(
        "-t", "--tag", dest="tag", help="the tag to process",
        default="python-polars", required=False
    )
    logger.info("starting the cleaning job")

    args = parser.parse_args()
    common_spark_config = {
        "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
        "spark.hadoop.fs.s3a.aws.credentials.provider": "software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider",
    }
    if args.env == "local":
        print("This is a local execution of the capestonellm project")
        builder = SparkSession.builder.appName("Spark S3 Integration").config(
            "spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.4.2"
        )
        for key, value in common_spark_config.items():
            builder = builder.config(key, value)
        session = builder.getOrCreate()
        clean(session, args.env, args.tag)
    else:
        with ClosableSparkSession("capstone_llm", spark_config=common_spark_config) as session:
            clean(session, args.env, args.tag)


if __name__ == "__main__":
    main()
