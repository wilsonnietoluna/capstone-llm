import argparse
import csv
import json
import time
from pathlib import Path

import requests

from generate import (
    build_context,
    generate_answer,
    retrieve,
)


STRATEGIES = [
    "accepted",
    "highest-score",
    "all",
]


FIELDNAMES = [
    "question",
    "strategy",
    "sources",
    "answers",
    "average_similarity",
    "context_characters",
    "generation_time_seconds",
    "context",
    "generated_answer",
]


def load_questions(tag: str, questions_path: Path):

    with open(questions_path, "r") as file:
        questions_by_tag = json.load(file)

    return questions_by_tag.get(tag, [])


def load_existing_results(output_path: Path):

    results = {}

    if not output_path.exists():
        return results

    with open(output_path, "r") as file:

        reader = csv.DictReader(file)

        for row in reader:

            key = (
                row["question"],
                row["strategy"],
            )

            results[key] = row

    return results


def result_is_complete(row):

    if row is None:
        return False

    # Results produced by the older evaluator did not
    # save the retrieved context. Re-run those once.
    if "context" not in row:
        return False

    if "context_characters" not in row:
        return False

    generated_answer = row.get(
        "generated_answer",
        "",
    )

    if not generated_answer:
        return False

    if generated_answer.startswith(
        "GENERATION TIMEOUT"
    ):
        return False

    if generated_answer.startswith(
        "GENERATION ERROR"
    ):
        return False

    return True


def save_results(results, output_path: Path):

    with open(
        output_path,
        "w",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES,
        )

        writer.writeheader()

        for row in results.values():

            clean_row = {}

            for field in FIELDNAMES:
                clean_row[field] = row.get(
                    field,
                    "",
                )

            writer.writerow(clean_row)


def evaluate(
    tag: str,
    top_k: int,
    model: str,
    questions_path: Path,
):

    output_dir = Path(
        "local/rag/evaluation"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir
        / f"{tag}_results.csv"
    )

    evaluation_questions = load_questions(
        tag,
        questions_path,
    )

    if len(evaluation_questions) == 0:

        print(
            f"No evaluation questions "
            f"configured for tag: {tag}"
        )

        return

    results = load_existing_results(
        output_path
    )

    print()
    print("=" * 70)
    print(f"Evaluating tag: {tag}")
    print(
        f"Questions: "
        f"{len(evaluation_questions)}"
    )
    print("=" * 70)

    for question_number, query in enumerate(
        evaluation_questions,
        start=1,
    ):

        print()
        print("=" * 70)
        print(
            f"Question "
            f"{question_number}/"
            f"{len(evaluation_questions)}"
        )
        print("=" * 70)
        print(query)

        for strategy in STRATEGIES:

            key = (
                query,
                strategy,
            )

            existing_result = results.get(
                key
            )

            if result_is_complete(
                existing_result
            ):

                print()
                print(
                    f"Strategy: {strategy}"
                )
                print(
                    "Already completed. "
                    "Skipping."
                )

                continue

            print()
            print(
                f"Strategy: {strategy}"
            )

            # ----------------------------------
            # Retrieval
            # ----------------------------------

            retrieved_documents = retrieve(
                tag,
                query,
                top_k,
                strategy,
            )

            source_count = len(
                retrieved_documents
            )

            answer_count = 0
            similarities = []

            for document in retrieved_documents:

                answer_count += len(
                    document["answers"]
                )

                similarities.append(
                    document["similarity"]
                )

            if similarities:

                average_similarity = (
                    sum(similarities)
                    / len(similarities)
                )

            else:

                average_similarity = 0.0

            # ----------------------------------
            # Context
            # ----------------------------------

            context = ""

            if source_count > 0:

                context = build_context(
                    retrieved_documents
                )

            context_characters = len(
                context
            )

            # ----------------------------------
            # Generation
            # ----------------------------------

            if source_count == 0:

                generated_answer = (
                    "No usable context was retrieved."
                )

                generation_time = 0.0

            else:

                start = time.perf_counter()

                try:

                    generated_answer = (
                        generate_answer(
                            query,
                            context,
                            model,
                        )
                    )

                except requests.exceptions.ReadTimeout:

                    generated_answer = (
                        "GENERATION TIMEOUT"
                    )

                except requests.exceptions.RequestException as error:

                    generated_answer = (
                        "GENERATION ERROR: "
                        f"{error}"
                    )

                end = time.perf_counter()

                generation_time = (
                    end - start
                )

            print(
                f"Sources: {source_count}"
            )

            print(
                f"Answers: {answer_count}"
            )

            print(
                "Average similarity: "
                f"{average_similarity:.4f}"
            )

            print(
                "Context characters: "
                f"{context_characters}"
            )

            print(
                "Generation time: "
                f"{generation_time:.2f} s"
            )

            result = {
                "question": query,
                "strategy": strategy,
                "sources": source_count,
                "answers": answer_count,
                "average_similarity": (
                    average_similarity
                ),
                "context_characters": (
                    context_characters
                ),
                "generation_time_seconds": (
                    generation_time
                ),
                "context": context,
                "generated_answer": (
                    generated_answer
                ),
            }

            results[key] = result

            # Save after EVERY generation.
            # If Ollama or the script fails,
            # completed runs are preserved.
            save_results(
                results,
                output_path,
            )

    print()
    print("=" * 70)
    print("Evaluation complete")
    print("=" * 70)

    print(
        f"Results saved to: "
        f"{output_path}"
    )


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Evaluate RAG answer-selection "
            "strategies"
        )
    )

    parser.add_argument(
        "-t",
        "--tag",
        required=True,
        help="Stack Overflow tag",
    )

    parser.add_argument(
        "-k",
        "--top-k",
        type=int,
        default=3,
        help="Number of questions to retrieve",
    )

    parser.add_argument(
        "-m",
        "--model",
        default="llama3.2:3b",
        help="Ollama model",
    )

    parser.add_argument(
        "--questions-file",
        default=(
            "local/rag/evaluation/"
            "questions.json"
        ),
        help=(
            "JSON file containing "
            "evaluation questions"
        ),
    )

    args = parser.parse_args()

    evaluate(
        args.tag,
        args.top_k,
        args.model,
        Path(args.questions_file),
    )


if __name__ == "__main__":
    main()