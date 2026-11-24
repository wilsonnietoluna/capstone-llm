import argparse
import csv
import statistics
import subprocess
import sys
import time
from pathlib import Path


def run_benchmark(name, command, runs):
    times = []

    print()
    print("=" * 50)
    print(f"Benchmarking: {name}")
    print("=" * 50)

    for run in range(1, runs + 1):
        print(f"Run {run}/{runs}")

        start = time.perf_counter()

        subprocess.run(
            command,
            check=True,
        )

        end = time.perf_counter()

        elapsed = end - start
        times.append(elapsed)

        print(f"{name}: {elapsed:.3f} s")

    return times


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark local cleaning implementations"
    )

    parser.add_argument(
        "-t",
        "--tag",
        default="dbt",
        help="Stack Overflow tag to benchmark",
    )

    parser.add_argument(
        "-r",
        "--runs",
        type=int,
        default=3,
        help="Number of benchmark runs",
    )

    args = parser.parse_args()

    tag = args.tag
    runs = args.runs

    # Make sure the raw data exists
    questions_path = Path(
        f"local/data/raw/{tag}/questions.json"
    )

    answers_path = Path(
        f"local/data/raw/{tag}/answers.json"
    )

    if not questions_path.exists():
        raise FileNotFoundError(
            f"Missing {questions_path}"
        )

    if not answers_path.exists():
        raise FileNotFoundError(
            f"Missing {answers_path}"
        )

    commands = {
        "spark": [
            sys.executable,
            "local/spark/clean.py",
            "-t",
            tag,
        ],

        "polars": [
            sys.executable,
            "local/polars/clean.py",
            "-t",
            tag,
        ],

        "dbt_duckdb": [
            "dbt",
            "run",
            "--project-dir",
            "local/dbt_duckdb",
            "--profiles-dir",
            "local/dbt_duckdb",
            "--vars",
            f'{{"tag": "{tag}"}}',
        ],
    }

    results = {}

    for name in commands:

        times = run_benchmark(
            name,
            commands[name],
            runs,
        )

        results[name] = times


    # ------------------------------------------
    # Print summary
    # ------------------------------------------

    print()
    print("=" * 50)
    print("Benchmark summary")
    print("=" * 50)

    print(
        f"{'Engine':<15}"
        f"{'Mean (s)':>12}"
        f"{'Median (s)':>14}"
        f"{'Min (s)':>12}"
    )

    for name in results:

        times = results[name]

        mean = statistics.mean(times)
        median = statistics.median(times)
        minimum = min(times)

        print(
            f"{name:<15}"
            f"{mean:>12.3f}"
            f"{median:>14.3f}"
            f"{minimum:>12.3f}"
        )


    # ------------------------------------------
    # Save raw benchmark results
    # ------------------------------------------

    output_dir = Path("local/benchmarks")
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_dir / f"{tag}.csv"

    with open(
        output_path,
        "w",
        newline="",
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "engine",
            "run",
            "seconds",
        ])

        for name in results:

            for run_number, elapsed in enumerate(
                results[name],
                start=1,
            ):

                writer.writerow([
                    name,
                    run_number,
                    elapsed,
                ])

    print()
    print(
        f"Results saved to: {output_path}"
    )


if __name__ == "__main__":
    main()