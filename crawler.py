"""Educational crawler to extract a web page and save it as JSON."""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


USER_AGENT = "ChronosCrawler/1.0 (educational crawler; personal use)"
TIMEOUT = 20


def normalize_url(url):
    """Remove the fragment (#...) and surrounding whitespace from a URL."""
    url = (url or "").strip()
    url, _fragment = urldefrag(url)
    return url


def extract_page(url):
    """Download an HTTP(S) page and return its data as a dictionary.

    Return None if a network error occurs or if the URL is not HTTP(S).
    """
    url = normalize_url(url)
    parsed_url = urlparse(url)

    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        print(
            "Error: The URL must start with http:// or https://.",
            file=sys.stderr,
        )
        return None

    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en,fr;q=0.8",
    }

    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.RequestException as error:
        print(f"Download error: {error}", file=sys.stderr)
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    title = soup.title.get_text(" ", strip=True) if soup.title else ""

    h1_titles = [
        element.get_text(" ", strip=True)
        for element in soup.find_all("h1")
        if element.get_text(" ", strip=True)
    ]

    # On Wikipedia, limit extraction to the main article.
    # On other websites, use the document body when available.
    content = (
        soup.select_one("main#content")
        or soup.select_one("main")
        or soup.select_one("article")
        or soup.body
        or soup
    )

    paragraphs = []

    for element in content.find_all("p"):
        text = re.sub(r"\s+", " ", element.get_text(" ", strip=True)).strip()

        if text:
            paragraphs.append(text)

    page_domain = urlparse(response.url).netloc.lower()

    links = []
    seen_urls = set()

    for element in content.find_all("a", href=True):
        href = element.get("href", "").strip()

        if not href or href.startswith(
            ("#", "javascript:", "mailto:", "tel:", "data:")
        ):
            continue

        link_url = normalize_url(urljoin(response.url, href))
        parsed_link = urlparse(link_url)

        if parsed_link.scheme not in {"http", "https"} or not parsed_link.netloc:
            continue

        url_key = link_url.lower()

        if url_key in seen_urls:
            continue

        seen_urls.add(url_key)

        link_text = re.sub(
            r"\s+", " ", element.get_text(" ", strip=True)
        ).strip()

        link_type = (
            "internal"
            if parsed_link.netloc.lower() == page_domain
            else "external"
        )

        links.append({
            "text": link_text,
            "url": link_url,
            "type": link_type,
        })

    internal_links = [link for link in links if link["type"] == "internal"]
    external_links = [link for link in links if link["type"] == "external"]

    return {
        "schema_version": 1,
        "source_url": response.url,
        "extraction_date": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "title": title,
        "h1_titles": h1_titles,
        "paragraphs": paragraphs,
        "links": links,
        "internal_links": internal_links,
        "external_links": external_links,
        "paragraph_count": len(paragraphs),
        "link_count": len(links),
        "internal_link_count": len(internal_links),
        "external_link_count": len(external_links),
    }


def filename_from_url(url):
    """Generate a simple filename from the last URL path segment."""
    segment = urlparse(url).path.rstrip("/").split("/")[-1] or "web_page"
    segment = re.sub(r"[^a-zA-Z0-9_-]+", "_", segment).strip("_").lower()

    return f"{segment or 'web_page'}.json"


def main():
    parser = argparse.ArgumentParser(
        description="Extract a web page into a Chronos JSON file."
    )

    parser.add_argument(
        "url",
        nargs="?",
        default="https://en.wikipedia.org/wiki/Mansa_Musa",
        help="HTTP(S) URL to extract",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output JSON file path",
    )

    args = parser.parse_args()

    result = extract_page(args.url)

    if result is None:
        raise SystemExit(1)

    output_path = (
        Path(args.output)
        if args.output
        else Path(filename_from_url(result["source_url"]))
    )

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)
            file.write("\n")

    except OSError as error:
        raise SystemExit(f"Unable to save the JSON file: {error}")

    print("===== CRAWL SUMMARY =====")
    print("Source URL:", result["source_url"])
    print("Title:", result["title"])
    print("Paragraphs:", result["paragraph_count"])
    print("Links:", result["link_count"])
    print("Internal links:", result["internal_link_count"])
    print("External links:", result["external_link_count"])
    print("JSON file:", output_path.resolve())


if __name__ == "__main__":
    main()