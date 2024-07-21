import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from ..utils.logger import create_logger
from ..utils.progress import track

log = create_logger(__name__)


def get_review_urls(page_url: str, retries: int = 5, backoff_factor: int = 2) -> set:
    """Get review URLs from a page on The Needle Drop website.

    Arguments:
        page_url: URL of the page to scrape.
        retries: Number of retries if the request fails.
        backoff_factor: Factor to increase the wait time between retries.

    Returns:
        A set of review URLs.
    """
    for attempt in range(retries):
        try:
            response = requests.get(page_url)
            response.raise_for_status()  # Check for HTTP errors
            break  # If successful, break out of the retry loop
        except requests.exceptions.RequestException as e:
            if response.status_code == 429:
                wait_time = backoff_factor**attempt
                log.warning(f"429 Too Many Requests. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            elif response.status_code == 404:
                log.warning("404 Not Found. No more pages to scrape.")
                return set()
            else:
                log.error(f"Request failed: {e}")
                return set()
    else:
        log.error(f"Failed after {retries} attempts.")
        return set()

    soup = BeautifulSoup(response.content, "html.parser")

    # Extract review URLs
    review_links = set()
    for div in soup.find_all("div", class_="title_holder"):
        a_tag = div.find("a", href=True)
        if a_tag:
            href = a_tag["href"]
            if not href.startswith("http"):
                href = "https://theneedledrop.com" + href
            review_links.add(href)

    return review_links


def scrape_all_urls(
    start_page: int = 1,
    max_pages: int = 1000,
    delay: int = 2,
    output_file: Path = Path("data/review_urls.txt"),
) -> set:
    """Scrape review URLs from multiple pages on The Needle Drop website.

    Arguments:
        start_page: Page number to start scraping from.
        max_pages: Maximum number of pages to scrape.
        delay: Delay between requests.
        output_file: File to write the review URLs.

    Returns:
        A set of all review URLs scraped
    """
    all_review_urls = set()

    output_file = Path(output_file)
    # Create parent directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "a") as file:
        for page_number in track(
            range(start_page, max_pages + 1), description="Scraping Pages"
        ):
            page_url = f"https://theneedledrop.com/album-reviews/page/{page_number}/"
            log.debug(f"Scraping: {page_url}")

            review_urls = get_review_urls(page_url)
            if not review_urls:
                log.warning("No more review URLs found or request failed.")
                break

            new_urls = review_urls - all_review_urls
            for url in new_urls:
                file.write(url + "\n")

            all_review_urls.update(new_urls)
            time.sleep(delay)  # Regular delay between requests

    return all_review_urls


def remove_duplicates(input_file: Path, output_file: Path) -> None:
    """Remove duplicate URLs from a file.

    Arguments:
        input_file: File containing URLs with duplicates.
        output_file: File to write the unique URLs
    """
    with open(input_file, "r") as file:
        urls = file.readlines()

    # Remove duplicates by converting the list to a set, then back to a list
    unique_urls = list(set(url.strip() for url in urls))

    # Sort the unique URLs (optional, but helps with readability)
    unique_urls.sort()

    # Create parent directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as file:
        for url in unique_urls:
            file.write(url + "\n")

    log.info(
        f"Removed duplicates. {len(unique_urls)} unique URLs written to {output_file}"
    )
