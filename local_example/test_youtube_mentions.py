"""
Local example: Test _search_youtube_mentions from marketing_detector.

Calls the YouTube Data API v3 (search + videos.list) for "Falabella"
(last 30 days) and prints engagement stats + estimated media value.

Env var required: YOUTUBE_API_KEY
"""

import json

from dotenv import load_dotenv

from products.b2b_outreach.signals import marketing_detector

load_dotenv()


def main():
    company = "Falabella"
    region = "CL"

    print(f"Searching YouTube mentions for '{company}' (region={region})...\n")

    result = marketing_detector._search_youtube_mentions(
        company_name=company,
        region_code=region,
    )

    print("=== YouTubeResult (model) ===")
    print(f"  total_results:              {result.total_results:,}")
    print(f"  total_views:                {result.total_views:,}")
    print(f"  total_likes:                {result.total_likes:,}")
    print(f"  total_comments:             {result.total_comments:,}")
    print(f"  estimated_media_value_usd:  ${result.estimated_media_value_usd:,.2f}")
    print(f"  note:                       {result.note}")

    print("\n=== Full JSON ===")
    print(json.dumps(result.model_dump(mode='json'), indent=2))


if __name__ == "__main__":
    main()
