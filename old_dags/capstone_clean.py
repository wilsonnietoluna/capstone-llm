import os
from datetime import datetime

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator

with DAG(
    dag_id="capstone_clean",
    start_date=datetime(2026, 9, 11),
    schedule=None,
    catchup=False,
) as dag:

    clean_data = DockerOperator(
        task_id="clean_data",
        image="capstonellm:latest",
        command="python3 -m capstonellm.tasks.clean -e prod -t dbt",
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge",
        auto_remove="force",
        environment={
            "AWS_ACCESS_KEY_ID": os.environ["AWS_ACCESS_KEY_ID"],
            "AWS_SECRET_ACCESS_KEY": os.environ["AWS_SECRET_ACCESS_KEY"],
            "AWS_SESSION_TOKEN": os.environ.get("AWS_SESSION_TOKEN", ""),
        },
    )