import argparse
import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


def build_index(tag: str):
    input_path = Path(
        f"local/data/rag/{tag}/documents.json"
    )

    output_dir = Path(
        f"local/data/rag/{tag}"
    )

    index_path = output_dir / "index.faiss"

    # ------------------------------------------
    # Load documents
    # ------------------------------------------

    with open(input_path, "r") as file:
        documents = json.load(file)

    texts = []

    for document in documents:
        texts.append(document["text"])

    print(f"Documents: {len(texts)}")

    # ------------------------------------------
    # Load embedding model
    # ------------------------------------------

    model_name = "sentence-transformers/all-MiniLM-L6-v2"

    print(f"Loading model: {model_name}")

    model = SentenceTransformer(model_name)

    # ------------------------------------------
    # Create embeddings
    # ------------------------------------------

    print("Creating embeddings...")

    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    embeddings = np.asarray(
        embeddings,
        dtype="float32",
    )

    print(f"Embedding shape: {embeddings.shape}")

    # ------------------------------------------
    # Create FAISS index
    # ------------------------------------------

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(dimension)

    index.add(embeddings)

    print(f"Vectors in index: {index.ntotal}")

    # ------------------------------------------
    # Save index
    # ------------------------------------------

    faiss.write_index(
        index,
        str(index_path),
    )

    print(f"Saved index to: {index_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Build FAISS index for RAG"
    )

    parser.add_argument(
        "-t",
        "--tag",
        required=True,
        help="Stack Overflow tag",
    )

    args = parser.parse_args()

    build_index(args.tag)


if __name__ == "__main__":
    main()