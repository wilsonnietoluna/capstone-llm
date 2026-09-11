from datetime import datetime

from airflow import DAG
from conveyor.operators import ConveyorContainerOperatorV2


tags = ["airflow", "apache-spark", "dbt", "docker", "pyspark", "python-polars", "sql"]

with DAG(
    dag_id="capstone_conveyor_llm",
    start_date=datetime(2026, 9, 11),
    schedule=None,
    catchup=False,
) as dag:

    previous_task = None

    for tag in tags:

        task_tag = tag.replace("-", "_")

        ingest_data = ConveyorContainerOperatorV2(
            task_id=f"ingest_{task_tag}",
            command=["python3"],
            arguments=[
                "-m",
                "capstonellm.tasks.ingest",
                "-t",
                tag,
            ],
            instance_type="mx.small",
            aws_role="capstone_conveyor_llm",
        )

        clean_data = ConveyorContainerOperatorV2(
            task_id=f"clean_{task_tag}",
            command=["python3"],
            arguments=[
                "-m",
                "capstonellm.tasks.clean",
                "-e",
                "prod",
                "-t",
                tag,
            ],
            instance_type="mx.medium",
            aws_role="capstone_conveyor_llm",
        )

        ingest_data >> clean_data

        if previous_task is not None:
            previous_task >> ingest_data

        previous_task = clean_data