import time

import requests
from bs4 import BeautifulSoup
from rich import print

from tns.utils.progress import track


def get_review_urls(page_url: str, retries: int = 5, backoff_factor: int = 2) -> set:
    for attempt in range(retries):
        try:
            response = requests.get(page_url)
            response.raise_for_status()  # Check for HTTP errors
            break  # If successful, break out of the retry loop
        except requests.exceptions.RequestException as e:
            if response.status_code == 429:
                wait_time = backoff_factor**attempt
                print(f"429 Too Many Requests. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Request failed: {e}")
                return set()
    else:
        print(f"Failed after {retries} attempts.")
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
    output_file: str = "review_urls.txt",
) -> set:
    all_review_urls = set()

    with open(output_file, "a") as file:
        for page_number in track(
            range(start_page, max_pages + 1), description="Scraping Pages"
        ):
            page_url = f"https://theneedledrop.com/album-reviews/page/{page_number}/"
            print(f"Scraping: {page_url}")

            review_urls = get_review_urls(page_url)
            if not review_urls:
                print("No more review URLs found or request failed.")
                break

            new_urls = review_urls - all_review_urls
            for url in new_urls:
                file.write(url + "\n")

            all_review_urls.update(new_urls)
            time.sleep(delay)  # Regular delay between requests

    return all_review_urls


if __name__ == "__main__":
    scrape_all_urls(
        start_page=206, max_pages=300, delay=2, output_file="data/new_review_urls.txt"
    )
