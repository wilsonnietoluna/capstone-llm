import os
from datetime import datetime

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator


tags = ["airflow", "apache-spark", "dbt", "docker", "pyspark", "python-polars", "sql"]


with DAG(
    dag_id="capstone_ingest_clean",
    start_date=datetime(2026, 9, 11),
    schedule=None,
    catchup=False,
) as dag:

    previous_task = None

    for tag in tags:

        task_tag = tag.replace("-", "_")

        ingest_data = DockerOperator(
            task_id=f"ingest_{task_tag}",
            image="capstonellm:latest",
            command=f"python3 -m capstonellm.tasks.ingest -t {tag}",
            docker_url="unix://var/run/docker.sock",
            network_mode="bridge",
            auto_remove="force",
            mount_tmp_dir=False,
            environment={
                "AWS_ACCESS_KEY_ID": os.environ["AWS_ACCESS_KEY_ID"],
                "AWS_SECRET_ACCESS_KEY": os.environ["AWS_SECRET_ACCESS_KEY"],
                "AWS_SESSION_TOKEN": os.environ.get(
                    "AWS_SESSION_TOKEN",
                    "",
                ),
            },
        )

        clean_data = DockerOperator(
            task_id=f"clean_{task_tag}",
            image="capstonellm:latest",
            command=(
                f"python3 -m capstonellm.tasks.clean "
                f"-e prod -t {tag}"
            ),
            docker_url="unix://var/run/docker.sock",
            network_mode="bridge",
            auto_remove="force",
            mount_tmp_dir=False,
            environment={
                "AWS_ACCESS_KEY_ID": os.environ["AWS_ACCESS_KEY_ID"],
                "AWS_SECRET_ACCESS_KEY": os.environ["AWS_SECRET_ACCESS_KEY"],
                "AWS_SESSION_TOKEN": os.environ.get(
                    "AWS_SESSION_TOKEN",
                    "",
                ),
            },
        )

        ingest_data >> clean_data

        if previous_task is not None:
            previous_task >> ingest_data

        previous_task = clean_data