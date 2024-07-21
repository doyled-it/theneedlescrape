import json
import time

import requests
from bs4 import BeautifulSoup

from tns.utils.logger import create_logger
from tns.utils.progress import track

log = create_logger(__name__)


def load_urls(file_path: str) -> list:
    """Load URLs from a file.

    Arguments:
        file_path: Path to the file containing URLs.

    Returns:
        A list of URLs.
    """
    with open(file_path, "r") as file:
        return [url.strip() for url in file.readlines()]


def load_processed_urls(file_path: str) -> set:
    """Load processed URLs from a file.

    Arguments:
        file_path: Path to the file containing processed URLs.

    Returns:
        A set of processed URLs.
    """
    processed_urls = set()
    try:
        with open(file_path, "r") as file:
            for line in file:
                review_info = json.loads(line)
                processed_urls.add(review_info["url"])
    except FileNotFoundError:
        pass
    return processed_urls


def extract_youtube_link(soup: BeautifulSoup) -> str:
    """Extract the YouTube link from a review page.

    Arguments:
        soup: BeautifulSoup object of the review page.

    Returns:
        The YouTube link.
    """
    # Extract YouTube link from the header
    youtube_link = None
    og_image_tag = soup.find("meta", property="og:image")
    if og_image_tag and og_image_tag.has_attr("content"):
        og_image_url = og_image_tag["content"]
        if og_image_url.startswith("https://i.ytimg.com/vi/"):
            video_id = og_image_url.split("/")[-2]
            youtube_link = f"https://www.youtube.com/watch?v={video_id}"
        else:
            log.debug(f"Unexpected og:image URL: {og_image_url}")

    # Fallback for YouTube link in the body if not found in the header
    if not youtube_link:
        ytp_title_text_div = soup.find("div", class_="ytp-title-text")
        if ytp_title_text_div:
            a_tag = ytp_title_text_div.find("a", href=True)
            if a_tag and "/watch?" in a_tag["href"]:
                youtube_link = a_tag["href"]
                if not youtube_link.startswith("http"):
                    youtube_link = "https://www.youtube.com" + youtube_link

    # Second fallback for YouTube link in <object> tag
    if not youtube_link:
        object_tag = soup.find(
            "object", classid="clsid:d27cdb6e-ae6d-11cf-96b8-444553540000"
        )
        if object_tag:
            param_tag = object_tag.find("param", {"name": "src"})
            if param_tag and param_tag.has_attr("value"):
                video_url = param_tag["value"]
                if "youtube.com/v/" in video_url:
                    video_id = video_url.split("/v/")[1].split("&")[0]
                    youtube_link = f"https://www.youtube.com/watch?v={video_id}"

    # Third fallback for YouTube link in <iframe> tag within post_content
    if not youtube_link:
        iframe_tag = soup.find("iframe", src=True)
        if iframe_tag and "youtube.com/embed/" in iframe_tag["src"]:
            video_id = iframe_tag["src"].split("/embed/")[1].split("?")[0]
            youtube_link = f"https://www.youtube.com/watch?v={video_id}"

    # Fourth fallback for YouTube link in <div id="player">
    if not youtube_link:
        player_div = soup.find("div", id="player")
        if player_div:
            ytp_title_div = player_div.find("div", class_="ytp-title")
            if ytp_title_div:
                a_tag = ytp_title_div.find("a", href=True)
                if a_tag and "/watch?" in a_tag["href"]:
                    youtube_link = a_tag["href"]
                    if not youtube_link.startswith("http"):
                        youtube_link = "https://www.youtube.com" + youtube_link

    # Fifth fallback for YouTube link in <div class="ytp-cued-thumbnail-overlay">
    if not youtube_link:
        ytp_thumbnail_overlay_div = soup.find("div", class_="ytp-cued-thumbnail-overlay")
        if ytp_thumbnail_overlay_div:
            ytp_thumbnail_overlay_image_div = ytp_thumbnail_overlay_div.find(
                "div", class_="ytp-cued-thumbnail-overlay-image"
            )
            if (
                ytp_thumbnail_overlay_image_div
                and ytp_thumbnail_overlay_image_div.has_attr("style")
            ):
                style_content = ytp_thumbnail_overlay_image_div["style"]
                if "background-image" in style_content:
                    video_id = style_content.split("/vi/")[1].split("/")[0]
                    youtube_link = f"https://www.youtube.com/watch?v={video_id}"

    # Sixth fallback for YouTube link in <div class="youtube-player">
    if not youtube_link:
        youtube_player_div = soup.find("div", class_="youtube-player")
        if youtube_player_div:
            iframe_tag = youtube_player_div.find("iframe", src=True)
            if iframe_tag and "youtube.com/embed/" in iframe_tag["src"]:
                video_id = iframe_tag["src"].split("/embed/")[1].split("?")[0]
                youtube_link = f"https://www.youtube.com/watch?v={video_id}"

    # Seventh fallback for YouTube link in <div class="sqs-video-wrapper">
    if not youtube_link:
        sqs_video_wrapper_div = soup.find("div", class_="sqs-video-wrapper")
        if sqs_video_wrapper_div and sqs_video_wrapper_div.has_attr("data-html"):
            data_html_content = sqs_video_wrapper_div["data-html"]
            if "youtube.com/embed/" in data_html_content:
                video_id = data_html_content.split("/embed/")[1].split("?")[0]
                youtube_link = f"https://www.youtube.com/watch?v={video_id}"

    # Eighth fallback for YouTube link in <object> with <param> and <embed> tags
    if not youtube_link:
        object_tag = soup.find("object", height=True, width=True)
        if object_tag:
            param_tag = object_tag.find("param", {"name": "movie"})
            embed_tag = object_tag.find("embed", src=True)
            if param_tag and param_tag.has_attr("value"):
                video_url = param_tag["value"]
                if "youtube.com/v/" in video_url:
                    video_id = video_url.split("/v/")[1].split("?")[0]
                    youtube_link = f"https://www.youtube.com/watch?v={video_id}"
            elif embed_tag:
                video_url = embed_tag["src"]
                if "youtube.com/v/" in video_url:
                    video_id = video_url.split("/v/")[1].split("?")[0]
                    youtube_link = f"https://www.youtube.com/watch?v={video_id}"

    return youtube_link


def get_review_info(url: str, retries: int = 5, backoff_factor: int = 2) -> dict:
    """Get review information from a review page on The Needle Drop website.

    Arguments:
        url: URL of the review page.
        retries: Number of retries if the request fails.
        backoff_factor: Factor to increase the wait time between retries.

    Returns:
        A dictionary containing review information.
    """
    for attempt in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()  # Check for HTTP errors
            break  # If successful, break out of the retry loop
        except requests.exceptions.RequestException as e:
            if response.status_code == 429:
                wait_time = backoff_factor**attempt
                log.info(f"429 Too Many Requests. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                log.info(f"Request failed: {e}")
                return None
    else:
        log.info(f"Failed after {retries} attempts.")
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    # Extract title from the header
    title = None
    title_tag = soup.find("meta", property="og:title")
    if title_tag and title_tag.has_attr("content"):
        title = title_tag["content"]
    if not title:
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

    # Extract date
    date = None
    date_tag = soup.find("time", datetime=True)
    if date_tag:
        date = date_tag["datetime"]

    # Extract YouTube link
    youtube_link = extract_youtube_link(soup)

    # Extract transcript
    transcript = []
    post_content = soup.find("div", class_="post_content")
    if post_content:
        for p_tag in post_content.find_all("p"):
            transcript.append(p_tag.get_text(strip=True))

    # Extract tags from the header
    tags = []
    for meta_tag in soup.find_all("meta", property="article:tag"):
        if meta_tag.has_attr("content"):
            tags.append(meta_tag["content"])

    # Fallback for tags in the body if not found in the header
    if not tags:
        body_tag = soup.find("body")
        if body_tag and body_tag.has_attr("class"):
            tags = [
                cls.replace("tag-", "")
                for cls in body_tag["class"]
                if cls.startswith("tag-")
            ]

    review_info = {
        "url": url,
        "title": title,
        "date": date,
        "youtube_link": youtube_link,
        "transcript": transcript,
        "tags": tags,
    }

    return review_info


def retry_null_youtube_links(file_path: str) -> None:
    with open(file_path, "r") as file:
        lines = file.readlines()

    updated_reviews = []
    for line in track(lines, description="Retrying null YouTube links"):
        review_info = json.loads(line)
        if review_info["youtube_link"] is None:
            log.debug(f"Retrying YouTube link extraction for URL: {review_info['url']}")
            review_info_updated = get_review_info(review_info["url"])
            if review_info_updated and review_info_updated["youtube_link"]:
                review_info["youtube_link"] = review_info_updated["youtube_link"]
                log.debug(f"Updated YouTube link for URL: {review_info['url']}")
            else:
                log.warning(f"Could not find YouTube link for URL: {review_info['url']}")
        updated_reviews.append(review_info)

    with open(file_path, "w") as file:
        for review_info in updated_reviews:
            if review_info["youtube_link"] is not None:
                file.write(json.dumps(review_info) + "\n")

    log.info(f"Updated reviews with retried YouTube links have been saved to {file_path}")


def scrape_all_reviews(input_file: str, output_file: str, delay: int = 2) -> None:
    """Scrape review information from a list of review URLs.

    Arguments:
        input_file: Path to the file containing review URLs.
        output_file: Path to save the review information.
        delay: Delay between requests.
    """
    urls = load_urls(input_file)
    processed_urls = load_processed_urls(output_file)

    for url in track(urls, description="Scraping reviews"):
        if url in processed_urls:
            log.debug(f"Skipping already processed URL: {url}")
            continue

        log.debug(f"Scraping: {url}")
        review_info = get_review_info(url)
        if review_info:
            with open(output_file, "a") as file:
                file.write(json.dumps(review_info) + "\n")
        time.sleep(delay)  # Respect delay to avoid rate limiting

    log.info(f"Review information has been saved to {output_file}")


if __name__ == "__main__":
    input_file = "data/review_urls.txt"
    output_file = "data/review_info.jsonl"
    scrape_all_reviews(input_file, output_file, delay=2)
