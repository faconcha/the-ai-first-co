# Author Twin

Scrapes an author's publicly available content (YouTube videos, web articles) and builds a markdown knowledge base.

## Current Author: Daniel Priestley

**Sources:**
- YouTube channel: Daniel Priestley (18 videos)
- YouTube channel: Key Person of Influence (662 videos, 280 eligible)
- YouTube search: interviews, keynotes, podcasts (86 videos, 74 eligible)
- Web: danielpriestley.com book/product pages (6 pages)

**Filtering:** Only videos between 5-60 minutes are scraped (394 too short, 58 too long excluded).

## Commands

### Claude Code skill (recommended)

```
/scrape-author daniel_priestley
```

### Scrape content (scan + transcript + web + report)

```bash
uv run python main.py author-twin scrape --author daniel_priestley
```

Each run:
1. Scans channels/search for new videos (fast, no rate limit)
2. Fetches transcripts for pending/blocked videos (rate limited by YouTube)
3. Scrapes web URLs
4. Generates report

### Generate report only

```bash
uv run python main.py author-twin report --author daniel_priestley
```

### Automated scraping (loop every 2 hours)

```bash
./products/author_twin/auto_scrape.sh daniel_priestley --loop
```

### Automated scraping (cron, every 2 hours 9am-11pm)

```bash
crontab -e
# Add:
0 9,11,13,15,17,19,21,23 * * * cd /Users/faconcha/Documents/Bison/the-ai-first-co && ./products/author_twin/auto_scrape.sh daniel_priestley >> /tmp/author_twin_scrape.log 2>&1
```

### One-shot run

```bash
./products/author_twin/auto_scrape.sh daniel_priestley
```

## How It Works

- **manifest.json** tracks every video ID with status, title, channel, duration
- Statuses: `scraped`, `pending`, `blocked` (retry), `too_short` (<5 min), `too_long` (>60 min), `no_transcript`
- Incremental: re-running only processes pending/blocked videos
- Rate limit handling: stops after 3 consecutive blocks, retries on next run
- Fallback: uses `yt-dlp` when `youtube-transcript-api` is blocked

## Output

- `knowledge/youtube/` — one .md per video transcript
- `knowledge/web/` — one .md per web article
- `report.md` — detailed scraping progress report
- `manifest.json` — source of truth for all tracked resources

## Tools Used (all free, no API keys)

- `scrapetube` — YouTube channel/search video listing
- `youtube-transcript-api` — YouTube transcript extraction
- `yt-dlp` — fallback transcript extraction
- `requests` + `beautifulsoup4` — web page scraping
