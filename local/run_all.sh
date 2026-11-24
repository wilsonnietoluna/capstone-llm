#!/usr/bin/env bash

set -uo pipefail


tags=(
    "airflow"
    "apache-spark"
    "dbt"
    "docker"
    "pyspark"
    "python-polars"
    "sql"
)


FORCE="${FORCE:-0}"
REFRESH_RAW="${REFRESH_RAW:-0}"
RUN_BENCHMARK="${RUN_BENCHMARK:-1}"
RUN_EVAL="${RUN_EVAL:-1}"

OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2:3b}"

QUESTIONS_FILE="local/rag/evaluation/questions.json"


failed_ingest=()
failed_spark=()
failed_polars=()
failed_dbt=()
failed_rag=()
failed_evaluation=()


echo
echo "=================================================="
echo "CAPSTONE LOCAL PIPELINE"
echo "=================================================="
echo "FORCE=$FORCE"
echo "REFRESH_RAW=$REFRESH_RAW"
echo "RUN_BENCHMARK=$RUN_BENCHMARK"
echo "RUN_EVAL=$RUN_EVAL"


for tag in "${tags[@]}"
do

    echo
    echo "=================================================="
    echo "TAG: $tag"
    echo "=================================================="


    questions="local/data/raw/$tag/questions.json"
    answers="local/data/raw/$tag/answers.json"

    spark_output="local/data/cleaned/spark/$tag"
    polars_output="local/data/cleaned/polars/$tag/cleaned.ndjson"

    dbt_output="local/data/cleaned/dbt_duckdb/$tag.duckdb"

    rag_documents="local/data/rag/$tag/documents.json"
    rag_index="local/data/rag/$tag/index.faiss"


    # ==================================================
    # INGEST
    # ==================================================

    echo
    echo "[INGEST]"


    if [[ \
        "$REFRESH_RAW" -eq 0 \
        && -f "$questions" \
        && -f "$answers" \
    ]]
    then

        echo "Raw data exists. Skipping."

    else

        echo "Raw data missing. Downloading..."

        if uv run python \
            local/ingest.py \
            -t "$tag"
        then

            echo "Ingest successful."

        else

            echo "Ingest FAILED."

            failed_ingest+=("$tag")

            continue

        fi

    fi


    # ==================================================
    # SPARK
    # ==================================================

    echo
    echo "[SPARK]"


    spark_exists=0

    if [[ -d "$spark_output" ]]
    then

        if find "$spark_output" \
            -name 'part-*.json' \
            -print \
            -quit \
            | grep -q .
        then

            spark_exists=1

        fi

    fi


    if [[ \
        "$FORCE" -eq 0 \
        && "$spark_exists" -eq 1 \
    ]]
    then

        echo "Spark output exists. Skipping."

    else

        if uv run python \
            local/spark/clean.py \
            -t "$tag"
        then

            echo "Spark successful."

        else

            echo "Spark FAILED."

            failed_spark+=("$tag")

        fi

    fi


    # ==================================================
    # POLARS
    # ==================================================

    echo
    echo "[POLARS]"


    if [[ \
        "$FORCE" -eq 0 \
        && -f "$polars_output" \
    ]]
    then

        echo "Polars output exists. Skipping."

    else

        if uv run python \
            local/polars/clean.py \
            -t "$tag"
        then

            echo "Polars successful."

        else

            echo "Polars FAILED."

            failed_polars+=("$tag")

        fi

    fi


    # ==================================================
    # DUCKDB + DBT
    # ==================================================

    echo
    echo "[DUCKDB + DBT]"

    mkdir -p \
        local/data/cleaned/dbt_duckdb


    if [[ \
        "$FORCE" -eq 0 \
        && -f "$dbt_output" \
    ]]
    then

        echo "DuckDB database exists. Skipping."

    else

        if DBT_DUCKDB_PATH="$dbt_output" \
            uv run dbt run \
            --project-dir local/dbt_duckdb \
            --profiles-dir local/dbt_duckdb \
            --vars "{\"tag\": \"$tag\"}"
        then

            echo "DuckDB/dbt successful."

        else

            echo "DuckDB/dbt FAILED."

            failed_dbt+=("$tag")

        fi

    fi


    # ==================================================
    # RAG DOCUMENTS
    # ==================================================

    echo
    echo "[RAG DOCUMENTS]"


    if [[ ! -f "$polars_output" ]]
    then

        echo "Polars output unavailable."
        echo "Skipping RAG."

        failed_rag+=("$tag")

        continue

    fi


    if [[ \
        "$FORCE" -eq 0 \
        && -f "$rag_documents" \
    ]]
    then

        echo "RAG documents exist. Skipping."

    else

        if uv run python \
            local/rag/prepare_documents.py \
            -t "$tag"
        then

            echo "RAG documents successful."

        else

            echo "RAG preparation FAILED."

            failed_rag+=("$tag")

            continue

        fi

    fi


    # ==================================================
    # FAISS
    # ==================================================

    echo
    echo "[FAISS INDEX]"


    if [[ \
        "$FORCE" -eq 0 \
        && -f "$rag_index" \
    ]]
    then

        echo "FAISS index exists. Skipping."

    else

        if uv run python \
            local/rag/build_index.py \
            -t "$tag"
        then

            echo "FAISS index successful."

        else

            echo "FAISS index FAILED."

            failed_rag+=("$tag")

            continue

        fi

    fi


    # ==================================================
    # EVALUATION
    # ==================================================

    if [[ "$RUN_EVAL" -eq 1 ]]
    then

        echo
        echo "[RAG EVALUATION]"


        if uv run python \
            local/rag/evaluate.py \
            -t "$tag" \
            -m "$OLLAMA_MODEL" \
            --questions-file "$QUESTIONS_FILE"
        then

            echo "Evaluation successful."

        else

            echo "Evaluation FAILED."

            failed_evaluation+=("$tag")

        fi

    fi

done


# ==================================================
# BENCHMARK
# ==================================================

if [[ "$RUN_BENCHMARK" -eq 1 ]]
then

    echo
    echo "=================================================="
    echo "BENCHMARK"
    echo "=================================================="


    if [[ \
        "$FORCE" -eq 0 \
        && -f "local/benchmarks/dbt.csv" \
    ]]
    then

        echo "Benchmark already exists. Skipping."

    else

        uv run python \
            local/benchmark.py \
            -t dbt \
            -r 3

    fi

fi


# ==================================================
# SUMMARY
# ==================================================

echo
echo "=================================================="
echo "PIPELINE SUMMARY"
echo "=================================================="


if [[ ${#failed_ingest[@]} -eq 0 ]]
then
    echo "Ingest:       OK"
else
    echo "Ingest failed: ${failed_ingest[*]}"
fi


if [[ ${#failed_spark[@]} -eq 0 ]]
then
    echo "Spark:        OK"
else
    echo "Spark failed: ${failed_spark[*]}"
fi


if [[ ${#failed_polars[@]} -eq 0 ]]
then
    echo "Polars:       OK"
else
    echo "Polars failed: ${failed_polars[*]}"
fi


if [[ ${#failed_dbt[@]} -eq 0 ]]
then
    echo "DuckDB/dbt:   OK"
else
    echo "dbt failed: ${failed_dbt[*]}"
fi


if [[ ${#failed_rag[@]} -eq 0 ]]
then
    echo "RAG:          OK"
else
    echo "RAG failed: ${failed_rag[*]}"
fi


if [[ ${#failed_evaluation[@]} -eq 0 ]]
then
    echo "Evaluation:   OK"
else
    echo "Eval failed: ${failed_evaluation[*]}"
fi


echo
echo "Pipeline finished."