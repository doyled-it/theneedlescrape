import json
import re


def title_case(s):
    return " ".join(
        word.capitalize() if word.lower() not in ["uk", "and"] else word.upper()
        for word in s.split()
    )


def parse_review(json_obj):
    description = json_obj.get("whole_description", "")
    title = json_obj.get("title", "")

    # Extract review score
    score_match = re.search(r"(\d+|classic|not good)/10", description, re.IGNORECASE)
    review_score = score_match.group(0).upper() if score_match else None

    # Extract year of release
    year = next(
        (tag for tag in json_obj.get("tags", []) if tag.isdigit() and len(tag) == 4), None
    )
    if not year:
        year_match = re.search(r"(\d{4})", description)
        year = year_match.group(1) if year_match else None

    # Extract artist, album, label, and genres
    info_line = None
    for line in description.split("\n"):
        if "/" in line and (
            (year and year in line)
            or any(
                keyword in line.upper()
                for keyword in [
                    "RECORDS",
                    "NATION",
                    "LTD",
                    "4AD",
                    "SELF-RELEASED",
                    "ENTERTAINMENT",
                ]
            )
        ):
            info_line = line
            break

    artist = album = label = None
    genres = []

    if info_line:
        parts = [part.strip() for part in info_line.split("/")]
        if len(parts) >= 3:
            artist_album = parts[0].rsplit("-", 1)
            if len(artist_album) == 2:
                artist, album = artist_album[0].strip(), artist_album[1].strip()
            elif len(artist_album) == 1:
                artist = artist_album[0].strip()

            label = parts[-2] if len(parts) > 3 else None
            genres = [
                title_case(genre.strip())
                for genre in parts[-1].split(",")
                if genre.strip()
            ]

    # If artist or album is still None, try to extract from title
    if artist is None or album is None:
        title_parts = title.split("-")
        if len(title_parts) == 2:
            artist = artist or title_parts[0].strip()
            album = album or title_parts[1].strip()

    # Ensure artist is not "Listen: http" or any URL
    if artist and (artist.startswith("Listen:") or artist.startswith("http")):
        artist = None

    # If artist is still None, try to extract from title
    if artist is None:
        artist = title.split("-")[0].strip()

    # If album is still None, try to extract from title
    if album is None:
        album_match = re.search(r"-\s*(.+)$", title)
        if album_match:
            album = album_match.group(1).strip()

    # If no genres were found, try to extract from tags
    if not genres:
        genre_tags = [
            tag
            for tag in json_obj.get("tags", [])
            if not tag.isdigit()
            and tag.lower() not in ["album", "review", "ep", "new", "loved list"]
        ]
        genres = [title_case(genre) for genre in genre_tags]

    # Ensure label is not a single digit
    if label and label.isdigit() and len(label) == 1:
        label = None

    # Parse favorite tracks
    fav_tracks = json_obj.get("fav_tracks", [])
    if (
        isinstance(fav_tracks, list)
        and len(fav_tracks) == 1
        and isinstance(fav_tracks[0], str)
    ):
        fav_tracks = [track.strip() for track in fav_tracks[0].split(";")]

    # Update the JSON object
    json_obj["review_score"] = review_score
    json_obj["year"] = year
    json_obj["artist"] = artist
    json_obj["album"] = album
    json_obj["label"] = label
    json_obj["genres"] = genres
    json_obj["fav_tracks"] = fav_tracks

    return json_obj


def process_jsonl_file(input_file, output_file):
    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        for line in infile:
            json_obj = json.loads(line.strip())
            updated_obj = parse_review(json_obj)
            json.dump(updated_obj, outfile)
            outfile.write("\n")


# Usage
input_file = "data/updated_review_info.jsonl"
output_file = "data/output.jsonl"
process_jsonl_file(input_file, output_file)
