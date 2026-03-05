"""
Local example: Test _search_youtube_mentions for Falabella.

Runs just the YouTube private function to inspect raw results.

Env var required: YOUTUBE_API_KEY
"""

import json

from dotenv import load_dotenv

from products.b2b_outreach.signals import marketing_detector

load_dotenv()


def main():
    company_name = "Falabella"
    region_code = "CL"

    print(f"Running _search_youtube_mentions for '{company_name}' (region={region_code})")
    print("=" * 60)

    result = marketing_detector._search_youtube_mentions(company_name, region_code=region_code)

    print(json.dumps(result.model_dump(mode='json'), indent=2))


if __name__ == "__main__":
    main()
