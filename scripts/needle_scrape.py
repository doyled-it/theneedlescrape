import time

import requests
from bs4 import BeautifulSoup


def get_review_urls(page_url, retries=5, backoff_factor=2):
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
                return set(), None
    else:
        print(f"Failed after {retries} attempts.")
        return set(), None

    soup = BeautifulSoup(response.content, "html.parser")

    # Extract review URLs
    review_links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/articles/" in href and not any(
            exclude in href for exclude in ["#comments", "/category/", "?tag="]
        ):
            # Ensure the URL is absolute
            if not href.startswith("http"):
                href = "https://www.theneedledrop.com" + href
            review_links.add(href)

    # Find the "Older" page link
    older_page_link = soup.find("a", text="Older")
    next_page_url = older_page_link["href"] if older_page_link else None

    # Ensure the next page URL is absolute
    if next_page_url and not next_page_url.startswith("http"):
        next_page_url = "https://www.theneedledrop.com" + next_page_url

    return review_links, next_page_url


def scrape_all_reviews(start_url):
    all_review_urls = set()
    next_page_url = start_url

    while next_page_url:
        print(f"Scraping: {next_page_url}")
        review_urls, next_page_url = get_review_urls(next_page_url)
        all_review_urls.update(review_urls)
        time.sleep(2)  # Regular delay between requests

    return all_review_urls


start_url = "https://web.archive.org/web/20240706161720/https://www.theneedledrop.com/articles/category/Reviews"
all_reviews = scrape_all_reviews(start_url)

for url in all_reviews:
    print(url)

# Optionally, save the URLs to a file
with open("review_urls.txt", "w") as file:
    for url in all_reviews:
        file.write(url + "\n")
