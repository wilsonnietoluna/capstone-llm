import csv
from collections import defaultdict
from pathlib import Path


input_path = Path(
    "local/rag/evaluation/dbt_results.csv"
)

output_path = Path(
    "local/rag/evaluation/dbt_scored.csv"
)


# --------------------------------------------------
# Manual review scores
#
# Each tuple:
# (
#     relevance,
#     groundedness,
#     usefulness,
# )
# --------------------------------------------------

scores = {
    (
        "How do I reference another model in dbt?",
        "accepted",
    ): (0, 1, 0),

    (
        "How do I reference another model in dbt?",
        "highest-score",
    ): (1, 2, 1),

    (
        "How do I reference another model in dbt?",
        "all",
    ): (2, 2, 2),

    (
        "How do I use variables in dbt?",
        "accepted",
    ): (0, 0, 0),

    (
        "How do I use variables in dbt?",
        "highest-score",
    ): (2, 1, 2),

    (
        "How do I use variables in dbt?",
        "all",
    ): (2, 2, 1),

    (
        "How do I load a CSV file in dbt?",
        "accepted",
    ): (2, 1, 2),

    (
        "How do I load a CSV file in dbt?",
        "highest-score",
    ): (1, 2, 1),

    (
        "How do I load a CSV file in dbt?",
        "all",
    ): (1, 2, 1),

    (
        "How do I configure an incremental model in dbt?",
        "accepted",
    ): (1, 2, 1),

    (
        "How do I configure an incremental model in dbt?",
        "highest-score",
    ): (1, 2, 1),

    (
        "How do I configure an incremental model in dbt?",
        "all",
    ): (1, 2, 1),

    (
        "How do I connect dbt to Snowflake using SSO?",
        "accepted",
    ): (1, 2, 1),

    (
        "How do I connect dbt to Snowflake using SSO?",
        "highest-score",
    ): (2, 2, 2),

    (
        "How do I connect dbt to Snowflake using SSO?",
        "all",
    ): (1, 1, 1),
}


# --------------------------------------------------
# Read evaluation results
# --------------------------------------------------

with open(input_path, "r") as file:

    reader = csv.DictReader(file)
    rows = list(reader)


# --------------------------------------------------
# Add scores
# --------------------------------------------------

for row in rows:

    key = (
        row["question"],
        row["strategy"],
    )

    if key not in scores:
        raise KeyError(
            f"No manual score defined for: {key}"
        )

    relevance, groundedness, usefulness = (
        scores[key]
    )

    row["relevance"] = relevance
    row["groundedness"] = groundedness
    row["usefulness"] = usefulness

    row["total_score"] = (
        relevance
        + groundedness
        + usefulness
    )


# --------------------------------------------------
# Save scored CSV
# --------------------------------------------------

fieldnames = list(
    rows[0].keys()
)

with open(
    output_path,
    "w",
    newline="",
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames,
    )

    writer.writeheader()
    writer.writerows(rows)


print(
    f"Scored results saved to: "
    f"{output_path}"
)


# --------------------------------------------------
# Aggregate results by strategy
# --------------------------------------------------

summary = defaultdict(
    lambda: {
        "count": 0,
        "relevance": 0,
        "groundedness": 0,
        "usefulness": 0,
        "total": 0,
        "context_characters": 0,
        "generation_time": 0,
    }
)


for row in rows:

    strategy = row["strategy"]

    summary[strategy]["count"] += 1

    summary[strategy]["relevance"] += int(
        row["relevance"]
    )

    summary[strategy]["groundedness"] += int(
        row["groundedness"]
    )

    summary[strategy]["usefulness"] += int(
        row["usefulness"]
    )

    summary[strategy]["total"] += int(
        row["total_score"]
    )

    summary[strategy]["context_characters"] += int(
        row["context_characters"]
    )

    summary[strategy]["generation_time"] += float(
        row["generation_time_seconds"]
    )


# --------------------------------------------------
# Print summary
# --------------------------------------------------

print()
print("=" * 90)
print("RAG STRATEGY SUMMARY")
print("=" * 90)

print(
    f"{'Strategy':<16}"
    f"{'Rel.':>8}"
    f"{'Ground.':>10}"
    f"{'Useful':>10}"
    f"{'Total':>10}"
    f"{'Context':>12}"
    f"{'Time (s)':>12}"
)


for strategy in [
    "accepted",
    "highest-score",
    "all",
]:

    values = summary[strategy]

    count = values["count"]

    relevance = (
        values["relevance"]
        / count
    )

    groundedness = (
        values["groundedness"]
        / count
    )

    usefulness = (
        values["usefulness"]
        / count
    )

    total = (
        values["total"]
        / count
    )

    context = (
        values["context_characters"]
        / count
    )

    generation_time = (
        values["generation_time"]
        / count
    )

    print(
        f"{strategy:<16}"
        f"{relevance:>8.2f}"
        f"{groundedness:>10.2f}"
        f"{usefulness:>10.2f}"
        f"{total:>10.2f}"
        f"{context:>12.0f}"
        f"{generation_time:>12.1f}"
    )