#!/bin/bash
# Auto-scrape: runs the author-twin scraper, then regenerates the report.
# Schedule with cron or launchd to retry blocked videos periodically.
#
# Usage:
#   # One-shot:
#   ./products/author_twin/claude/auto_scrape.sh daniel_priestley
#
#   # Loop mode (runs every 2 hours until killed):
#   ./products/author_twin/claude/auto_scrape.sh daniel_priestley --loop
#
#   # Add to crontab (every 2 hours, 9am-11pm):
#   crontab -e
#   0 9,11,13,15,17,19,21,23 * * * cd /Users/faconcha/Documents/Bison/the-ai-first-co && ./products/author_twin/claude/auto_scrape.sh daniel_priestley >> /tmp/author_twin_scrape.log 2>&1

set -e

AUTHOR="${1:?Usage: auto_scrape.sh <author_slug> [--loop]}"
LOOP_MODE="${2:-}"
PROJECT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
INTERVAL=7200  # 2 hours in seconds

cd "$PROJECT_DIR"

run_scrape() {
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') - Starting scrape for $AUTHOR ==="
    uv run python main.py author-twin scrape --author "$AUTHOR"
    uv run python main.py author-twin report --author "$AUTHOR"

    # Print summary
    uv run python -c "
import json
with open('products/author_twin/authors/${AUTHOR}/manifest.json') as f:
    m = json.load(f)
yt = m.get('youtube', {})
scraped = sum(1 for v in yt.values() if v.get('status') == 'scraped')
blocked = sum(1 for v in yt.values() if v.get('status') == 'blocked')
print(f'  Scraped: {scraped} | Blocked (pending): {blocked} | Total: {len(yt)}')
if blocked == 0:
    print('  All videos processed!')
"
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') - Scrape complete ==="
}

if [ "$LOOP_MODE" = "--loop" ]; then
    echo "Loop mode: will run every $(($INTERVAL / 3600)) hours. Ctrl+C to stop."
    while true; do
        run_scrape
        REMAINING=$(uv run python -c "
import json
with open('products/author_twin/authors/${AUTHOR}/manifest.json') as f:
    m = json.load(f)
blocked = sum(1 for v in m.get('youtube',{}).values() if v.get('status')=='blocked')
print(blocked)
")
        if [ "$REMAINING" = "0" ]; then
            echo "All videos scraped. Exiting loop."
            break
        fi
        echo "Sleeping ${INTERVAL}s ($(($INTERVAL / 3600))h) before next run..."
        sleep $INTERVAL
    done
else
    run_scrape
fi
