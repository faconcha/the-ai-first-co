"""
Local example: Test detect_all_signals for Falabella (Chile).

Runs the full signal detection pipeline: Google Ads, LinkedIn Jobs,
YouTube, SEO, and Content. Meta Ads is skipped (pending API approval).

Env vars required:
    DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD (or DATAFORSEO_API_KEY)
    YOUTUBE_API_KEY
"""

import json
import os

from dotenv import load_dotenv

from products.b2b_outreach.signals import marketing_detector

load_dotenv()

# Ensure Meta Ads is skipped (pending approval)
os.environ.pop("META_ACCESS_TOKEN", None)


def main():
    company_name = "Falabella"
    domain = "falabella.com"
    location_config = marketing_detector.location_config_for_country("CL")

    print(f"Running detect_all_signals for '{company_name}' ({domain})")
    print(f"Location config: {json.dumps(location_config, indent=2)}")
    print("=" * 60)

    signals, raw_signals = marketing_detector.detect_all_signals(
        company_name=company_name,
        domain=domain,
        include_extended=True,
        location_config=location_config,
    )

    # --- CompanySignals summary (what the LLM sees) ---
    print("\n" + "=" * 60)
    print("COMPANY SIGNALS (LLM-facing summary)")
    print("=" * 60)

    print("\n--- Ads ---")
    print(f"  active_campaigns:       {signals.ads.active_campaigns}")
    print(f"  platforms:              {signals.ads.platforms}")
    print(f"  themes:                 {signals.ads.themes}")
    print(f"  paid_keywords_count:    {signals.ads.paid_keywords_count}")
    print(f"  estimated_paid_traffic: {signals.ads.estimated_paid_traffic:,.1f}")
    print(f"  estimated_paid_cost:    ${signals.ads.estimated_paid_cost_usd:,.2f}")
    print(f"  paid_search_ratio:      {signals.ads.paid_search_ratio:.3f}")
    print(f"  ad_count (meta):        {signals.ads.ad_count}")

    print("\n--- Growth ---")
    print(f"  hiring_velocity:        {signals.growth.hiring_velocity}")
    print(f"  roles:                  {signals.growth.roles[:5]}")
    print(f"  marketing_hiring:       {signals.growth.marketing_hiring}")
    print(f"  marketing_roles:        {signals.growth.marketing_roles[:5]}")

    print("\n--- Social (YouTube) ---")
    print(f"  youtube_video_estimate: {signals.social.youtube_video_estimate}")
    print(f"  youtube_total_views:    {signals.social.youtube_total_views:,}")
    print(f"  youtube_total_likes:    {signals.social.youtube_total_likes:,}")
    print(f"  youtube_total_comments: {signals.social.youtube_total_comments:,}")

    if signals.seo:
        print("\n--- SEO ---")
        print(f"  organic_traffic:        {signals.seo.organic_traffic:,.1f}")
        print(f"  organic_traffic_value:  ${signals.seo.organic_traffic_value_usd:,.2f}")
        print(f"  keywords_count:         {signals.seo.keywords_count:,}")
        print(f"  top_keywords:           {signals.seo.top_keywords}")
    else:
        print("\n--- SEO: not collected ---")

    if signals.content:
        print("\n--- Content ---")
        print(f"  blog_pages:             {signals.content.blog_pages}")
        print(f"  blog_activity:          {signals.content.blog_activity}")
    else:
        print("\n--- Content: not collected ---")

    print(f"\n--- Total DataForSEO API cost: ${signals.total_api_cost:.4f} ---")

    # --- Raw signals (what gets saved to individual JSON files) ---
    print("\n" + "=" * 60)
    print("RAW SIGNALS (per-source JSON files)")
    print("=" * 60)

    raw_dict = raw_signals.model_dump(mode='json')
    for signal_name, signal_data in raw_dict.items():
        if signal_data is not None:
            print(f"\n--- {signal_name}.json ---")
            print(json.dumps(signal_data, indent=2))

    # --- Full CompanySignals JSON ---
    print("\n" + "=" * 60)
    print("FULL 02_signals.json (CompanySignals)")
    print("=" * 60)
    print(json.dumps(signals.model_dump(mode='json'), indent=2))


if __name__ == "__main__":
    main()
