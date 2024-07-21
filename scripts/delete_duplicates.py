from tns.utils.progress import track


def remove_duplicates(input_file: str, output_file: str) -> None:
    with open(input_file, "r") as file:
        urls = file.readlines()

    # Remove duplicates by converting the list to a set, then back to a list
    unique_urls = list(set(url.strip() for url in urls))

    # Sort the unique URLs (optional, but helps with readability)
    unique_urls.sort()

    with open(output_file, "w") as file:
        for url in track(unique_urls, description="Writing URLs"):
            file.write(url + "\n")

    print(f"Removed duplicates. {len(unique_urls)} unique URLs written to {output_file}")


if __name__ == "__main__":
    input_file = "data/new_review_urls.txt"
    output_file = "data/unique_review_urls.txt"
    remove_duplicates(input_file, output_file)
