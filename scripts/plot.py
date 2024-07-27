import base64
import json
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


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
                    "youtube_link": review.get("youtube_link", ""),
                    "cover_art_thumbnail": review.get("cover_art_thumbnail", ""),
                    "cover_art_full": review.get("cover_art_full", ""),
                }
            )

    if not data:
        raise ValueError("No valid data found in the file.")

    print(f"Processed {len(data)} valid entries. Skipped {skipped_entries} entries.")
    return pd.DataFrame(data)


try:
    df = process_jsonl("data/output_with_mbid_and_cover_art.jsonl")
except Exception as e:
    print(f"Error processing the file: {e}")
    exit(1)

# Define a custom color palette
color_palette = [
    "#FFCC02",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
]


def encode_font(file_path):
    with open(file_path, "rb") as font_file:
        return base64.b64encode(font_file.read()).decode("utf-8")


# Encode your font files (adjust paths as necessary)
font_woff2 = encode_font("assets/fonts/Montserrat-Black.woff2")
font_woff = encode_font("assets/fonts/Montserrat-Black.woff")
font_otf = encode_font("assets/fonts/Montserrat-Black.otf")
font_ttf = encode_font("assets/fonts/Montserrat-Black.ttf")


def create_layout_with_image(title_text, image_path, bgcolor="#F9F28D"):
    return dict(
        images=[
            dict(
                source=image_path,
                xref="paper",
                yref="paper",
                x=0.5,
                y=1.05,
                sizex=0.2,
                sizey=0.2,
                xanchor="center",
                yanchor="bottom",
            )
        ],
        title=dict(
            text=title_text,
            font=dict(family="Montserrat-Black", size=24, color="#333"),
            y=0.95,
            x=0.5,
            xanchor="center",
            yanchor="top",
        ),
        plot_bgcolor=bgcolor,
        paper_bgcolor=bgcolor,
        font=dict(family="Montserrat-Black", size=12, color="#333"),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(100,100,100,0.5)",
            showline=True,
            linewidth=2,
            linecolor="rgba(0,0,0,0.5)",
        ),
        yaxis=dict(
            range=[-0.5, 10.5],
            tickmode="linear",
            tick0=0,
            dtick=1,
            tickvals=list(range(0, 11)),
            ticktext=list(range(0, 11)),
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(100,100,100,0.5)",
            showline=True,
            linewidth=2,
            linecolor="rgba(0,0,0,0.5)",
        ),
    )


# 1. Score vs. date plot
fig1 = px.scatter(
    df,
    x="date",
    y="score",
    custom_data=[
        "original_score",
        "artist",
        "album",
        "youtube_link",
        "cover_art_thumbnail",
    ],
)
fig1.update_traces(
    marker=dict(
        size=8,
        color="white",
        line=dict(color="black", width=1.5),
    ),
    opacity=1,
    hovertemplate=(
        "<b>%{customdata[1]} - %{customdata[2]}</b><br>"
        "Date: %{x|%B %d, %Y}<br>"
        "Score: %{customdata[0]}<br>"
        "<extra></extra>"  # Important to close hovertemplate correctly
    ),
)
fig1.update_layout(
    create_layout_with_image(
        "THE NEEDLE DROP REVIEWS OVER TIME",
        "assets/img/The_Needle_Drop_logo.png",
    ),
    height=800,
)
fig1.update_xaxes(title_text="Review Date")
fig1.update_yaxes(title_text="Score")

# 2. Score vs. year plot (modified)
fig2 = go.Figure()

for i, year in enumerate(sorted(df["year"].unique())):
    year_data = df[df["year"] == year]
    fig2.add_trace(
        go.Box(
            y=year_data["score"],
            x=[year] * len(year_data),
            name=str(year),
            boxpoints="outliers",
            jitter=0.3,
            whiskerwidth=0.2,
            fillcolor=color_palette[i % len(color_palette)],
            marker_color=color_palette[i % len(color_palette)],
            line_color="rgb(0,0,0)",
            marker=dict(size=5, opacity=0.7),
            customdata=year_data[["original_score", "artist", "album"]].values,
            hovertemplate="<br>".join(
                [
                    "<b>%{customdata[1]} - %{customdata[2]}</b>",
                    "Year: %{x}",
                    "Score: %{customdata[0]}",
                ]
            ),
        )
    )

fig2.update_layout(
    create_layout_with_image(
        "THE NEEDLE DROP REVIEWS BY YEAR",
        "assets/img/The_Needle_Drop_logo.png",
    ),
    height=800,
)
fig2.update_xaxes(title_text="Album Release Year")
fig2.update_yaxes(title_text="Score")


# Display the plots
# fig1.show()
# fig2.show()

# Custom CSS for HTML output
custom_css = f"""
<style>
@font-face {{
  font-family: 'Montserrat-Black';
  src: url(data:font/woff2;charset=utf-8;base64,{font_woff2}) format('woff2'),
       url(data:font/woff;charset=utf-8;base64,{font_woff}) format('woff'),
       url(data:font/ttf;charset=utf-8;base64,{font_ttf}) format('truetype');
       url(data:font/otf;charset=utf-8;base64,{font_otf}) format('opentype');
  font-weight: normal;
  font-style: normal;
}}

body {{
  font-family: 'Montserrat-Black', Arial, sans-serif;
}}
</style>
"""

# Modify the HTML template
html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Review Scores</title>
    {custom_css}
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        #plot {{
            height: 800px;
            width: 100%;
        }}
        .hover-image {{
            max-width: 100px;
            max-height: 100px;
            display: block;
            margin: 5px 0;
        }}
        .hover-info {{
            position: absolute;
            bottom: 10px;
            right: 10px;
            border: 1px solid #ccc;
            padding: 10px;
            background-color: white;
        }}
    </style>
</head>
<body>
    <div id="plot"></div>
    <div class="hover-info"></div>
    <script>
        var plotData = {plot_data};
        Plotly.newPlot('plot', plotData.data, plotData.layout).then(function() {{
            var gd = document.getElementById('plot');
            var hoverInfo = document.querySelector('.hover-info');

            gd.on('plotly_click', function(data) {{
                var point = data.points[0];
                var youtubeLink = point.customdata[3];
                if (youtubeLink) {{
                    window.open(youtubeLink, '_blank');
                }}
            }});

            gd.on('plotly_hover', function(data) {{
                var point = data.points[0];
                var coverArtLink = point.customdata[4];
                if (coverArtLink) {{
                    var hoverInfo = document.querySelector('.hover-info');
                    if (hoverInfo) {{
                        var img = hoverInfo.querySelector('img');
                        if (!img) {{
                            img = document.createElement('img');
                            img.className = 'hover-image';
                            hoverInfo.appendChild(img);
                        }}
                        img.src = coverArtLink;
                    }}
                }}
            }});

            gd.on('plotly_unhover', function(data) {{
                hoverInfo.innerHTML = '';
            }});

            var traces = document.querySelectorAll('#plot .traces');
            traces.forEach(function(trace) {{
                trace.style.fontFamily = "'Montserrat-Black', Arial, sans-serif";
            }});
            Plotly.redraw(gd);
        }});
    </script>
</body>
</html>
"""

# Save the plots as HTML files
with open("score_vs_date.html", "w") as f:
    plot_data = json.loads(fig1.to_json())
    f.write(html_template.format(custom_css=custom_css, plot_data=json.dumps(plot_data)))

with open("score_vs_year.html", "w") as f:
    plot_data = json.loads(fig2.to_json())
    f.write(html_template.format(custom_css=custom_css, plot_data=json.dumps(plot_data)))

print(
    "HTML files have been generated with embedded fonts. You can now open them in your "
    "browser."
)
