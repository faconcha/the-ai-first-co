import json
from datetime import datetime
from pathlib import Path

import yaml


AUTHORS_DIR = Path(__file__).resolve().parent.parent / "authors"


def generate_report(author_slug):
    """Generate a detailed markdown report of the scraping results."""
    author_dir = AUTHORS_DIR / author_slug
    config_path = author_dir / "config.yaml"
    manifest_path = author_dir / "manifest.json"

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    if not manifest_path.exists():
        return

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    author_name = config.get("name", author_slug)
    youtube_data = manifest.get("youtube", {})
    web_data = manifest.get("web", {})

    yt_scraped = {k: v for k, v in youtube_data.items() if v.get("status") == "scraped"}
    yt_pending = {k: v for k, v in youtube_data.items() if v.get("status") == "pending"}
    yt_blocked = {k: v for k, v in youtube_data.items() if v.get("status") == "blocked"}
    yt_no_transcript = {k: v for k, v in youtube_data.items() if v.get("status") == "no_transcript"}
    yt_too_short = {k: v for k, v in youtube_data.items() if v.get("status") == "too_short"}
    yt_too_long = {k: v for k, v in youtube_data.items() if v.get("status") == "too_long"}
    web_scraped = {k: v for k, v in web_data.items() if v.get("status") == "scraped"}
    web_failed = {k: v for k, v in web_data.items() if v.get("status") == "failed"}
    web_insufficient = {k: v for k, v in web_data.items() if v.get("status") == "insufficient_content"}

    to_scrape = len(yt_pending) + len(yt_blocked)
    total_words, total_files = _count_knowledge_stats(author_dir / "knowledge")

    # Count per-channel stats
    channel_stats = {}
    for info in youtube_data.values():
        ch = info.get("channel", "Unknown")
        if ch not in channel_stats:
            channel_stats[ch] = {"total": 0, "scraped": 0, "pending": 0, "blocked": 0, "too_short": 0, "too_long": 0, "no_transcript": 0}
        channel_stats[ch]["total"] += 1
        status = info.get("status", "")
        if status in channel_stats[ch]:
            channel_stats[ch][status] += 1

    lines = []
    lines.append(f"# Scraping Report: {author_name}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| YouTube videos found | {len(youtube_data)} |")
    lines.append(f"| YouTube transcripts scraped | {len(yt_scraped)} |")
    lines.append(f"| YouTube pending (to scrape) | {len(yt_pending)} |")
    lines.append(f"| YouTube blocked (will retry) | {len(yt_blocked)} |")
    lines.append(f"| YouTube too short (<5 min) | {len(yt_too_short)} |")
    lines.append(f"| YouTube too long (>60 min) | {len(yt_too_long)} |")
    lines.append(f"| YouTube no transcript available | {len(yt_no_transcript)} |")
    lines.append(f"| **YouTube remaining to scrape** | **{to_scrape}** |")
    lines.append(f"| Web URLs attempted | {len(web_data)} |")
    lines.append(f"| Web pages scraped | {len(web_scraped)} |")
    lines.append(f"| Web pages failed | {len(web_failed)} |")
    lines.append(f"| Web pages insufficient content | {len(web_insufficient)} |")
    lines.append(f"| Total knowledge files | {total_files} |")
    lines.append(f"| Total word count | {total_words:,} |")
    lines.append(f"| Estimated reading time | {total_words // 250} min |")
    lines.append("")

    if channel_stats:
        lines.append("## Per-Channel Breakdown")
        lines.append("")
        lines.append("| Channel | Total | Scraped | Pending | Blocked | Too Short | Too Long | No Transcript |")
        lines.append("|---------|-------|---------|---------|---------|-----------|----------|---------------|")
        for ch, stats in sorted(channel_stats.items()):
            lines.append(f"| {ch} | {stats['total']} | {stats['scraped']} | {stats['pending']} | {stats['blocked']} | {stats['too_short']} | {stats['too_long']} | {stats['no_transcript']} |")
        lines.append("")

    if yt_scraped:
        lines.append("## YouTube Transcripts Scraped")
        lines.append("")
        lines.append("| Video ID | Title | Channel | Duration | File |")
        lines.append("|----------|-------|---------|----------|------|")
        for vid, info in sorted(yt_scraped.items(), key=lambda x: x[1].get("title", "")):
            title = info.get("title", "")
            channel = info.get("channel", "")
            duration = info.get("duration", "")
            filename = info.get("file", "")
            lines.append(f"| {vid} | {title} | {channel} | {duration} | {filename} |")
        lines.append("")

    if yt_pending or yt_blocked:
        lines.append("## YouTube Videos To Scrape (Pending + Blocked)")
        lines.append("")
        lines.append(f"{to_scrape} videos remaining. Run the scraper again to continue.")
        lines.append("")
        lines.append("| Video ID | Title | Channel | Duration | Status |")
        lines.append("|----------|-------|---------|----------|--------|")
        combined = {**yt_pending, **yt_blocked}
        for vid, info in sorted(combined.items(), key=lambda x: x[1].get("title", "")):
            title = info.get("title", "")
            channel = info.get("channel", "")
            duration = info.get("duration", "")
            status = info.get("status", "")
            lines.append(f"| {vid} | {title} | {channel} | {duration} | {status} |")
        lines.append("")

    if yt_too_short:
        lines.append("## YouTube Videos Skipped (Too Short)")
        lines.append("")
        lines.append(f"{len(yt_too_short)} videos under 5 minutes, excluded from scraping.")
        lines.append("")
        lines.append("| Video ID | Title | Channel | Duration |")
        lines.append("|----------|-------|---------|----------|")
        for vid, info in sorted(yt_too_short.items(), key=lambda x: x[1].get("title", "")):
            title = info.get("title", "")
            channel = info.get("channel", "")
            duration = info.get("duration", "")
            lines.append(f"| {vid} | {title} | {channel} | {duration} |")
        lines.append("")

    if yt_too_long:
        lines.append("## YouTube Videos Skipped (Too Long)")
        lines.append("")
        lines.append(f"{len(yt_too_long)} videos over 60 minutes, excluded from scraping.")
        lines.append("")
        lines.append("| Video ID | Title | Channel | Duration |")
        lines.append("|----------|-------|---------|----------|")
        for vid, info in sorted(yt_too_long.items(), key=lambda x: x[1].get("title", "")):
            title = info.get("title", "")
            channel = info.get("channel", "")
            duration = info.get("duration", "")
            lines.append(f"| {vid} | {title} | {channel} | {duration} |")
        lines.append("")

    if yt_no_transcript:
        lines.append("## YouTube Videos Without Transcripts")
        lines.append("")
        lines.append("| Video ID | Title | Channel | Duration |")
        lines.append("|----------|-------|---------|----------|")
        for vid, info in sorted(yt_no_transcript.items(), key=lambda x: x[1].get("title", "")):
            title = info.get("title", "")
            channel = info.get("channel", "")
            duration = info.get("duration", "")
            lines.append(f"| {vid} | {title} | {channel} | {duration} |")
        lines.append("")

    if web_scraped:
        lines.append("## Web Pages Scraped")
        lines.append("")
        lines.append("| URL | Title | File |")
        lines.append("|-----|-------|------|")
        for url, info in sorted(web_scraped.items()):
            title = info.get("title", "")
            filename = info.get("file", "")
            lines.append(f"| {url} | {title} | {filename} |")
        lines.append("")

    if web_failed or web_insufficient:
        lines.append("## Web Pages Not Scraped")
        lines.append("")
        lines.append("| URL | Status |")
        lines.append("|-----|--------|")
        for url, info in sorted({**web_failed, **web_insufficient}.items()):
            status = info.get("status", "unknown")
            lines.append(f"| {url} | {status} |")
        lines.append("")

    report_content = "\n".join(lines)
    report_path = author_dir / "report.md"
    report_path.write_text(report_content)

    return report_path


def _count_knowledge_stats(knowledge_dir):
    """Count total files and words across all knowledge .md files."""
    total_words = 0
    total_files = 0

    if not knowledge_dir.exists():
        return total_words, total_files

    for md_file in knowledge_dir.rglob("*.md"):
        total_files += 1
        text = md_file.read_text()
        total_words += len(text.split())

    return total_words, total_files
