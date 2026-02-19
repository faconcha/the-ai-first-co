"""
Local example: Test _detect_seo_performance from marketing_detector.

Calls DataForSEO Labs API (ranked_keywords organic) for falabella.com
to get organic traffic, organic traffic value (USD), and top keywords.

Env vars required: DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD
"""

import json

from dotenv import load_dotenv

from products.b2b_outreach.signals import marketing_detector

load_dotenv()


def main():
    domain = "falabella.com"
    location_code = 2152
    language_code = "es"

    print(f"Detecting SEO performance for '{domain}' (location={location_code}, lang={language_code})...\n")

    result = marketing_detector._detect_seo_performance(
        domain=domain,
        location_code=location_code,
        language_code=language_code,
    )

    print("=== SEOResult (model) ===")
    print(f"  organic_traffic:           {result.organic_traffic:,.1f}")
    print(f"  organic_traffic_value_usd: ${result.organic_traffic_value_usd:,.2f}")
    print(f"  keywords_count:            {result.keywords_count:,}")
    print(f"  top_keywords:              {result.top_keywords}")
    print(f"  note:                      {result.note}")

    print("\n=== Full JSON ===")
    print(json.dumps(result.model_dump(mode='json'), indent=2))


if __name__ == "__main__":
    main()
