import argparse
import json
from pathlib import Path

import faiss
import numpy as np
import requests
from sentence_transformers import SentenceTransformer

from query import select_answers


def retrieve(
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
    # Load documents and FAISS index
    # ------------------------------------------

    with open(documents_path, "r") as file:
        documents = json.load(file)

    index = faiss.read_index(
        str(index_path)
    )

    # ------------------------------------------
    # Embed query
    # ------------------------------------------

    model_name = "sentence-transformers/all-MiniLM-L6-v2"

    embedding_model = SentenceTransformer(
        model_name
    )

    query_embedding = embedding_model.encode(
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

    retrieved_documents = []

    for rank in range(top_k):

        document_index = indices[0][rank]
        similarity = scores[0][rank]

        document = documents[document_index]

        selected_answers = select_answers(
            document["answers"],
            strategy,
        )

        # For example, with the accepted strategy,
        # some questions may have no accepted answer.
        if len(selected_answers) == 0:
            continue

        result = {
            "rank": rank + 1,
            "similarity": float(similarity),
            "question_id": document["question_id"],
            "title": document["title"],
            "question": document["question"],
            "link": document["link"],
            "answers": selected_answers,
        }

        retrieved_documents.append(result)

    return retrieved_documents


def build_context(retrieved_documents):
    context_parts = []

    for source_number, document in enumerate(
        retrieved_documents,
        start=1,
    ):

        source_text = (
            f"Source {source_number}\n"
            f"Title: {document['title']}\n"
            f"Question: {document['question']}\n"
        )

        for answer_number, answer in enumerate(
            document["answers"],
            start=1,
        ):

            source_text += (
                f"\nAnswer {answer_number}:\n"
                f"{answer['answer']}\n"
                f"Accepted: {answer['is_accepted']}\n"
                f"Score: {answer['score']}\n"
            )

        context_parts.append(source_text)

    return "\n\n".join(context_parts)


def generate_answer(
    query: str,
    context: str,
    model: str,
):
    prompt = f"""
You are a technical assistant answering a question using
retrieved Stack Overflow material.

RULES:

1. Use only information contained in the retrieved context.
2. Do not use outside knowledge.
3. Do not invent syntax, functions, arguments, configuration,
   commands, or behavior.
4. If you show code or syntax, it must be directly supported
   by the retrieved context.
5. Cite supporting material using [Source 1], [Source 2], etc.
6. If the context only answers a narrower version of the
   user's question, explain that limitation.
7. If the context is insufficient, say exactly what is missing.
8. Give a concise answer. Do not repeat irrelevant details
   from the retrieved posts.

User question:
{query}

Retrieved context:
{context}

Answer:
"""

    response = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": 256,
            },
            "keep_alive": "10m",
        },
        timeout=900,
    )

    response.raise_for_status()

    response_data = response.json()

    return response_data["response"]

def main():
    parser = argparse.ArgumentParser(
        description="Generate a RAG answer using Ollama"
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
        help="Question to answer",
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

    parser.add_argument(
        "-m",
        "--model",
        default="llama3.2:3b",
        help="Ollama model",
    )

    args = parser.parse_args()

    # ------------------------------------------
    # Retrieval
    # ------------------------------------------

    retrieved_documents = retrieve(
        args.tag,
        args.query,
        args.top_k,
        args.strategy,
    )

    if len(retrieved_documents) == 0:
        print(
            "No usable context was retrieved "
            "for this strategy."
        )
        return

    # ------------------------------------------
    # Build context
    # ------------------------------------------

    context = build_context(
        retrieved_documents
    )
    context_length = len(context)

    print(
        f"Context characters: {context_length}"
    )
    
    # ------------------------------------------
    # Generate answer
    # ------------------------------------------

    print()
    print(f"Query: {args.query}")
    print(f"Strategy: {args.strategy}")
    print(f"Model: {args.model}")
    print()
    print("Generating answer...")
    print()

    answer = generate_answer(
        args.query,
        context,
        args.model,
    )

    print("=" * 70)
    print("Generated answer")
    print("=" * 70)
    print()
    print(answer)

    # ------------------------------------------
    # Show retrieved sources
    # ------------------------------------------

    print()
    print("=" * 70)
    print("Retrieved sources")
    print("=" * 70)

    for source_number, document in enumerate(
        retrieved_documents,
        start=1,
    ):

        print()
        print(
            f"Source {source_number}: "
            f"{document['title']}"
        )
        print(
            f"Similarity: "
            f"{document['similarity']:.4f}"
        )
        print(document["link"])


if __name__ == "__main__":
    main()