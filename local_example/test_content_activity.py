"""
Local example: Test _detect_content_activity from marketing_detector.

Searches Google via DataForSEO for 'site:{domain} inurl:blog' to detect
blog activity and extract blog page URLs.

Env vars required: DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD (or DATAFORSEO_API_KEY)
"""

import json

from dotenv import load_dotenv

from products.b2b_outreach.signals import marketing_detector

load_dotenv()


def main():
    domain = "falabella.com"
    location_code = 2152
    language_code = "es"

    print(f"Detecting content activity for '{domain}' (location={location_code}, lang={language_code})...\n")

    result = marketing_detector._detect_content_activity(
        domain=domain,
        location_code=location_code,
        language_code=language_code,
    )

    print("=== ContentResult (model) ===")
    print(f"  blog_pages:     {result.blog_pages:,}")
    print(f"  blog_activity:  {result.blog_activity}")
    print(f"  blog_urls:      ({len(result.blog_urls)} URLs)")
    for url in result.blog_urls:
        print(f"    - {url}")
    print(f"  note:           {result.note}")

    print("\n=== Full JSON ===")
    print(json.dumps(result.model_dump(mode='json'), indent=2))


if __name__ == "__main__":
    main()
