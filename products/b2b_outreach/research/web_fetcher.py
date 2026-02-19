"""
Web Fetcher
============

Fetch and extract text content from web pages using requests + BeautifulSoup.
"""

import requests
import bs4
from typing import Optional
from urllib.parse import urljoin


_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


def fetch_page_content(url, timeout=30):
    """
    Fetch a web page and extract its text content.

    Args:
        url: Full URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Extracted text content as string, or None if failed.
    """
    try:
        response = requests.get(url, headers=_DEFAULT_HEADERS, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException:
        return None

    soup = bs4.BeautifulSoup(response.text, "html.parser")

    # Strip non-content elements to reduce noise for LLM processing
    for tag in soup.find_all(["script", "style", "nav", "footer", "iframe", "noscript"]):
        tag.decompose()

    parts = []

    # Extract page metadata (title and meta description)
    title_tag = soup.find("title")
    if title_tag:
        parts.append(f"Title: {title_tag.get_text(strip=True)}")

    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        parts.append(f"Description: {meta_tag['content']}")

    # Extract headings as structural markers
    for heading in soup.find_all(["h1", "h2", "h3"]):
        text = heading.get_text(strip=True)
        if text:
            parts.append(f"\n## {text}")

    # Extract body text from the main content area, filtering short fragments
    content_element = soup.find("article") or soup.find("main") or soup.find("body")
    if content_element:
        for p in content_element.find_all(["p", "li"]):
            text = p.get_text(strip=True)
            if text and len(text) > 20:
                parts.append(text)

    return "\n".join(parts) if parts else None


def fetch_multiple_pages(domain, pages, timeout=30):
    """
    Fetch content from multiple pages of a website.

    Args:
        domain: Base domain (e.g., 'example.com' or 'https://example.com').
        pages: List of page paths (e.g., ['/', '/about', '/products']).
        timeout: Request timeout in seconds per page.

    Returns:
        Dictionary mapping page path to extracted text content.
    """
    if not domain.startswith(("http://", "https://")):
        domain = f"https://{domain}"

    content_map = {}

    for page in pages:
        full_url = urljoin(domain, page)
        content = fetch_page_content(full_url, timeout=timeout)
        if content:
            content_map[page] = content

    return content_map
