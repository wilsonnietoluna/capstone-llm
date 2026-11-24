import argparse
import json
from pathlib import Path

import polars as pl
from bs4 import BeautifulSoup


def clean_html(text: str) -> str:
    soup = BeautifulSoup(
        text,
        "html.parser",
    )

    return soup.get_text(
        separator="\n",
        strip=True,
    )


def prepare_documents(tag: str):
    input_path = Path(
        f"local/data/cleaned/polars/{tag}/cleaned.ndjson"
    )

    output_dir = Path(
        f"local/data/rag/{tag}"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_dir / "documents.json"

    # ------------------------------------------
    # Load cleaned Q&A data
    # ------------------------------------------

    data = pl.read_ndjson(input_path)

    documents = []

    # ------------------------------------------
    # Create one RAG document per QUESTION
    # ------------------------------------------

    for row in data.iter_rows(named=True):

        question_id = row["question_id"]
        title = row["title"]
        link = row["link"]

        clean_question = clean_html(
            row["question"]
        )

        # This is the text that will be embedded.
        # Answers are deliberately NOT included.
        text = (
            f"Title: {title}\n\n"
            f"Question:\n{clean_question}"
        )

        answers = []

        for answer in row["answers"]:

            clean_answer = clean_html(
                answer["answer"]
            )

            answer_data = {
                "answer_id": answer["answer_id"],
                "answer": clean_answer,
                "is_accepted": answer["is_accepted"],
                "score": answer["score"],
            }

            answers.append(answer_data)

        document = {
            "text": text,
            "question_id": question_id,
            "title": title,
            "question": clean_question,
            "link": link,
            "answers": answers,
        }

        documents.append(document)

    # ------------------------------------------
    # Save documents
    # ------------------------------------------

    with open(
        output_path,
        "w",
    ) as file:

        json.dump(
            documents,
            file,
            indent=2,
        )

    print(f"Questions: {len(documents)}")
    print(f"Saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Prepare Stack Overflow documents for RAG"
    )

    parser.add_argument(
        "-t",
        "--tag",
        required=True,
        help="Stack Overflow tag",
    )

    args = parser.parse_args()

    prepare_documents(args.tag)


if __name__ == "__main__":
    main()