import json
from pathlib import Path

import yaml

from products.author_twin.scrapers import youtube_scraper
from products.author_twin.scrapers import web_scraper
from products.author_twin.claude import report


AUTHORS_DIR = Path(__file__).resolve().parent.parent / "authors"

MIN_DURATION_SECONDS = 300   # 5 minutes
MAX_DURATION_SECONDS = 3600  # 60 minutes


def load_author_config(author_slug):
    """Load an author's config.yaml."""
    config_path = AUTHORS_DIR / author_slug / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_manifest(author_slug):
    """Load or initialize the scraping manifest."""
    manifest_path = AUTHORS_DIR / author_slug / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, "r") as f:
            return json.load(f)
    return {"youtube": {}, "web": {}}


def save_manifest(author_slug, manifest):
    """Persist the scraping manifest."""
    manifest_path = AUTHORS_DIR / author_slug / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


def run_scrape(author_slug):
    """Run the full scraping pipeline for an author.
    Phase 1: Scan channels/search to discover videos (metadata only, no rate limit risk).
    Phase 2: Scrape transcripts for pending/blocked videos (rate limited).
    Phase 3: Scrape web URLs.
    Phase 4: Generate report.
    """
    config = load_author_config(author_slug)
    manifest = load_manifest(author_slug)

    scraping_config = config.get("scraping", {})
    sleep_min = scraping_config.get("sleep_min_seconds", 5)
    sleep_max = scraping_config.get("sleep_max_seconds", 10)
    sort_by = scraping_config.get("youtube_sort_by", "newest")
    max_videos = scraping_config.get("max_videos_per_channel")
    max_search = scraping_config.get("max_search_results", 50)
    cookies_file = scraping_config.get("cookies_file")
    time_window = scraping_config.get("time_window")

    # Load cookies if provided
    if cookies_file:
        cookies_path = AUTHORS_DIR / author_slug / cookies_file
        youtube_scraper.load_cookies(str(cookies_path))

    # Check time window
    if not youtube_scraper.check_time_window(time_window):
        print(f"Outside scraping time window {time_window}. Skipping.")
        return

    youtube_config = config.get("youtube", {})
    languages = youtube_config.get("transcript_languages", ["en"])

    # For scanning (metadata only), use average sleep
    scan_sleep = (sleep_min + sleep_max) / 2

    # Phase 1: Scan channels and search (metadata only, fast)
    for channel in youtube_config.get("channels", []):
        manifest["youtube"] = youtube_scraper.scan_channel(
            channel_config=channel,
            manifest=manifest,
            sleep_seconds=scan_sleep,
            sort_by=sort_by,
            max_videos=max_videos,
            min_duration_seconds=MIN_DURATION_SECONDS,
            max_duration_seconds=MAX_DURATION_SECONDS,
        )
        save_manifest(author_slug, manifest)

    for query in youtube_config.get("search_queries", []):
        manifest["youtube"] = youtube_scraper.scan_search(
            query=query,
            manifest=manifest,
            sleep_seconds=scan_sleep,
            max_results=max_search,
            min_duration_seconds=MIN_DURATION_SECONDS,
            max_duration_seconds=MAX_DURATION_SECONDS,
        )
        save_manifest(author_slug, manifest)

    # Phase 2: Scrape transcripts for pending/blocked videos (with randomized sleep)
    yt_output_dir = AUTHORS_DIR / author_slug / "knowledge" / "youtube"
    yt_output_dir.mkdir(parents=True, exist_ok=True)

    manifest["youtube"] = youtube_scraper.scrape_pending(
        output_dir=yt_output_dir,
        manifest=manifest,
        languages=languages,
        sleep_min_seconds=sleep_min,
        sleep_max_seconds=sleep_max,
    )
    save_manifest(author_slug, manifest)

    # Phase 3: Web content
    web_config = config.get("web", {})
    web_output_dir = AUTHORS_DIR / author_slug / "knowledge" / "web"
    web_output_dir.mkdir(parents=True, exist_ok=True)

    web_urls = web_config.get("urls", [])
    if web_urls:
        manifest["web"] = web_scraper.scrape_urls(
            urls=web_urls,
            output_dir=web_output_dir,
            manifest=manifest,
            sleep_seconds=sleep_min,  # Use minimum for web scraping
        )
        save_manifest(author_slug, manifest)

    # Phase 4: Report
    report.generate_report(author_slug)
