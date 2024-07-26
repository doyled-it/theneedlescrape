import json
from datetime import datetime

import pandas as pd
import plotly.express as px


def safe_float(value):
    try:
        return float(value)
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
            original_score = score  # Keep the original score for tooltip

            if score is None:
                print(f"Skipping entry with no score on line {line_num}")
                skipped_entries += 1
                continue

            if isinstance(score, str):
                score = score.lower().strip()
                if score in ["classic", "classic/10"]:
                    score = 9.5  # Changed from 10 to 9.5
                    original_score = "Classic"
                elif score in ["not good", "not good/10"]:
                    score = 0.5  # Changed from 0 to 0.5
                    original_score = "NOT GOOD"
                else:
                    try:
                        score = safe_float(score.split("/")[0])
                    except (AttributeError, IndexError):
                        print(f"Skipping invalid score: {score} on line {line_num}")
                        skipped_entries += 1
                        continue

            if score is None:
                print(f"Skipping invalid score: {score} on line {line_num}")
                skipped_entries += 1
                continue

            date = review.get("date")
            year = safe_float(review.get("year"))

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
                    "year": int(year),
                    "score": score,
                    "original_score": original_score,
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
    title="TheNeedleDrop Review Scores Over Time",
    custom_data=["original_score", "artist", "album"],
)
fig1.update_traces(
    marker=dict(size=8),
    hovertemplate="<br>".join(
        [
            "Date: %{x}",
            "Score: %{customdata[0]}",
            "Artist: %{customdata[1]}",
            "Album: %{customdata[2]}",
        ]
    ),
)
fig1.update_layout(
    xaxis_title="Review Date",
    yaxis_title="Score",
    yaxis=dict(
        range=[-0.5, 10.5],  # Extended range for breathing room
        tickmode="linear",
        tick0=0,
        dtick=1,
        tickvals=list(range(0, 11)),
        ticktext=list(range(0, 11)),
    ),
)

# 2. Score vs. year plot (modified)
fig2 = px.box(
    df,
    x="year",
    y="score",
    points="outliers",
    title="TheNeedleDrop Review Scores by Year",
    boxmode="overlay",
    notched=True,
    custom_data=["original_score", "artist", "album"],
)
fig2.update_traces(
    boxpoints="outliers",
    jitter=0,
    marker=dict(size=5, opacity=0.7),
    hovertemplate="<br>".join(
        [
            "Year: %{x}",
            "Score: %{customdata[0]}",
            "Artist: %{customdata[1]}",
            "Album: %{customdata[2]}",
        ]
    ),
)
fig2.update_layout(
    xaxis_title="Album Release Year",
    yaxis_title="Score",
    yaxis=dict(
        range=[-0.5, 10.5],  # Extended range for breathing room
        tickmode="linear",
        tick0=0,
        dtick=1,
        tickvals=list(range(0, 11)),
        ticktext=list(range(0, 11)),
    ),
)

# Display the plots
fig1.show()
fig2.show()

# Optionally, save the plots as HTML files for easy sharing
fig1.write_html("score_vs_date.html")
fig2.write_html("score_vs_year.html")
