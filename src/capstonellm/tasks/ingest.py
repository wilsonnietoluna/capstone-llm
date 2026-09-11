import argparse
from typing import List
import logging
import json
import requests
import boto3
from capstonellm.common.catalog import llm_bucket
import time
logger = logging.getLogger(__name__)

def ingest(tag: str):
    ##Take all questions from stackoverflow using a while so it stops when there are no more pages. 

    all_questions = []

    page = 1
    has_more = True

    while has_more:

        questions_url = "https://api.stackexchange.com/2.3/questions"
        questions_params = {"site": "stackoverflow", "tagged": tag, "pagesize": 100, "page": page, "filter": "withbody"}

        response = requests.get(questions_url, params=questions_params)
        if response.status_code != 200:
            print("Stack Exchange API error:")
            print(response.text)
        response.raise_for_status()
        questions_page = response.json()

        for question in questions_page["items"]:
            all_questions.append(question)

        if "backoff" in questions_page:
            time.sleep(questions_page["backoff"])
        
        has_more = questions_page["has_more"]
        page += 1


    print("Total questions:", len(all_questions))


    ## Get questions ids for answers.

    question_ids = []

    for question in all_questions:
        question_ids.append(question["question_id"])


    ## Get answers with same logic as the questions.

    all_answers = []

    # API accepts maximum 100 question IDs at a time
    for start in range(0, len(question_ids), 100):

        id_batch = question_ids[start:start + 100]
        ids_list = []

        for qid in id_batch:
            ids_list.append(str(qid))

        ids = ";".join(ids_list)


        page = 1
        has_more = True

        while has_more:

            answers_url = (f"https://api.stackexchange.com/2.3/questions/{ids}/answers")

            answers_params = {"site": "stackoverflow", "pagesize": 100, "page": page, "filter": "withbody"}

            response = requests.get(answers_url, params=answers_params)
            if response.status_code != 200:
                print("Stack Exchange API error:")
                print(response.text)
            
            response.raise_for_status()

            answers_page = response.json()

            for answer in answers_page["items"]:
                all_answers.append(answer)

            if "backoff" in answers_page:
                time.sleep(answers_page["backoff"])
            
            has_more = answers_page["has_more"]
            page += 1


    print("Total answers:", len(all_answers))


    ## Put data back to the same format for clean code. 

    questions = {"items": all_questions}

    answers = {"items": all_answers}


    ## Upload data to AWS

    s3 = boto3.client("s3")

    questions_key = (f"input/wilsonnietoluna/{tag}/questions.json")

    answers_key = (f"input/wilsonnietoluna/{tag}/answers.json")

    s3.put_object(Bucket=llm_bucket, Key=questions_key, Body=json.dumps(questions), ContentType="application/json")

    s3.put_object(Bucket=llm_bucket, Key=answers_key, Body=json.dumps(answers), ContentType="application/json")


def main():
    parser = argparse.ArgumentParser(description="stackoverflow ingest")
    parser.add_argument(
        "-t", "--tag", dest="tag", help="Tag of the question in stackoverflow to process",
        default="python-polars", required=False
    )
    args = parser.parse_args()
    logger.info("Starting the ingest job")

    ingest(args.tag)


if __name__ == "__main__":
    main()
