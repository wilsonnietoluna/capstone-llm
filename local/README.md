# Local Capstone LLM Pipeline

This directory contains a fully local version of the original `capstone-llm`
project.

The original capstone was developed using AWS S3, Apache Spark, Airflow, Docker,
and Conveyor. This local version removes the dependency on cloud infrastructure
so that the project can continue to be developed and tested on a personal
computer.

The pipeline collects Stack Overflow questions and answers, cleans and
structures the data, and prepares it for later use in a Retrieval-Augmented
Generation (RAG) system.

## Pipeline

The current local pipeline is:

```text
Stack Overflow API
        |
        v
   local/ingest.py
        |
        v
local/data/raw/<tag>/
    questions.json
    answers.json
        |
        v
local/spark/clean.py
        |
        v
local/data/cleaned/spark/<tag>/

