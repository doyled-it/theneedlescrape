import json
import time

import musicbrainzngs
import requests

from tns.utils.logger import create_logger
from tns.utils.progress import track

log = create_logger(__name__)

# Set up MusicBrainz API
musicbrainzngs.set_useragent("theneedlepoint", "0.1.0", "michaeldoyle1994@gmail.com")


def search_album_mbid(artist: str, album: str) -> str:
    """Search for the MusicBrainz ID for an album.

    Arguments:
        artist: The artist name.
        album: The album name.

    Returns:
        The MusicBrainz ID for the album, or None if not found
    """
    try:
        result = musicbrainzngs.search_release_groups(
            artist=artist, release=album, limit=1
        )
        if result["release-group-list"]:
            return result["release-group-list"][0]["id"]
    except musicbrainzngs.WebServiceError as exc:
        log.error(f"Error searching for {artist} - {album}: {exc}")
    return None


def get_genres(mbid: str) -> list:
    """Get the genres for a given MusicBrainz release group ID.

    Arguments:
        mbid: The MusicBrainz release group ID.

    Returns:
        A list of genres for the release group.
    """
    try:
        result = musicbrainzngs.get_release_group_by_id(mbid, includes=["tags"])
        genres = result["release-group"].get("tag-list", [])
        return [genre["name"] for genre in genres]
    except musicbrainzngs.WebServiceError as exc:
        log.error(f"Error fetching genres for MBID {mbid}: {exc}")
    return []


def get_cover_art_links(mbid: str) -> tuple:
    """Get the cover art links for a given MusicBrainz release group ID.

    Arguments:
        mbid: The MusicBrainz release group ID.

    Returns:
        A tuple containing the full image URL and the thumbnail URL.
    """
    url = f"http://coverartarchive.org/release-group/{mbid}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data["images"]:
                full_image = data["images"][0]["image"]
                thumbnail = None
                # Look for the smallest thumbnail available
                for image in data["images"]:
                    if "thumbnails" in image:
                        thumbnails = image["thumbnails"]
                        # Prioritize smaller thumbnails
                        for size in ["250", "small", "large"]:
                            if size in thumbnails:
                                thumbnail = thumbnails[size]
                                break
                        if thumbnail:
                            break
                return full_image, thumbnail or full_image
    except requests.RequestException as exc:
        log.error(f"Error fetching cover art for MBID {mbid}: {exc}")
    return None, None


def get_processed_urls(output_file: str) -> set:
    """Return a set of URLs that have already been processed.

    Arguments:
        output_file: The file to read processed URLs from.

    Returns:
        A set of URLs that have already been processed.
    """
    processed = set()
    try:
        with open(output_file, "r") as f:
            for line in f:
                entry = json.loads(line)
                url = entry.get("url")
                if url:
                    processed.add(url)
    except FileNotFoundError:
        pass  # Output file doesn't exist yet, which is fine
    return processed


def get_mbid_info(input_file: str, output_file: str) -> None:
    """Process the input file, adding MBIDs, genres and cover art links.

    Arguments:
        input_file: The input file to process.
        output_file: The output file to write the processed data to.
    """

    processed_urls = get_processed_urls(output_file)

    with open(input_file, "r") as infile:
        input_lines = infile.readlines()

    with open(output_file, "a") as outfile:
        for line in track(
            input_lines,
            description="Collecting MBIDs, Genres & Cover Art",
            total=len(input_lines),
        ):
            entry = json.loads(line)
            url = entry.get("url")

            if url in processed_urls:
                log.info(f"Skipping already processed entry: {url}")
                continue

            artist = entry.get("artist")
            album = entry.get("album")

            if artist and album:
                if "Run Overdrive" in album:
                    album = album.replace(" 7'' | REVIEW", "").replace('"', "")
                if "| REVIEW" in album:
                    album = album.replace("| REVIEW", "")
                if "‡ REVIEW" in album:
                    album = album.replace("‡ REVIEW", "")

                mbid = search_album_mbid(artist, album)
                if mbid:
                    entry["album_mbid"] = mbid

                    # Fetch and add genres
                    genres = get_genres(mbid)
                    if genres:
                        entry["mb_genres"] = genres
                    else:
                        log.warning(f"No genres found for {artist} - {album}")

                    full_image, thumbnail = get_cover_art_links(mbid)
                    if full_image:
                        entry["cover_art_full"] = full_image
                        entry["cover_art_thumbnail"] = thumbnail
                    else:
                        log.warning(f"No cover art found for {artist} - {album}")
                else:
                    log.warning(f"No MBID found for {artist} - {album}")

            json.dump(entry, outfile)
            outfile.write("\n")
            outfile.flush()  # Ensure the data is written immediately

            processed_urls.add(url)

            # Be nice to the APIs
            time.sleep(0.5)


if __name__ == "__main__":
    input_file = "data/final_review_info.jsonl"
    output_file = "data/output_with_mbid_genres_and_cover_art.jsonl"
    get_mbid_info(input_file, output_file)
    log.info("Processing complete. Check the output file.")
