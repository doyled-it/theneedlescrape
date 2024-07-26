import json
from datetime import datetime

import pandas as pd
import plotly.express as px


def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def process_jsonl(file_path):
    data = []
    skipped_entries = 0
    with open(file_path, "r") as file:
        for line_num, line in enumerate(file, 1):
            try:
                review = json.loads(line)
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON on line {line_num}")
                skipped_entries += 1
                continue

            score = review.get("review_score")

            if score is None:
                print(f"Skipping entry with no score on line {line_num}")
                skipped_entries += 1
                continue

            if score == "classic":
                score = 10
            elif score == "not good":
                score = 0
            else:
                try:
                    score = int(score.split("/")[0])
                except (AttributeError, ValueError, IndexError):
                    print(f"Skipping invalid score: {score} on line {line_num}")
                    skipped_entries += 1
                    continue

            date = review.get("date")
            year = safe_int(review.get("year"))

            if date is None or year is None:
                print(
                    f"Skipping entry with invalid date or year on line {line_num}: "
                    f"date={date}, year={year}"
                )
                skipped_entries += 1
                continue

            try:
                date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                print(
                    f"Skipping entry with invalid date format on line {line_num}: {date}"
                )
                skipped_entries += 1
                continue

            data.append(
                {
                    "date": date,
                    "year": year,
                    "score": score,
                    "artist": review.get("artist", "Unknown Artist"),
                    "album": review.get("album", "Unknown Album"),
                }
            )

    if not data:
        raise ValueError("No valid data found in the file.")

    print(f"Processed {len(data)} valid entries. Skipped {skipped_entries} entries.")
    return pd.DataFrame(data)


# Read and process the data
try:
    df = process_jsonl("data/final_review_info.jsonl")
except Exception as e:
    print(f"Error processing the file: {e}")
    exit(1)

# 1. Score vs. date plot
fig1 = px.scatter(
    df,
    x="date",
    y="score",
    hover_data=["artist", "album"],
    title="TheNeedleDrop Review Scores Over Time",
)
fig1.update_traces(marker=dict(size=8))
fig1.update_layout(
    xaxis_title="Review Date",
    yaxis_title="Score",
    yaxis=dict(
        range=[-0.5, 10.5],  # Extended range
        tickmode="linear",
        tick0=0,
        dtick=1,
        tickvals=list(range(0, 11)),  # Ensure ticks are only on whole numbers
        ticktext=list(range(0, 11)),  # Label ticks with whole numbers
    ),
)

# 2. Score vs. year plot (modified)
fig2 = px.box(
    df,
    x="year",
    y="score",
    points="outliers",  # Only show outliers
    hover_data=["artist", "album"],
    title="TheNeedleDrop Review Scores by Year",
    boxmode="overlay",  # Overlay boxes instead of grouping
    notched=True,  # Add notches to show confidence interval around median
)
fig2.update_traces(
    boxpoints="outliers",  # Ensure only outliers are shown as points
    jitter=0,  # Remove jitter for cleaner appearance
    marker=dict(size=5, opacity=0.7),  # Adjust marker size and opacity for outliers
)
fig2.update_layout(
    xaxis_title="Album Release Year",
    yaxis_title="Score",
    yaxis=dict(
        range=[-0.5, 10.5],  # Extended range
        tickmode="linear",
        tick0=0,
        dtick=1,
        tickvals=list(range(0, 11)),  # Ensure ticks are only on whole numbers
        ticktext=list(range(0, 11)),  # Label ticks with whole numbers
    ),
)

# Display the plots
fig1.show()
fig2.show()

# Optionally, save the plots as HTML files for easy sharing
fig1.write_html("score_vs_date.html")
fig2.write_html("score_vs_year.html")
