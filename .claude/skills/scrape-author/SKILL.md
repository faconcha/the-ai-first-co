---
name: scrape-author
description: Run the author-twin scraping pipeline for a given author
argument-hint: <author_slug>
disable-model-invocation: true
allowed-tools:
  - Bash(uv run python:*)
  - Bash(./products/author_twin/claude/auto_scrape.sh:*)
  - Read
  - Glob
---

Run the author-twin scraping pipeline for the author: $ARGUMENTS

Steps:
1. Verify the author config exists at `products/author_twin/authors/$ARGUMENTS/config.yaml`. If it doesn't exist, tell the user and stop.
2. Run the full scraping pipeline:
   ```bash
   uv run python main.py author-twin scrape --author $ARGUMENTS
   ```
3. After scraping completes, read the generated report at `products/author_twin/authors/$ARGUMENTS/report.md` and show a summary to the user with:
   - Total videos found vs scraped vs pending
   - Duration filter applied (5-60 minutes)
   - Per-channel breakdown
   - Knowledge base stats (files, word count)
   - Web pages scraped
4. If there are still pending/blocked videos, remind the user they can run this skill again later or use the auto-scrape loop:
   ```bash
   ./products/author_twin/claude/auto_scrape.sh $ARGUMENTS --loop
   ```
