from datetime import datetime

from airflow import DAG
from conveyor.operators import ConveyorContainerOperatorV2

with DAG(
    dag_id="capstone_conveyor_llm",
    start_date=datetime(2026, 9, 11),
    schedule=None,
    catchup=False,
) as dag:

    ingest_data = ConveyorContainerOperatorV2(
        task_id="ingest_data",
        command=["python3"],
        arguments=[
            "-m",
            "capstonellm.tasks.ingest",
            "-t",
            "dbt",
        ],
        instance_type="mx.small",
        aws_role="capstone_conveyor_llm",
    )

    clean_data = ConveyorContainerOperatorV2(
        task_id="clean_data",
        command=["python3"],
        arguments=[
            "-m",
            "capstonellm.tasks.clean",
            "-e",
            "prod",
            "-t",
            "dbt",
        ],
        instance_type="mx.medium",
        aws_role="capstone_conveyor_llm",
    )

    ingest_data >> clean_data