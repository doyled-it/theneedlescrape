from pathlib import Path

import typer
from typing_extensions import Annotated

from .scraping.reparse import reparse_reviews
from .scraping.reviews import retry_null_youtube_links, scrape_all_reviews
from .scraping.web import remove_duplicates, scrape_all_urls
from .scraping.youtube import update_reviews_with_youtube_details
from .utils.logger import create_logger

app = typer.Typer(
    help=(
        "[green]TheNeedleScrape[/green]: A CLI for scraping data from The Needle Drop "
        "website and YouTube channel."
    ),
    add_completion=False,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    rich_markup_mode="rich",
)

scrape = typer.Typer(
    help="Scrape from different data sources.",
    add_completion=False,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)

log = create_logger(__name__)


@app.callback(
    no_args_is_help=True,
)
def callback():
    """
    TheNeedleScrape: A CLI for scraping data from The Needle Drop website and YouTube
    channel.
    """
    pass


@scrape.command(
    "links",
    help="Scrape a list of the review URLs.",
    context_settings={"help_option_names": ["-h", "--help"]},
)
def links(
    start_page: Annotated[
        int, typer.Option(help="Page number to start scraping from.")
    ] = 1,
    max_pages: Annotated[
        int, typer.Option(help="Maximum page number to attempt scraping.")
    ] = 1000,
    delay: Annotated[int, typer.Option(help="Delay between requests.")] = 2,
    output_file: Annotated[
        Path, typer.Option(help="Path to save the review URLs.")
    ] = Path("data/review_urls.txt"),
) -> None:
    """Scrape a list of the review URLs from The Needle Drop website.

    Arguments:

    """
    scrape_all_urls(
        start_page=start_page, max_pages=max_pages, delay=delay, output_file=output_file
    )
    remove_duplicates(output_file, output_file)


@scrape.command(
    "reviews",
    help=(
        "Scrape the review data from each of the review pages. Must run `tns scrape "
        "links` first."
    ),
    context_settings={"help_option_names": ["-h", "--help"]},
)
def reviews(
    input_file: Annotated[
        str,
        typer.Option(
            "--input-file", "-i", help="Path to the file containing review URLs."
        ),
    ] = "data/unique_review_urls.txt",
    output_file: Annotated[
        str,
        typer.Option(
            "--output-file",
            "-o",
            help="Path to save the review data (JSON Lines [.jsonl]).",
        ),
    ] = "data/review_info.jsonl",
    delay: Annotated[
        int, typer.Option("--delay", "-d", help="Delay between requests.")
    ] = 2,
) -> None:
    """Scrape a list of the review URLs from The Needle Drop website.

    Arguments:
        input_file: Path to the file containing review URLs.
        output_file: Path to save the review data.
        delay: Delay between requests
    """
    scrape_all_reviews(input_file=input_file, output_file=output_file, delay=delay)
    retry_null_youtube_links(output_file)


@scrape.command(
    "youtube",
    help=(
        "Scrape the review data from each of the reviews' YouTube Videos. Must run `tns "
        "scrape reviews` first."
    ),
    context_settings={"help_option_names": ["-h", "--help"]},
)
def youtube(
    input_file: Annotated[
        str,
        typer.Option(
            "--input-file",
            "-i",
            help="Path to the file containing review JSON Lines data.",
        ),
    ] = "data/review_info.jsonl",
    output_file: Annotated[
        str,
        typer.Option(
            "--output-file",
            "-o",
            help="Path to save the review & YouTube data (JSON Lines [.jsonl]).",
        ),
    ] = "data/updated_review_info.jsonl",
) -> None:
    """Scrape a list of the review URLs from The Needle Drop website.

    Arguments:
        input_file: Path to the file containing review URLs.
        output_file: Path to save the review data.
    """
    update_reviews_with_youtube_details(input_file, output_file)
    reparse_reviews(output_file, output_file)


app.add_typer(scrape, name="scrape")

if __name__ == "__main__":
    app()
