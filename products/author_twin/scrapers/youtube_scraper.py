import json
import random
import re
import time
from datetime import datetime
from http.cookiejar import MozillaCookieJar
from pathlib import Path

import requests
import scrapetube
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)


_RETRYABLE_STATUSES = {"blocked"}
_PERMANENT_STATUSES = {"scraped", "no_transcript", "too_short", "too_long"}

# Realistic browser user agents for rotation
_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
]

# Global cookies storage
_COOKIES = None


def _random_sleep(min_seconds=5, max_seconds=10):
    """Sleep for a random duration to mimic human behavior."""
    duration = random.uniform(min_seconds, max_seconds)
    time.sleep(duration)


def _get_random_user_agent():
    """Return a random browser user agent."""
    return random.choice(_USER_AGENTS)


def load_cookies(cookies_file_path):
    """Load cookies from JSON or Netscape format file. Call once before scraping."""
    global _COOKIES
    if not cookies_file_path or not Path(cookies_file_path).exists():
        _COOKIES = None
        return

    path = Path(cookies_file_path)

    # Try JSON format first
    if path.suffix == ".json":
        with open(path) as f:
            cookies_list = json.load(f)
            _COOKIES = {c["name"]: c["value"] for c in cookies_list if "name" in c and "value" in c}
        return

    # Try Netscape format (cookies.txt)
    try:
        jar = MozillaCookieJar(str(path))
        jar.load(ignore_discard=True, ignore_expires=True)
        _COOKIES = {cookie.name: cookie.value for cookie in jar}
    except Exception:
        _COOKIES = None


def check_time_window(time_window):
    """Check if current time is within allowed scraping window. Returns True if allowed.
    time_window: list like ["09:00", "23:00"] or None."""
    if not time_window or len(time_window) != 2:
        return True

    now = datetime.now()
    start_hour, start_min = map(int, time_window[0].split(":"))
    end_hour, end_min = map(int, time_window[1].split(":"))

    start_time = now.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
    end_time = now.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)

    return start_time <= now <= end_time


def get_channel_videos(channel_url, sort_by="newest", limit=None, sleep=1):
    """Retrieve video metadata from a YouTube channel."""
    videos = scrapetube.get_channel(
        channel_url=channel_url,
        sort_by=sort_by,
        limit=limit,
        sleep=sleep,
        content_type="videos",
    )
    return list(videos)


def get_search_videos(query, limit=50, sleep=1):
    """Search YouTube for videos matching a query."""
    videos = scrapetube.get_search(
        query=query,
        limit=limit,
        sleep=sleep,
    )
    return list(videos)


def fetch_transcript(video_id, languages=None):
    """Fetch transcript using youtube-transcript-api first, yt-dlp as fallback. Returns (status, text)."""
    if languages is None:
        languages = ["en"]

    status, text = _fetch_transcript_api(video_id, languages)
    if status == "scraped":
        return status, text

    if status == "blocked":
        fallback_status, fallback_text = _fetch_transcript_ytdlp(video_id, languages)
        if fallback_status == "scraped":
            return fallback_status, fallback_text
        return "blocked", None

    return status, text


def _fetch_transcript_api(video_id, languages):
    """Try youtube-transcript-api. Returns (status, text_or_none)."""
    ytt_api = YouTubeTranscriptApi()
    try:
        fetched = ytt_api.fetch(video_id, languages=languages)
        text = " ".join(snippet.text for snippet in fetched)
        return "scraped", text
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        return "no_transcript", None
    except Exception as e:
        error_name = type(e).__name__
        if "RequestBlocked" in error_name or "IPBlocked" in error_name:
            return "blocked", None
        return "no_transcript", None


def _fetch_transcript_ytdlp(video_id, languages):
    """Try yt-dlp subtitle extraction as fallback. Returns (status, text_or_none)."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": languages,
        "subtitlesformat": "json3",
    }

    # Add user agent and cookies for better success rate
    user_agent = _get_random_user_agent()
    opts["http_headers"] = {"User-Agent": user_agent}

    if _COOKIES:
        opts["cookiefile"] = None  # We'll pass cookies via http_headers instead
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        subs = info.get("subtitles", {})
        auto_subs = info.get("automatic_captions", {})

        subtitle_data = None
        for lang in languages:
            if lang in subs:
                subtitle_data = subs[lang]
                break
            if lang in auto_subs:
                subtitle_data = auto_subs[lang]
                break

        if not subtitle_data:
            return "no_transcript", None

        json3_url = None
        for fmt in subtitle_data:
            if fmt.get("ext") == "json3":
                json3_url = fmt.get("url")
                break

        if not json3_url:
            vtt_url = None
            for fmt in subtitle_data:
                if fmt.get("ext") == "vtt":
                    vtt_url = fmt.get("url")
                    break
            if not vtt_url:
                return "no_transcript", None

            headers = {"User-Agent": user_agent}
            resp = requests.get(vtt_url, headers=headers, cookies=_COOKIES, timeout=30)
            resp.raise_for_status()
            text = _parse_vtt_text(resp.text)
            if text:
                return "scraped", text
            return "no_transcript", None

        headers = {"User-Agent": user_agent}
        resp = requests.get(json3_url, headers=headers, cookies=_COOKIES, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        segments = data.get("events", [])
        texts = []
        for seg in segments:
            segs = seg.get("segs", [])
            for s in segs:
                t = s.get("utf8", "").strip()
                if t and t != "\n":
                    texts.append(t)

        if texts:
            return "scraped", " ".join(texts)
        return "no_transcript", None

    except Exception:
        return "blocked", None


def _parse_vtt_text(vtt_content):
    """Extract plain text from VTT subtitle content."""
    lines = vtt_content.split("\n")
    texts = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("WEBVTT"):
            continue
        if line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if "-->" in line:
            continue
        if line.isdigit():
            continue
        clean = line.replace("<c>", "").replace("</c>", "")
        clean = re.sub(r"<[^>]+>", "", clean)
        if clean.strip():
            texts.append(clean.strip())
    if texts:
        return " ".join(texts)
    return None


def _extract_video_title(video):
    """Extract title from scrapetube video dict."""
    title_data = video.get("title", {})
    if isinstance(title_data, dict):
        runs = title_data.get("runs", [])
        if runs:
            return runs[0].get("text", "untitled")
    if isinstance(title_data, str):
        return title_data
    return "untitled"


def _extract_duration_seconds(video):
    """Extract video duration in seconds from scrapetube video dict. Returns 0 if unknown."""
    length_text = video.get("lengthText", {})
    if isinstance(length_text, dict):
        simple = length_text.get("simpleText", "")
        if simple:
            return _parse_duration_string(simple)
    return 0


def _parse_duration_string(duration_str):
    """Parse a duration string like '15:43' or '1:02:30' into seconds."""
    parts = duration_str.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 1:
            return int(parts[0])
    except ValueError:
        pass
    return 0


def _sanitize_filename(text):
    """Create a safe filename from a title string."""
    safe = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in text)
    return safe.strip().replace(" ", "_")[:100].lower()


def _format_transcript_md(video_id, title, channel_name, duration_str, transcript_text):
    """Format a transcript as a markdown document."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    lines = [
        f"# {title}",
        "",
        f"**Source:** YouTube - {channel_name}",
        f"**URL:** {url}",
        f"**Video ID:** {video_id}",
        f"**Duration:** {duration_str}",
        "",
        "---",
        "",
        transcript_text,
    ]
    return "\n".join(lines)


def _should_process(video_id, scraped):
    """Check if a video should be processed based on manifest status."""
    if video_id not in scraped:
        return True
    status = scraped[video_id].get("status", "")
    return status in _RETRYABLE_STATUSES


def scan_channel(channel_config, manifest, sleep_seconds=2, sort_by="newest",
                 max_videos=None, min_duration_seconds=300, max_duration_seconds=3600):
    """Scan a channel and register all videos in the manifest (metadata only, no transcripts).
    Returns updated manifest youtube entries."""
    channel_name = channel_config["name"]
    channel_url = channel_config["url"]

    videos = get_channel_videos(
        channel_url=channel_url,
        sort_by=sort_by,
        limit=max_videos,
        sleep=sleep_seconds,
    )

    scraped = dict(manifest.get("youtube", {}))

    for video in videos:
        video_id = video.get("videoId")
        if not video_id:
            continue
        if video_id in scraped:
            existing = scraped[video_id]
            if "channel" not in existing:
                existing["channel"] = channel_name
            if "duration_seconds" not in existing:
                dur = _extract_duration_seconds(video)
                existing["duration_seconds"] = dur
                existing["duration"] = video.get("lengthText", {}).get("simpleText", "")
            continue

        title = _extract_video_title(video)
        duration_seconds = _extract_duration_seconds(video)
        duration_str = video.get("lengthText", {}).get("simpleText", "")

        if duration_seconds < min_duration_seconds:
            scraped[video_id] = {
                "title": title,
                "status": "too_short",
                "channel": channel_name,
                "duration": duration_str,
                "duration_seconds": duration_seconds,
            }
            continue

        if max_duration_seconds and duration_seconds > max_duration_seconds:
            scraped[video_id] = {
                "title": title,
                "status": "too_long",
                "channel": channel_name,
                "duration": duration_str,
                "duration_seconds": duration_seconds,
            }
            continue

        scraped[video_id] = {
            "title": title,
            "status": "pending",
            "channel": channel_name,
            "duration": duration_str,
            "duration_seconds": duration_seconds,
        }

    return scraped


def scan_search(query, manifest, sleep_seconds=2, max_results=50,
                min_duration_seconds=300, max_duration_seconds=3600):
    """Scan YouTube search results and register videos in the manifest (metadata only).
    Returns updated manifest youtube entries."""
    videos = get_search_videos(query=query, limit=max_results, sleep=sleep_seconds)

    scraped = dict(manifest.get("youtube", {}))

    for video in videos:
        video_id = video.get("videoId")
        if not video_id:
            continue
        if video_id in scraped:
            existing = scraped[video_id]
            if "duration_seconds" not in existing:
                dur = _extract_duration_seconds(video)
                existing["duration_seconds"] = dur
                existing["duration"] = video.get("lengthText", {}).get("simpleText", "")
            continue

        title = _extract_video_title(video)
        duration_seconds = _extract_duration_seconds(video)
        duration_str = video.get("lengthText", {}).get("simpleText", "")

        if duration_seconds < min_duration_seconds:
            scraped[video_id] = {
                "title": title,
                "status": "too_short",
                "channel": "YouTube Search",
                "duration": duration_str,
                "duration_seconds": duration_seconds,
                "search_query": query,
            }
            continue

        if max_duration_seconds and duration_seconds > max_duration_seconds:
            scraped[video_id] = {
                "title": title,
                "status": "too_long",
                "channel": "YouTube Search",
                "duration": duration_str,
                "duration_seconds": duration_seconds,
                "search_query": query,
            }
            continue

        scraped[video_id] = {
            "title": title,
            "status": "pending",
            "channel": "YouTube Search",
            "duration": duration_str,
            "duration_seconds": duration_seconds,
            "search_query": query,
        }

    return scraped


def scrape_pending(output_dir, manifest, languages, sleep_min_seconds=5,
                   sleep_max_seconds=10, **kwargs):
    """Scrape transcripts for all pending and blocked videos. Returns updated manifest youtube entries."""
    scraped = dict(manifest.get("youtube", {}))
    blocked_count = 0

    pending_ids = [
        vid for vid, info in scraped.items()
        if info.get("status") in {"pending", "blocked"}
    ]

    for video_id in pending_ids:
        info = scraped[video_id]
        title = info.get("title", "untitled")
        channel_name = info.get("channel", "Unknown")
        duration_str = info.get("duration", "")

        status, transcript_text = fetch_transcript(video_id, languages=languages)

        if status == "blocked":
            info["status"] = "blocked"
            blocked_count += 1
            if blocked_count >= 3:
                break
            # Longer wait after being blocked
            _random_sleep(sleep_min_seconds * 2, sleep_max_seconds * 2)
            continue

        if status == "no_transcript":
            info["status"] = "no_transcript"
            _random_sleep(sleep_min_seconds, sleep_max_seconds)
            continue

        filename = f"{video_id}_{_sanitize_filename(title)}.md"
        filepath = output_dir / filename
        content = _format_transcript_md(video_id, title, channel_name, duration_str, transcript_text)
        filepath.write_text(content)
        info["status"] = "scraped"
        info["file"] = filename
        blocked_count = 0

        # Random sleep between successful requests
        _random_sleep(sleep_min_seconds, sleep_max_seconds)

    return scraped
