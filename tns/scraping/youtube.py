import json
import re

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from ..utils.logger import create_logger
from ..utils.progress import track

log = create_logger(__name__)


def load_jsonl(file_path: str) -> list:
    """Load a JSON Lines file into a list of dictionaries.

    Arguments:
        file_path: Path to the JSON Lines file.

    Returns:
        A list of dictionaries.
    """
    with open(file_path, "r") as file:
        return [json.loads(line) for line in file.readlines()]


def extract_review_details(description: str) -> dict:
    """Extract review details from a description.

    Arguments:
        description: Description of the review.

    Returns:
        A dictionary containing the review details.
    """
    details = {
        "whole_description": description,
        "review_score": None,
        "genres": [],
        "fav_tracks": [],
        "least_fav_track": None,
    }

    if len(description) == 0:
        return details

    # Extract review score (e.g., 8/10 or NOT GOOD/10)
    score_match = re.search(r"\b[\dA-Z\s]+/10\b", description)
    if score_match:
        details["review_score"] = score_match.group(0)

    # Extract favorite and least favorite tracks
    fav_tracks_match = re.search(
        r"FAV(?:ORITE)? TRACKS?:\s*(.*)", description, re.IGNORECASE
    )
    if fav_tracks_match:
        details["fav_tracks"] = [
            track.strip().upper() for track in fav_tracks_match.group(1).split(",")
        ]

    least_fav_track_match = re.search(
        r"LEAST FAV(?:ORITE)? TRACK:\s*(.*)", description, re.IGNORECASE
    )
    if least_fav_track_match:
        details["least_fav_track"] = least_fav_track_match.group(1).strip().upper()

    # Define common non-genre words to exclude
    non_genre_words = {
        "LP",
        "I",
        "THIS",
        "OF",
        "THE",
        "AND",
        "WITH",
        "FOR",
        "TRACKS",
        "TRACK",
        "FAV",
        "FAVORITE",
        "LEAST",
        "THENEEDLEDROP",
        "HTTP",
        "WWW",
        "REVIEW",
        "ALBUM",
        "VIDEO",
    }

    # Define genres to look for
    genre_keywords = [
        "ALT",
        "POP",
        "ROCK",
        "HIP",
        "HOP",
        "JAZZ",
        "FUNK",
        "INDIE",
        "BOOGIE",
        "GENRE",
        "METAL",
        "PUNK",
        "AMBIENT",
        "ELECTRONIC",
        "HOUSE",
        "HARDCORE",
        "CLASSIC",
        "COUNTRY",
        "NOISE",
    ]

    # Create a regex pattern for genres
    genre_pattern = re.compile(r"\b([A-Z]+(?:\s[A-Z]+)*(?:,\s*[A-Z]+(?:\s[A-Z]+)*)*)\b")
    genre_line_pattern = re.compile(rf"\b(?:{'|'.join(genre_keywords)})\b", re.IGNORECASE)
    description_lines = description.split("\n")
    genres = set()

    for line in description_lines:
        line = line.strip()
        # Check if the line likely contains genres
        if genre_line_pattern.search(line):
            genre_match = genre_pattern.findall(line)
            for match in genre_match:
                for genre in match.split(","):
                    genre = genre.strip().upper()
                    # Exclude common non-genre words, very short words, and track titles
                    if (
                        genre not in non_genre_words
                        and len(genre) > 3
                        and genre not in details["fav_tracks"]
                        and genre != details["least_fav_track"]
                    ):
                        genres.add(genre)

    details["genres"] = list(genres)
    return details


def get_youtube_description(youtube_link: str) -> str:
    """Get the description of a YouTube video.

    Arguments:
        youtube_link: Link to the YouTube video.

    Returns:
        The description of the YouTube video.
    """
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "force_generic_extractor": True,
        "outtmpl": "%(id)s.%(ext)s",
    }

    with YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(youtube_link, download=False)
        except DownloadError as e:
            log.warning(f"Failed to get video info for {youtube_link}: {e}")
            return ""
        return result.get("description", "")


def load_processed_reviews(output_file: str) -> set:
    """Load already processed reviews from the output file.

    Arguments:
        output_file: Path to the output file.

    Returns:
        A set of URLs of processed reviews.
    """
    try:
        with open(output_file, "r") as file:
            return {json.loads(line)["url"] for line in file}
    except FileNotFoundError:
        return set()


def update_reviews_with_youtube_details(input_file: str, output_file: str) -> None:
    """Update review details with information from YouTube.

    Arguments:
        input_file: Path to the JSON Lines file containing review details.
        output_file: Path to save the updated review details.
    """
    reviews = load_jsonl(input_file)
    processed_urls = load_processed_reviews(output_file)

    with open(output_file, "a") as out_file:
        for review in track(reviews, description="Getting YouTube details"):
            review_url = review["url"]
            if review_url in processed_urls:
                log.info(f"Skipping already processed review: {review_url}")
                continue

            youtube_link = review.get("youtube_link")
            if youtube_link:
                log.debug(f"Processing {youtube_link}")
                description = get_youtube_description(youtube_link)
                details = extract_review_details(description)
                review.update(details)
            else:
                log.warning(f"No YouTube link for {review_url}")

            out_file.write(json.dumps(review) + "\n")
            processed_urls.add(review_url)


if __name__ == "__main__":
    input_file = "data/review_info.jsonl"
    output_file = "data/updated_review_info.jsonl"
    update_reviews_with_youtube_details(input_file, output_file)
