import re
from datetime import datetime

def load_urls(file_path):
    with open(file_path, 'r') as file:
        urls = file.readlines()
    return [url.strip() for url in urls]

def extract_date(url):
    match = re.search(r'/articles/(\d{4})/(\d{1,2})/', url)
    if match:
        year, month = match.groups()
        return datetime(int(year), int(month), 1)  # Assuming the date as the first of the month
    return None

def sort_urls_by_date(urls):
    urls_with_dates = [(url, extract_date(url)) for url in urls]
    urls_with_dates = [item for item in urls_with_dates if item[1] is not None]  # Filter out URLs without valid dates
    sorted_urls_with_dates = sorted(urls_with_dates, key=lambda x: x[1])
    return [url for url, date in sorted_urls_with_dates]

def save_urls(file_path, urls):
    with open(file_path, 'w') as file:
        for url in urls:
            file.write(url + '\n')

input_file = 'review_urls.txt'
output_file = 'sorted_review_urls.txt'

urls = load_urls(input_file)
sorted_urls = sort_urls_by_date(urls)
save_urls(output_file, sorted_urls)

print(f'Sorted URLs have been saved to {output_file}')
