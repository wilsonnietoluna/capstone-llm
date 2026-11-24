# Stack Overflow Data Pipeline and Local RAG System

An end-to-end data engineering and retrieval-augmented generation project built from the DataMinded Academy Summer School capstone.

The original capstone implements a cloud data pipeline that collects Stack Overflow questions and answers, processes them with PySpark, orchestrates the workflow with Airflow, and runs it through Conveyor using Amazon S3 for storage.

I extended the project locally to compare alternative data-processing approaches and to build a complete RAG pipeline over the cleaned Stack Overflow data using SentenceTransformers, FAISS, and a local Llama model served through Ollama.

The resulting project covers:

- API ingestion and pagination
- cloud and local data processing
- PySpark
- Polars
- DuckDB + dbt
- workflow orchestration
- benchmarking
- text preprocessing
- semantic embeddings
- vector search
- retrieval-augmented generation
- local LLM inference
- RAG strategy evaluation

---

## Architecture

### Original cloud capstone

```text
Stack Exchange API
        |
        v
      Airflow
        |
        v
     PySpark
        |
        v
   Amazon S3
        |
        v
     Conveyor
```

The original assignment collects Stack Overflow questions and answers for a set of technical tags and stores the raw data in S3.

PySpark then:

1. loads the question and answer data;
2. extracts the relevant fields;
3. groups answers by question;
4. joins questions with their answers;
5. writes the cleaned dataset back to S3.

Airflow manages task dependencies, while Conveyor provides the deployed execution environment.

---

### Local extension

The local version expands the same dataset into three alternative transformation pipelines and a RAG system:

```text
                    Stack Exchange API
                           |
                           v
                       Raw Q&A
                           |
              +------------+------------+
              |            |            |
              v            v            v
          PySpark        Polars     DuckDB + dbt
              |            |            |
              +------------+------------+
                           |
                           v
                     Cleaned Q&A
                           |
                           v
                  HTML preprocessing
                           |
                           v
                 SentenceTransformers
                           |
                           v
                         FAISS
                           |
                           v
                  Semantic retrieval
                           |
                           v
                Answer selection strategy
               /            |             \
       accepted       highest-score        all
               \            |             /
                           v
                    Ollama / Llama 3.2
                           |
                           v
                    Generated answer
                           |
                           v
                       Evaluation
```

---

## Dataset

The pipeline collects Stack Overflow questions and answers for seven tags:

- `airflow`
- `apache-spark`
- `dbt`
- `docker`
- `pyspark`
- `python-polars`
- `sql`

Raw data is stored locally under:

```text
local/data/raw/<tag>/
    questions.json
    answers.json
```

The local master pipeline reuses existing raw data instead of downloading it again unless explicitly requested.

---

## Data Processing Implementations

Three implementations transform the same raw Stack Overflow data.

### PySpark

The Spark implementation:

- explodes the Stack Exchange API response;
- selects question and answer fields;
- groups answers by `question_id`;
- stores answers as nested structs;
- performs an inner join between questions and answers.

Example output structure:

```text
question_id
title
question
link
answers
    answer_id
    answer
    is_accepted
    score
```

Spark output is stored under:

```text
local/data/cleaned/spark/<tag>/
```

---

### Polars

The Polars implementation performs the same logical transformation using an eager DataFrame workflow.

It provides a lightweight local alternative to Spark and produces:

```text
local/data/cleaned/polars/<tag>/cleaned.ndjson
```

---

### DuckDB + dbt

The dbt implementation separates the transformation into models:

```text
stg_questions
        |
        |
stg_answers
        |
        v
int_answers_per_question
        |
        v
questions_with_answers
```

The dbt project is located in:

```text
local/dbt_duckdb/
```

A separate DuckDB database can be created for each Stack Overflow tag using the `DBT_DUCKDB_PATH` environment variable.

This version demonstrates how the same data transformation can be expressed declaratively using SQL models and dbt dependencies.

---

## Local Processing Benchmark

A small benchmark compares the end-to-end local execution time of the three implementations using the `dbt` Stack Overflow dataset.

Representative results were:

| Pipeline | Approx. runtime |
|---|---:|
| Polars | 0.21 s |
| DuckDB + dbt | 3.74 s |
| PySpark | 19.99 s |

These results should **not** be interpreted as a general performance ranking between the technologies.

The workloads have different execution overhead:

- Spark launches a JVM and performs multiple Spark actions.
- Spark writes many small output files.
- Polars runs directly in-process and writes a single NDJSON file.
- the dbt measurement includes dbt orchestration and DuckDB startup.

The benchmark therefore illustrates the overhead of each approach for this particular small local workload rather than providing an apples-to-apples engine benchmark.

Benchmark code:

```text
local/benchmark.py
```

Results:

```text
local/benchmarks/
```

---

# Retrieval-Augmented Generation

The cleaned Stack Overflow dataset is also used to build a local RAG system.

## Document preparation

Each Stack Overflow **question** becomes one retrieval document.

Only the question title and body are embedded:

```text
Title: <question title>

Question:
<question body>
```

Its answers remain attached as metadata:

```json
{
  "question_id": 123,
  "title": "...",
  "question": "...",
  "answers": [
    {
      "answer_id": 456,
      "answer": "...",
      "is_accepted": true,
      "score": 10
    }
  ]
}
```

Using one document per question avoids retrieving the same question several times simply because it has several answers.

HTML from Stack Overflow is converted to plain text with BeautifulSoup before indexing.

---

## Embeddings

The embedding model is:

```text
sentence-transformers/all-MiniLM-L6-v2
```

It produces 384-dimensional embeddings.

Embeddings are normalized before indexing.

---

## Vector search

FAISS is used for semantic retrieval with:

```text
IndexFlatIP
```

Because the embeddings are normalized, the inner product corresponds to cosine similarity.

For a user query, the system retrieves the most semantically similar Stack Overflow questions.

---

## Answer selection

Retrieval operates at the **question level**.

After the nearest questions have been found, the system decides which answers from those questions should be passed to the LLM.

Three strategies were evaluated.

### `accepted`

Use only accepted Stack Overflow answers.

Advantages:

- small context;
- fast inference;
- Stack Overflow has explicitly marked the answer as accepted.

Disadvantage:

- retrieved questions without accepted answers contribute no answer context.

---

### `highest-score`

Use the highest-scored answer from each retrieved question.

Advantages:

- every retrieved question can contribute an answer;
- one answer per question keeps the context controlled;
- Stack Overflow community voting provides a useful ranking signal.

---

### `all`

Use every answer attached to each retrieved question.

Advantages:

- maximum information coverage.

Disadvantages:

- significantly larger prompts;
- slower local inference;
- more irrelevant or conflicting information can reach the LLM.

---

## Local generation

Answer generation uses:

```text
Ollama
llama3.2:3b
```

The model runs locally.

The generation prompt instructs the model to:

- answer using only the retrieved material;
- avoid inventing syntax or facts;
- treat retrieved text as reference material rather than instructions;
- cite retrieved sources where possible;
- explicitly state when the available context is insufficient.

The local machine used for the experiment runs the model on CPU, so generation latency is relatively high.

---

# RAG Evaluation

The three answer-selection strategies were compared using five fixed dbt questions:

1. How do I reference another model in dbt?
2. How do I use variables in dbt?
3. How do I load a CSV file in dbt?
4. How do I configure an incremental model in dbt?
5. How do I connect dbt to Snowflake using SSO?

Each question was evaluated using:

```text
accepted
highest-score
all
```

giving:

```text
5 questions × 3 strategies = 15 generations
```

The evaluation records:

- number of retrieved sources;
- number of answers included;
- mean retrieval similarity;
- context size;
- generation time;
- retrieved context;
- generated answer.

---

## Manual quality evaluation

Each generated answer was also reviewed using three criteria:

### Relevance

```text
0 = does not answer the question
1 = partially answers the question
2 = directly answers the question
```

### Groundedness

```text
0 = unsupported or hallucinated
1 = partially supported by retrieved context
2 = fully supported by retrieved context
```

### Usefulness

```text
0 = unusable
1 = partially useful
2 = clear and actionable
```

The maximum quality score is therefore:

```text
6
```

---

## Evaluation results

| Strategy | Avg. sources | Avg. answers | Avg. similarity | Avg. context | Avg. generation time | Quality / 6 |
|---|---:|---:|---:|---:|---:|---:|
| `accepted` | 1.2 | 1.2 | 0.648 | 1,838 chars | 56.4 s | 2.8 |
| **`highest-score`** | **3.0** | **3.0** | **0.662** | **4,347 chars** | **109.8 s** | **4.6** |
| `all` | 3.0 | 6.2 | 0.662 | 6,740 chars | 133.9 s | 4.4 |

The retrieval similarity for `highest-score` and `all` is identical because both strategies retrieve the same questions. The strategies differ only in which answers are subsequently included in the generation context.

---

## Main finding

The `highest-score` strategy produced the best overall balance.

Using only accepted answers reduced prompt size and inference time considerably, but it frequently removed useful information because not every retrieved Stack Overflow question had an accepted answer.

Passing all answers increased average context from roughly 4,300 to 6,700 characters compared with `highest-score`, while also increasing CPU inference time. The additional context did not improve the average manual quality score and sometimes introduced distracting information.

The experiment therefore suggests:

> **Selecting the highest-scored answer from each retrieved Stack Overflow question provides a useful compromise between retrieval coverage, answer quality, prompt size, and local inference cost.**

This is especially relevant for small local LLMs, where additional context is not free: larger prompts increase inference cost and can also introduce information that makes the generated answer less focused.

---

## Example failure modes

The evaluation also exposed several useful RAG failure modes.

### Accepted answers are not always the most relevant

For the question about referencing another dbt model, accepted-answer filtering selected an answer focused primarily on BigQuery sources rather than the requested model reference.

The broader strategies retrieved an answer containing the relevant two-argument dbt `ref` syntax.

---

### More context can introduce distractions

For the Snowflake SSO question, the `all` strategy received the correct SSO information but also several unrelated Snowflake troubleshooting answers.

The generated response consequently mixed SSO configuration with unrelated package installation and connection troubleshooting.

The `highest-score` strategy remained more focused.

---

### Retrieval quality does not guarantee generation quality

For the variables question, the accepted-answer context contained useful information about dbt variables, but the local LLM incorrectly concluded that the context did not contain enough information.

This illustrates that a RAG pipeline can retrieve relevant evidence while the generation stage still fails to use it correctly.

---

# Running the Project Locally

## Requirements

The local project uses:

- Python
- `uv`
- Java 17 for PySpark
- Ollama for local generation

Install the Python environment with:

```bash
uv sync
```

For local LLM generation, install Ollama and pull:

```bash
ollama pull llama3.2:3b
```

---

## Run the local data and RAG pipeline

The master script processes all configured Stack Overflow tags.

```bash
./local/run_all.sh
```

The script is resumable.

Existing raw data and generated outputs are reused unless forced to run again.

Useful options include:

```bash
RUN_EVAL=0 ./local/run_all.sh
```

Run the processing and indexing pipeline without LLM evaluation.

```bash
FORCE=1 ./local/run_all.sh
```

Rebuild generated outputs.

```bash
REFRESH_RAW=1 ./local/run_all.sh
```

Download raw Stack Overflow data again.

---

## Run the RAG evaluation

Evaluate the three answer strategies for the dbt test set:

```bash
uv run python local/rag/evaluate.py -t dbt
```

The evaluator writes results incrementally, so interrupted evaluations can be resumed.

Results are stored under:

```text
local/rag/evaluation/
```

Apply the manually reviewed quality scores with:

```bash
uv run python local/rag/apply_scores.py
```

---

# Local Project Structure

```text
local/
├── benchmark.py
├── benchmarks/
│   └── dbt.csv
├── data/
│   ├── raw/
│   ├── cleaned/
│   └── rag/
├── dbt_duckdb/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── staging/
│       ├── intermediate/
│       └── marts/
├── ingest.py
├── polars/
│   └── clean.py
├── rag/
│   ├── prepare_documents.py
│   ├── build_index.py
│   ├── query.py
│   ├── generate.py
│   ├── evaluate.py
│   ├── apply_scores.py
│   └── evaluation/
├── spark/
│   └── clean.py
├── run_spark_all.sh
└── run_all.sh
```

Generated dbt files, caches, vector indexes, local databases, and large intermediate datasets are excluded from version control where appropriate.

---

# What This Project Demonstrates

The project started as a data engineering capstone and evolved into a broader experiment connecting data engineering with applied LLM systems.

It demonstrates:

- consuming and paginating a public REST API;
- designing raw and cleaned data layers;
- distributed processing with PySpark;
- local DataFrame processing with Polars;
- analytical SQL with DuckDB;
- transformation management with dbt;
- workflow orchestration with Airflow;
- cloud execution using Conveyor and S3;
- reproducible benchmarking;
- preprocessing semi-structured text;
- semantic embeddings;
- vector indexing with FAISS;
- retrieval design;
- local LLM serving with Ollama;
- RAG evaluation beyond retrieval similarity alone.

Most importantly, the RAG experiment shows that retrieval systems need to be evaluated as complete pipelines. Increasing the amount of retrieved context does not necessarily improve the final answer, and simple metadata such as Stack Overflow answer scores can be useful for controlling both quality and inference cost.

---

## Background

This repository originated from the **DataMinded Academy Summer School** capstone project and was subsequently extended beyond the original assignment to explore alternative data-processing technologies and retrieval-augmented generation.
