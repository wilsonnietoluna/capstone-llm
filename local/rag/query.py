import argparse
import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


def select_answers(answers, strategy):
    if strategy == "accepted":

        selected_answers = []

        for answer in answers:
            if answer["is_accepted"]:
                selected_answers.append(answer)

        return selected_answers

    if strategy == "highest-score":

        if len(answers) == 0:
            return []

        highest_score_answer = max(
            answers,
            key=lambda answer: answer["score"],
        )

        return [highest_score_answer]

    if strategy == "all":
        return answers

    raise ValueError(
        f"Unknown strategy: {strategy}"
    )


def search(
    tag: str,
    query: str,
    top_k: int,
    strategy: str,
):
    data_dir = Path(
        f"local/data/rag/{tag}"
    )

    documents_path = data_dir / "documents.json"
    index_path = data_dir / "index.faiss"

    # ------------------------------------------
    # Load documents
    # ------------------------------------------

    with open(documents_path, "r") as file:
        documents = json.load(file)

    # ------------------------------------------
    # Load FAISS index
    # ------------------------------------------

    index = faiss.read_index(
        str(index_path)
    )

    # ------------------------------------------
    # Load embedding model
    # ------------------------------------------

    model_name = "sentence-transformers/all-MiniLM-L6-v2"

    model = SentenceTransformer(
        model_name
    )

    # ------------------------------------------
    # Embed query
    # ------------------------------------------

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
    )

    query_embedding = np.asarray(
        query_embedding,
        dtype="float32",
    )

    # ------------------------------------------
    # Search FAISS
    # ------------------------------------------

    scores, indices = index.search(
        query_embedding,
        top_k,
    )

    # ------------------------------------------
    # Print results
    # ------------------------------------------

    print()
    print(f"Query: {query}")
    print(f"Strategy: {strategy}")
    print()

    for rank in range(top_k):

        document_index = indices[0][rank]
        similarity = scores[0][rank]

        document = documents[document_index]

        selected_answers = select_answers(
            document["answers"],
            strategy,
        )

        print("=" * 70)
        print(f"Result {rank + 1}")
        print(f"Similarity: {similarity:.4f}")
        print(
            f"Question ID: "
            f"{document['question_id']}"
        )
        print(f"Link: {document['link']}")
        print()

        print(
            f"Title: {document['title']}"
        )
        print()

        print("Question:")
        print(document["question"])
        print()

        # --------------------------------------
        # Answers selected by strategy
        # --------------------------------------

        if len(selected_answers) == 0:
            print(
                "No answer available "
                "for this strategy."
            )
            print()
            continue

        for answer_number, answer in enumerate(
            selected_answers,
            start=1,
        ):

            print("-" * 50)
            print(
                f"Selected answer "
                f"{answer_number}"
            )
            print(
                f"Answer ID: "
                f"{answer['answer_id']}"
            )
            print(
                f"Accepted: "
                f"{answer['is_accepted']}"
            )
            print(
                f"Stack Overflow score: "
                f"{answer['score']}"
            )
            print()
            print(answer["answer"])
            print()


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Search the local Stack Overflow "
            "RAG index"
        )
    )

    parser.add_argument(
        "-t",
        "--tag",
        required=True,
        help="Stack Overflow tag",
    )

    parser.add_argument(
        "-q",
        "--query",
        required=True,
        help="Question to search for",
    )

    parser.add_argument(
        "-k",
        "--top-k",
        type=int,
        default=3,
        help="Number of questions to retrieve",
    )

    parser.add_argument(
        "-s",
        "--strategy",
        choices=[
            "accepted",
            "highest-score",
            "all",
        ],
        default="highest-score",
        help="Answer selection strategy",
    )

    args = parser.parse_args()

    search(
        args.tag,
        args.query,
        args.top_k,
        args.strategy,
    )


if __name__ == "__main__":
    main()