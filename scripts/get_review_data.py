import json
import random
import time

import requests
from bs4 import BeautifulSoup
from rich import print
from rich.progress import track


def load_urls(file_path):
    with open(file_path, "r") as file:
        urls = file.readlines()
    return [url.strip() for url in urls]


def load_existing_data(output_file):
    existing_data = {}
    try:
        with open(output_file, "r") as file:
            for line in file:
                review_info = json.loads(line.strip())
                existing_data[review_info["url"]] = review_info
    except FileNotFoundError:
        pass
    return existing_data


def scrape_review_info(url, delay, output_file):
    retries = 5
    backoff_factor = 2

    for attempt in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()  # Check for HTTP errors
            break  # If successful, break out of the retry loop
        except requests.exceptions.RequestException as e:
            if response.status_code == 429:  # Too Many Requests
                wait_time = backoff_factor**attempt
                print(f"429 Error. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Request failed: {e}")
                return None

    if response is None:
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    # Extract title and date
    header = soup.find("header", class_="entry-header")
    if not header:
        print(f"No header found for URL: {url}")
        return None

    title_tag = header.find("h1", class_="entry-title")
    if not title_tag:
        print(f"No title found for URL: {url}")
        return None

    title = title_tag.get_text(strip=True)

    date_tag = header.find("time", class_="entry-header-date")
    if not date_tag:
        print(f"No date found for URL: {url}")
        return None

    date = date_tag.get_text(strip=True)

    # Extract tags
    tags_section = soup.find("span", class_="entry-tags")
    tags = (
        [tag.get_text(strip=True) for tag in tags_section.find_all("a")]
        if tags_section
        else []
    )

    # Extract YouTube link
    youtube_section = soup.find("div", class_="sqs-html-content")
    if youtube_section is None:
        youtube_section = soup.find("div", class_="html5-video-container")
    youtube_link = None
    if youtube_section:
        embed_tag = youtube_section.find("embed")
        a_tag = youtube_section.find("a", class_="ytp-title-link yt-uix-sessionlink")
        if embed_tag and "src" in embed_tag.attrs:
            youtube_link = embed_tag.attrs["src"]
        else:
            youtube_link = a_tag.attrs["href"]

    review_info = {
        "url": url,
        "title": title,
        "date": date,
        "tags": tags,
        "youtube_link": youtube_link,
    }

    # Append the result to the output file
    with open(output_file, "a") as file:
        file.write(json.dumps(review_info) + "\n")

    time.sleep(delay)  # Respect delay to avoid rate limiting


def scrape_all_reviews(urls, existing_data, output_file, delay=2):
    urls_to_scrape = [url for url in urls if url not in existing_data]
    print(f"Total URLs to scrape: {len(urls_to_scrape)}")

    for url in track(urls_to_scrape, description="Scraping reviews"):
        scrape_review_info(url, delay, output_file)


input_file = "data/sorted_review_urls.txt"
output_file = "data/review_info.jsonl"

urls = load_urls(input_file)
existing_data = load_existing_data(output_file)

scrape_all_reviews(urls, existing_data, output_file, delay=2)

print(f"Review information has been saved to {output_file}")
