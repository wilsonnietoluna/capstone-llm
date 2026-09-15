#!/usr/bin/env bash

set -euo pipefail

tags=(
    "airflow"
    "apache-spark"
    "dbt"
    "docker"
    "pyspark"
    "python-polars"
    "sql"
)

for tag in "${tags[@]}"
do
    echo
    echo "===================================="
    echo "Processing tag: $tag"
    echo "===================================="

    questions="local/data/raw/$tag/questions.json"
    answers="local/data/raw/$tag/answers.json"

    # Only call Stack Overflow if the raw data
    # does not already exist locally.
    if [[ -f "$questions" && -f "$answers" ]]
    then
        echo "Raw data already exists. Skipping ingest."
    else
        echo "Ingesting Stack Overflow data..."
        uv run python local/ingest.py -t "$tag"
    fi

    echo "Cleaning with Spark..."
    uv run python local/spark/clean.py -t "$tag"

    echo "Finished: $tag"
done

echo
echo "All tags finished."