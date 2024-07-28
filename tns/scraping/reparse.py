import json
import re

from ..utils.logger import create_logger

log = create_logger(__name__)


def title_case(s):
    return " ".join(
        word.capitalize() if word.lower() not in ["uk", "and"] else word.upper()
        for word in s.split()
    )


def extract_score(text: str) -> str:
    """Extract a score from a string

    Arguments:
        text: The string to extract the score from

    Returns:
        The extracted score as a string
    """
    # Try to find a numeric score at the end of the description
    numeric_match = re.search(r"\b(10|[0-9](?:\.\d+)?)/10\s*$", text, re.MULTILINE)
    if numeric_match:
        return numeric_match.group(0)

    # If no numeric score at the end, look for any valid score
    numeric_match = re.search(r"\b(10|[0-9](?:\.\d+)?)/10\b(?!\d)", text)
    if numeric_match:
        return numeric_match.group(0)

    # If no numeric score, look for text followed by "/10"
    text_match = re.search(r"\b(\w+(?:\s+\w+){0,3})/10\b(?!\d)", text)
    if text_match:
        return text_match.group(0)

    return None


def extract_year(description: str, tags: list[str], url: str) -> str:
    """Extract the year from a description, tags, or URL

    Arguments:
        description: The description of the review
        tags: The tags associated with the review
        url: The URL of the review

    Returns:
        The extracted year as a string
    """
    current_year = (
        2024  # Update this annually or use a dynamic method to get the current year
    )

    # First, try to find a year in the URL
    url_year_match = re.search(r"/(\d{4})-", url)
    if url_year_match:
        year = int(url_year_match.group(1))
        if 1900 <= year <= current_year:
            return str(year)

    # If not found in URL, look for a 4-digit year in tags
    year_tag = next(
        (
            tag
            for tag in tags
            if tag.isdigit() and len(tag) == 4 and 1900 <= int(tag) <= current_year
        ),
        None,
    )
    if year_tag:
        return year_tag

    # If still not found, search for a year in the format "/ YYYY /" in the description
    year_match = re.search(r"/\s*(19\d{2}|20\d{2})\s*/", description)
    if year_match:
        year = int(year_match.group(1))
        if year <= current_year:
            return str(year)

    # If still not found, search for any 4-digit year between 1900 and current year in
    # the description
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", description)
    if year_match and 1900 <= int(year_match.group(1)) <= current_year:
        return year_match.group(1)

    return None


def is_multi_review(description: str) -> bool:
    # Check if the description contains multiple numbered entries
    return bool(re.search(r"\n\d+\..*\n\d+\.", description, re.DOTALL))


def parse_review(json_obj: dict) -> dict:
    description = json_obj.get("whole_description", "")
    title = json_obj.get("title", "")
    tags = json_obj.get("tags", [])
    url = json_obj.get("url", "")

    # Check if this is a multi-review post
    if is_multi_review(description):
        return {
            "review_score": None,
            "year": json_obj.get("year"),
            "artist": None,
            "album": None,
            "label": None,
            "genres": [],
            "fav_tracks": json_obj.get("fav_tracks", []),
            "least_fav_track": json_obj.get("least_fav_track"),
        }
    # Try to extract score from description
    review_score = extract_score(description)

    # If not found in description, try tags
    if not review_score:
        for tag in tags:
            score = extract_score(tag)
            if score:
                review_score = score
                break

    # Extract year using the new function
    year = extract_year(description, tags, url)

    # Ensure review_score is not the same as the year
    if review_score and review_score.split("/")[0] == year:
        review_score = None

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
                if genre.strip() and not genre.strip().startswith("http")
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
            and not tag.startswith("http")
        ]
        genres = [title_case(genre) for genre in genre_tags]

    # Ensure label is not a single digit or a URL
    if label and (label.isdigit() or label.startswith("http")):
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


def reparse_reviews(input_file: str, output_file: str) -> None:
    """Reparse the review information in the input file and write to the output file

    Arguments:
        input_file: The path to the input file containing the review information
        output_file: The path to the output file to write the updated review information
    """
    with open(input_file, "r") as infile:
        # Read all the lines in the input file
        lines = infile.readlines()
    objs = []
    for line in lines:
        # Parse the JSON object and update the review information
        updated_obj = parse_review(json.loads(line))
        objs.append(updated_obj)
    with open(output_file, "w") as outfile:
        for updated_obj in objs:
            # Write the updated JSON object to the output file
            json.dump(updated_obj, outfile)
            outfile.write("\n")
    log.debug(f"Reparse complete. Updated review information saved to {output_file}")


if __name__ == "__main__":
    input_file = "data/updated_review_info.jsonl"
    output_file = "data/final_review_info.jsonl"
    reparse_reviews(input_file, output_file)
