import time
from pathlib import Path
from urllib.parse import urlparse

import requests
import bs4


_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


def fetch_page(url, timeout=30):
    """Fetch a web page and return its HTML. Returns None on failure."""
    try:
        response = requests.get(url, headers=_DEFAULT_HEADERS, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        return None


def extract_article_content(html, url):
    """Extract meaningful text content from an HTML page."""
    soup = bs4.BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)

    content_element = soup.find("article")
    if content_element is None:
        content_element = soup.find("main")
    if content_element is None:
        content_element = soup.find("body")

    text = ""
    if content_element:
        text = content_element.get_text(separator="\n", strip=True)

    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_desc = meta_tag.get("content", "")

    return {
        "title": title,
        "text": text,
        "meta_description": meta_desc,
        "url": url,
    }


def _sanitize_filename(text):
    """Create a safe filename from a string."""
    safe = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in text)
    return safe.strip().replace(" ", "_")[:100].lower()


def _format_article_md(title, url, meta_description, text):
    """Format article content as markdown."""
    domain = urlparse(url).netloc
    lines = [
        f"# {title}",
        "",
        f"**Source:** {domain}",
        f"**URL:** {url}",
    ]
    if meta_description:
        lines.append(f"**Description:** {meta_description}")
    lines.extend([
        "",
        "---",
        "",
        text,
    ])
    return "\n".join(lines)


def scrape_urls(urls, output_dir, manifest, sleep_seconds=2):
    """Scrape a list of URLs and save as markdown files. Returns updated manifest web entries."""
    scraped = dict(manifest.get("web", {}))

    for url in urls:
        if url in scraped and scraped[url].get("status") == "scraped":
            continue

        html = fetch_page(url)
        if html is None:
            scraped[url] = {"status": "failed", "url": url}
            continue

        article = extract_article_content(html, url)

        if not article["text"] or len(article["text"]) < 100:
            scraped[url] = {"status": "insufficient_content", "url": url}
            continue

        title = article["title"] or urlparse(url).path.strip("/").split("/")[-1]
        filename = f"{_sanitize_filename(title)}.md"
        filepath = output_dir / filename

        content = _format_article_md(
            title=article["title"],
            url=url,
            meta_description=article["meta_description"],
            text=article["text"],
        )
        filepath.write_text(content)

        scraped[url] = {
            "title": article["title"],
            "status": "scraped",
            "file": filename,
        }

        time.sleep(sleep_seconds)

    return scraped
