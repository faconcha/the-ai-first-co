"""
Marketing Signal Detector
=========================

Detects marketing signals using public APIs and web scraping.
Each private function queries a specific data source and returns a dict
with normalized signal data. The orchestrator `detect_all_signals` combines
them into a CompanySignals object.

Location/language parameters default to values in b2b_outreach.yaml but can
be overridden per-call to support Latam, Europe, or other regions.
"""

import os
import re
import base64
import yaml
import logging
import requests
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta

from products.b2b_outreach import models

logger = logging.getLogger("b2b_outreach.signals")

# ISO country code → DataForSEO location_code + language/news parameters.
# Used by location_config_for_country() to auto-configure signal detection
# based on the company's country from research (Step 1).
COUNTRY_LOCATION_MAP = {
    # North America
    "US": {"location_code": 2840, "language_code": "en", "country_code": "US", "ad_reached_countries": "US", "news_hl": "en-US", "news_gl": "US", "news_ceid": "US:en"},
    # Latam — Spanish-speaking
    "MX": {"location_code": 2484, "language_code": "es", "country_code": "MX", "ad_reached_countries": "MX", "news_hl": "es-419", "news_gl": "MX", "news_ceid": "MX:es"},
    "CO": {"location_code": 2170, "language_code": "es", "country_code": "CO", "ad_reached_countries": "CO", "news_hl": "es-419", "news_gl": "CO", "news_ceid": "CO:es"},
    "AR": {"location_code": 2032, "language_code": "es", "country_code": "AR", "ad_reached_countries": "AR", "news_hl": "es-419", "news_gl": "AR", "news_ceid": "AR:es"},
    "CL": {"location_code": 2152, "language_code": "es", "country_code": "CL", "ad_reached_countries": "CL", "news_hl": "es-419", "news_gl": "CL", "news_ceid": "CL:es"},
    "PE": {"location_code": 2604, "language_code": "es", "country_code": "PE", "ad_reached_countries": "PE", "news_hl": "es-419", "news_gl": "PE", "news_ceid": "PE:es"},
    "EC": {"location_code": 2218, "language_code": "es", "country_code": "EC", "ad_reached_countries": "EC", "news_hl": "es-419", "news_gl": "EC", "news_ceid": "EC:es"},
    "VE": {"location_code": 2862, "language_code": "es", "country_code": "VE", "ad_reached_countries": "VE", "news_hl": "es-419", "news_gl": "VE", "news_ceid": "VE:es"},
    "UY": {"location_code": 2858, "language_code": "es", "country_code": "UY", "ad_reached_countries": "UY", "news_hl": "es-419", "news_gl": "UY", "news_ceid": "UY:es"},
    "PY": {"location_code": 2600, "language_code": "es", "country_code": "PY", "ad_reached_countries": "PY", "news_hl": "es-419", "news_gl": "PY", "news_ceid": "PY:es"},
    "BO": {"location_code": 2068, "language_code": "es", "country_code": "BO", "ad_reached_countries": "BO", "news_hl": "es-419", "news_gl": "BO", "news_ceid": "BO:es"},
    "DO": {"location_code": 2214, "language_code": "es", "country_code": "DO", "ad_reached_countries": "DO", "news_hl": "es-419", "news_gl": "DO", "news_ceid": "DO:es"},
    "CR": {"location_code": 2188, "language_code": "es", "country_code": "CR", "ad_reached_countries": "CR", "news_hl": "es-419", "news_gl": "CR", "news_ceid": "CR:es"},
    "PA": {"location_code": 2591, "language_code": "es", "country_code": "PA", "ad_reached_countries": "PA", "news_hl": "es-419", "news_gl": "PA", "news_ceid": "PA:es"},
    "GT": {"location_code": 2320, "language_code": "es", "country_code": "GT", "ad_reached_countries": "GT", "news_hl": "es-419", "news_gl": "GT", "news_ceid": "GT:es"},
    "HN": {"location_code": 2340, "language_code": "es", "country_code": "HN", "ad_reached_countries": "HN", "news_hl": "es-419", "news_gl": "HN", "news_ceid": "HN:es"},
    "SV": {"location_code": 2222, "language_code": "es", "country_code": "SV", "ad_reached_countries": "SV", "news_hl": "es-419", "news_gl": "SV", "news_ceid": "SV:es"},
    "NI": {"location_code": 2558, "language_code": "es", "country_code": "NI", "ad_reached_countries": "NI", "news_hl": "es-419", "news_gl": "NI", "news_ceid": "NI:es"},
    "CU": {"location_code": 2192, "language_code": "es", "country_code": "CU", "ad_reached_countries": "CU", "news_hl": "es-419", "news_gl": "CU", "news_ceid": "CU:es"},
    "PR": {"location_code": 2630, "language_code": "es", "country_code": "PR", "ad_reached_countries": "PR", "news_hl": "es-419", "news_gl": "PR", "news_ceid": "PR:es"},
    # Latam — Portuguese
    "BR": {"location_code": 2076, "language_code": "pt", "country_code": "BR", "ad_reached_countries": "BR", "news_hl": "pt-BR", "news_gl": "BR", "news_ceid": "BR:pt-419"},
    # Europe
    "ES": {"location_code": 2724, "language_code": "es", "country_code": "ES", "ad_reached_countries": "ES", "news_hl": "es", "news_gl": "ES", "news_ceid": "ES:es"},
    "GB": {"location_code": 2826, "language_code": "en", "country_code": "GB", "ad_reached_countries": "GB", "news_hl": "en-GB", "news_gl": "GB", "news_ceid": "GB:en"},
    "DE": {"location_code": 2276, "language_code": "de", "country_code": "DE", "ad_reached_countries": "DE", "news_hl": "de", "news_gl": "DE", "news_ceid": "DE:de"},
    "FR": {"location_code": 2250, "language_code": "fr", "country_code": "FR", "ad_reached_countries": "FR", "news_hl": "fr", "news_gl": "FR", "news_ceid": "FR:fr"},
}


# Country name → ISO code. Accepts English and Spanish names.
COUNTRY_NAME_TO_CODE = {
    "united states": "US", "estados unidos": "US", "usa": "US",
    "mexico": "MX", "méxico": "MX",
    "colombia": "CO",
    "argentina": "AR",
    "chile": "CL",
    "peru": "PE", "perú": "PE",
    "ecuador": "EC",
    "venezuela": "VE",
    "uruguay": "UY",
    "paraguay": "PY",
    "bolivia": "BO",
    "dominican republic": "DO", "república dominicana": "DO", "republica dominicana": "DO",
    "costa rica": "CR",
    "panama": "PA", "panamá": "PA",
    "guatemala": "GT",
    "honduras": "HN",
    "el salvador": "SV",
    "nicaragua": "NI",
    "cuba": "CU",
    "puerto rico": "PR",
    "brazil": "BR", "brasil": "BR",
    "spain": "ES", "españa": "ES", "espana": "ES",
    "united kingdom": "GB", "uk": "GB", "gran bretaña": "GB",
    "germany": "DE", "alemania": "DE",
    "france": "FR", "francia": "FR",
}


def location_config_for_country(country: str) -> Optional[Dict]:
    """Return location config for a country name or ISO code.

    Accepts ISO 2-letter codes ('CL'), full names in English ('Chile'),
    or full names in Spanish ('chile'). Case-insensitive.

    Returns None if the country is not recognized, so the caller
    can fall back to YAML defaults.
    """
    if not country:
        return None
    value = country.strip().upper()
    # Try as ISO code first
    if value in COUNTRY_LOCATION_MAP:
        return COUNTRY_LOCATION_MAP[value]
    # Try as country name
    code = COUNTRY_NAME_TO_CODE.get(country.strip().lower())
    if code:
        return COUNTRY_LOCATION_MAP[code]
    return None


def _get_dataforseo_auth() -> Tuple[Optional[str], Optional[str]]:
    """Resolve DataForSEO credentials.

    Checks DATAFORSEO_API_KEY (base64-encoded login:password) first,
    then falls back to separate DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD.
    """
    api_key = os.getenv('DATAFORSEO_API_KEY')
    if api_key:
        decoded = base64.b64decode(api_key).decode('utf-8')
        login, password = decoded.split(':', 1)
        return login, password

    return os.getenv('DATAFORSEO_LOGIN'), os.getenv('DATAFORSEO_PASSWORD')


def _load_config() -> Dict:
    """Load b2b_outreach.yaml configuration."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "config",
        "b2b_outreach.yaml"
    )
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Advertising & Social signals (Google Ads, Meta Ads, LinkedIn Jobs, YouTube)
# ---------------------------------------------------------------------------


def _search_google_ads_transparency(
    domain: str,
    location_code: int = 2840,
    language_code: str = "en",
    max_keywords: int = 5,
) -> models.GoogleAdsResult:
    """Detect whether a domain invests in Google Ads using DataForSEO ranked_keywords.

    Data Source: DataForSEO Labs > Google > Ranked Keywords (paid)
    API docs: https://docs.dataforseo.com/v3/dataforseo_labs-google-ranked_keywords-live/

    How it works:
        Queries the domain filtered to item_types=["paid"] to retrieve only
        keywords where the domain appears in paid SERP results. This proves
        the company is actively bidding on Google Ads, and reveals which
        keywords they target (brand, product, competitor).

    Args:
        domain: Company domain (e.g., 'falabella.com').
        location_code: DataForSEO location code (default 2840 = US).
        language_code: ISO language code (default 'en').
        max_keywords: Maximum number of top paid keywords to include in the result.

    Returns:
        dict with keys: has_ads (bool), platforms (list), keywords (list),
        paid_keywords_count (int), estimated_paid_traffic (float),
        estimated_paid_cost_usd (float).

    Limitations:
        - Only captures keywords currently in DataForSEO's index.
        - Does not include display or YouTube ad campaigns.
        - Requires paid DataForSEO API access.

    Env vars required: DATAFORSEO_API_KEY (or DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD)
    """
    login, password = _get_dataforseo_auth()

    if not login or not password:
        return models.GoogleAdsResult(note='DataForSEO credentials not configured')

    try:
        url = "https://api.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live"
        auth = requests.auth.HTTPBasicAuth(login, password)

        payload = [{
            "target": domain,
            "location_code": location_code,
            "language_code": language_code,
            "item_types": ["paid"],
            "limit": max_keywords,
            "order_by": ["keyword_data.keyword_info.search_volume,desc"],
        }]

        response = requests.post(url, json=payload, auth=auth, timeout=30)

        if response.status_code == 200:
            data = response.json()

            if data.get('status_code') == 20000 and data.get('tasks'):
                task = data['tasks'][0]
                task_cost = task.get('cost', 0)
                if task.get('result'):
                    result = task['result'][0]
                    total_count = result.get('total_count', 0)

                    if total_count > 0:
                        paid_metrics = result.get('metrics', {}).get('paid', {})
                        items = result.get('items', [])

                        keywords = [
                            item.get('keyword_data', {}).get('keyword', '')
                            for item in items
                        ]

                        return models.GoogleAdsResult(
                            has_ads=True,
                            platforms=['google'],
                            keywords=keywords,
                            paid_keywords_count=total_count,
                            estimated_paid_traffic=round(paid_metrics.get('etv', 0), 1),
                            estimated_paid_cost_usd=round(paid_metrics.get('estimated_paid_traffic_cost', 0), 1),
                            api_cost=task_cost,
                        )

                return models.GoogleAdsResult(api_cost=task_cost)

        return models.GoogleAdsResult()

    except Exception as e:
        logger.error("Error checking Google Ads via DataForSEO: %s", e)
        return models.GoogleAdsResult()


def _search_meta_ads_library(
    company_name: str,
    ad_reached_countries: str = "US",
    max_ads_to_analyze: int = 5,
) -> models.MetaAdsResult:
    """Search Meta Ad Library API for active Facebook/Instagram ads.

    Data Source: Meta Ad Library API (free, public)
    API docs: https://www.facebook.com/ads/library/api/

    How it works:
        Searches for active ads matching the company name. Collects
        publishing platforms (facebook, instagram, etc.) and ad copy snippets
        from the top results.

    Args:
        company_name: Company name to search for.
        ad_reached_countries: ISO country code for ad targeting (default 'US').
        max_ads_to_analyze: Maximum ads to inspect for platform/theme data.

    Returns:
        dict with keys: has_ads (bool), platforms (list), themes (list), count (int).

    Limitations:
        - Search is by company name string, may match unrelated advertisers.
        - Only returns active ads, not historical.

    Env vars required: META_ACCESS_TOKEN
    """
    access_token = os.getenv('META_ACCESS_TOKEN')

    if not access_token:
        return models.MetaAdsResult(note='META_ACCESS_TOKEN not configured')

    try:
        url = "https://graph.facebook.com/v19.0/ads_archive"

        params = {
            'access_token': access_token,
            'search_terms': company_name,
            'ad_reached_countries': ad_reached_countries,
            'ad_active_status': 'ACTIVE',
            'limit': 10
        }

        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()
            ads = data.get('data', [])

            if ads:
                platforms = set()
                themes = []

                for ad in ads[:max_ads_to_analyze]:
                    publisher = ad.get('publisher_platform', [])
                    if isinstance(publisher, list):
                        platforms.update(publisher)

                    snippet = ad.get('ad_creative_body', '')
                    if snippet:
                        themes.append(snippet[:100])

                return models.MetaAdsResult(
                    has_ads=True,
                    platforms=list(platforms),
                    themes=themes,
                    count=len(ads),
                )

        return models.MetaAdsResult()

    except Exception as e:
        logger.error("Error checking Meta Ad Library: %s", e)
        return models.MetaAdsResult()


def _search_linkedin_jobs(
    company_name: str,
    location_code: int = 2840,
    language_code: str = "en",
    hiring_velocity_cap: int = 50,
) -> models.LinkedInJobsResult:
    """Detect hiring velocity and marketing hiring intent via Google-indexed LinkedIn jobs.

    Data Source: DataForSEO SERP API > Google Organic
    API docs: https://docs.dataforseo.com/v3/serp-se-type-live-regular/

    How it works:
        Runs two Google searches scoped to linkedin.com/jobs:
        1. General: total job count for the company (growth signal).
        2. Marketing-filtered: jobs matching marketing/growth/digital keywords
           (buying intent signal — the company is building a marketing team).

    Args:
        company_name: Company name to search for.
        location_code: DataForSEO location code (default 2840 = US).
        language_code: ISO language code (default 'en').
        hiring_velocity_cap: Maximum hiring velocity value to return (caps outliers).

    Returns:
        dict with keys:
            hiring_velocity (int): Total open positions.
            roles (list[str]): Sample role names from descriptions.
            marketing_hiring (bool): True if hiring marketing/growth/digital roles.
            marketing_roles (list[str]): Specific marketing-related roles found.
            source (str): Data source identifier.

    Env vars required: DATAFORSEO_API_KEY (or DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD)
    """
    login, password = _get_dataforseo_auth()

    if not login or not password:
        return models.LinkedInJobsResult(note='DataForSEO credentials not configured')

    try:
        url = "https://api.dataforseo.com/v3/serp/google/organic/live/regular"
        auth = requests.auth.HTTPBasicAuth(login, password)

        # Search 1: total job count
        general_keyword = f'site:linkedin.com/jobs "{company_name}"'
        payload = [{
            "keyword": general_keyword,
            "location_code": location_code,
            "language_code": language_code,
            "depth": 10,
        }]

        response = requests.post(url, json=payload, auth=auth, timeout=30)

        job_count = 0
        roles = []
        total_cost = 0.0
        if response.status_code == 200:
            data = response.json()
            if data.get('status_code') == 20000 and data.get('tasks'):
                task = data['tasks'][0]
                total_cost += task.get('cost', 0)
                result = (task.get('result') or [{}])[0]
                items = result.get('items') or []

                for item in items:
                    if item.get('type') != 'organic':
                        continue
                    title = item.get('title', '')
                    match = re.search(r'([\d.,]+)\+?\s+(?:empleos?|jobs?)', title, re.IGNORECASE)
                    if match:
                        num_str = match.group(1).replace('.', '').replace(',', '')
                        parsed = int(num_str)
                        if parsed > job_count:
                            job_count = parsed

                    description = item.get('description', '') or ''
                    role_matches = re.findall(r'·\s*([^·\n]{5,60}?)(?:\s*·|\s*$)', description)
                    for role in role_matches[:3]:
                        cleaned = role.strip()
                        if cleaned and cleaned not in roles:
                            roles.append(cleaned)

        # Search 2: marketing/growth/digital roles (buying intent signal)
        marketing_keyword = (
            f'site:linkedin.com/jobs "{company_name}" '
            f'(marketing OR growth OR digital OR SEO OR SEM '
            f'OR "redes sociales" OR "social media" OR "paid media" '
            f'OR "performance" OR "contenido" OR "content")'
        )
        payload_mkt = [{
            "keyword": marketing_keyword,
            "location_code": location_code,
            "language_code": language_code,
            "depth": 10,
        }]

        response_mkt = requests.post(url, json=payload_mkt, auth=auth, timeout=30)

        marketing_hiring = False
        marketing_roles = []
        if response_mkt.status_code == 200:
            data_mkt = response_mkt.json()
            if data_mkt.get('status_code') == 20000 and data_mkt.get('tasks'):
                task_mkt = data_mkt['tasks'][0]
                total_cost += task_mkt.get('cost', 0)
                result_mkt = (task_mkt.get('result') or [{}])[0]
                items_mkt = result_mkt.get('items') or []

                for item in items_mkt:
                    if item.get('type') != 'organic':
                        continue
                    # Individual job pages have the role in the title
                    # Format: "Role Name - Company Name" or "Role Name - Location"
                    title = item.get('title', '')
                    role = title.split(' - ')[0].strip() if ' - ' in title else ''
                    # Skip aggregate listing pages ("1.000 empleos de ...")
                    if role and not re.search(r'\d+\s+(?:empleos?|jobs?)', role, re.IGNORECASE):
                        if role not in marketing_roles:
                            marketing_roles.append(role)

                marketing_hiring = len(marketing_roles) > 0

        return models.LinkedInJobsResult(
            hiring_velocity=min(job_count, hiring_velocity_cap),
            roles=roles[:10],
            marketing_hiring=marketing_hiring,
            marketing_roles=marketing_roles[:10],
            source='dataforseo_serp_linkedin',
            api_cost=total_cost,
        )

    except Exception as e:
        logger.error("Error checking LinkedIn jobs via DataForSEO: %s", e)
        return models.LinkedInJobsResult()


def _search_youtube_mentions(
    company_name: str,
    region_code: str = "US",
) -> models.YouTubeResult:
    """Detect YouTube brand mentions and engagement in the last 30 days.

    Data Source: YouTube Data API v3 (Search + Videos endpoints)
    API docs:
        - https://developers.google.com/youtube/v3/docs/search/list
        - https://developers.google.com/youtube/v3/docs/videos/list

    How it works:
        1. search.list — finds videos mentioning the company (last 30 days).
           Returns total_results (YouTube's estimate) and up to 10 video IDs.
        2. videos.list — fetches viewCount, likeCount, commentCount for those
           video IDs in a single batch call.

    Args:
        company_name: Company name to search for.
        region_code: ISO country code for regional results (default 'US').

    Returns:
        YouTubeResult with total_results and engagement stats.

    API quota cost: 100 units (search) + 1 unit (videos) = 101 units per call.
    Free tier: 10,000 units/day → ~99 calls/day.

    Limitations:
        - Only searches video titles/descriptions, not transcripts.
        - Results may include unrelated videos matching the company name.
        - Stats are sampled from the top 10 results, not the full total_results.

    Env vars required: YOUTUBE_API_KEY
    """
    api_key = os.getenv('YOUTUBE_API_KEY')

    if not api_key:
        return models.YouTubeResult(note='YOUTUBE_API_KEY not configured')

    try:
        # Step 1: Search for videos mentioning the brand (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat() + 'Z'

        search_params = {
            'part': 'id',
            'q': company_name,
            'type': 'video',
            'publishedAfter': thirty_days_ago,
            'regionCode': region_code,
            'maxResults': 50,
            'key': api_key,
        }

        search_resp = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params=search_params, timeout=15,
        )

        if search_resp.status_code == 403:
            return models.YouTubeResult(note='YouTube API quota exceeded or invalid key')

        if search_resp.status_code != 200:
            return models.YouTubeResult(note=f'YouTube search API returned {search_resp.status_code}')

        search_data = search_resp.json()
        total_results = search_data.get('pageInfo', {}).get('totalResults', 0)
        items = search_data.get('items', [])

        if not items:
            return models.YouTubeResult(total_results=total_results)

        # Step 2: Fetch engagement stats for the returned video IDs
        video_ids = ','.join(item['id']['videoId'] for item in items)

        stats_params = {
            'part': 'statistics',
            'id': video_ids,
            'key': api_key,
        }

        stats_resp = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params=stats_params, timeout=15,
        )

        total_views = 0
        total_likes = 0
        total_comments = 0

        if stats_resp.status_code == 200:
            for video in stats_resp.json().get('items', []):
                stats = video.get('statistics', {})
                total_views += int(stats.get('viewCount', 0))
                total_likes += int(stats.get('likeCount', 0))
                total_comments += int(stats.get('commentCount', 0))

        return models.YouTubeResult(
            total_results=total_results,
            total_views=total_views,
            total_likes=total_likes,
            total_comments=total_comments,
        )

    except Exception as e:
        logger.error("Error checking YouTube: %s", e)

    return models.YouTubeResult()


# ---------------------------------------------------------------------------
# Extended signals (SEO, Content, Prospection, Funding, News, Intent)
# ---------------------------------------------------------------------------


def _detect_seo_performance(
    domain: str,
    location_code: int = 2840,
    language_code: str = "en",
    max_top_keywords: int = 5,
) -> models.SEOResult:
    """Detect organic search performance using DataForSEO ranked_keywords.

    Data Source: DataForSEO Labs > Google > Ranked Keywords (organic)
    API docs: https://docs.dataforseo.com/v3/dataforseo_labs-google-ranked_keywords-live/

    How it works:
        Same endpoint as _search_google_ads_transparency but filtered to
        item_types=["organic"]. Returns the domain's organic keyword rankings,
        estimated organic traffic, and crucially the organic_traffic_value_usd:
        what the company would have to pay in Google Ads to get this traffic.

        Combined with paid traffic from _search_google_ads_transparency, this
        enables computing paid_search_ratio in detect_all_signals.

    Args:
        domain: Company domain (e.g., 'falabella.com').
        location_code: DataForSEO location code (default 2840 = US).
        language_code: ISO language code (default 'en').
        max_top_keywords: Maximum top keywords to include in the result.

    Returns:
        SEOResult with organic_traffic_volume, organic_traffic_value_usd,
        keywords_count, and top_keywords.

    Env vars required: DATAFORSEO_API_KEY (or DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD)
    """
    login, password = _get_dataforseo_auth()

    if not login or not password:
        return models.SEOResult(note='DATAFORSEO credentials not configured')

    try:
        url = "https://api.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live"
        auth = requests.auth.HTTPBasicAuth(login, password)

        payload = [{
            "target": domain,
            "location_code": location_code,
            "language_code": language_code,
            "item_types": ["organic"],
            "limit": max_top_keywords,
            "order_by": ["keyword_data.keyword_info.search_volume,desc"],
        }]

        response = requests.post(url, json=payload, auth=auth, timeout=30)

        if response.status_code == 200:
            data = response.json()

            if data.get('status_code') == 20000 and data.get('tasks'):
                task = data['tasks'][0]
                task_cost = task.get('cost', 0)
                if task.get('result'):
                    result = task['result'][0]
                    total_count = result.get('total_count', 0)

                    organic_metrics = result.get('metrics', {}).get('organic', {})
                    items = result.get('items', [])

                    top_keywords = [
                        item.get('keyword_data', {}).get('keyword', '')
                        for item in items
                    ]

                    return models.SEOResult(
                        organic_traffic_volume=round(organic_metrics.get('etv', 0), 1),
                        organic_traffic_value_usd=round(organic_metrics.get('estimated_paid_traffic_cost', 0), 1),
                        keywords_count=total_count,
                        top_keywords=top_keywords,
                        keywords_is_new=organic_metrics.get('is_new', 0),
                        keywords_is_up=organic_metrics.get('is_up', 0),
                        keywords_is_down=organic_metrics.get('is_down', 0),
                        keywords_is_lost=organic_metrics.get('is_lost', 0),
                        api_cost=task_cost,
                    )

                return models.SEOResult(api_cost=task_cost)

        return models.SEOResult()

    except Exception as e:
        logger.error("Error detecting SEO performance: %s", e)
        return models.SEOResult()


def _detect_content_activity(
    domain: str,
    location_code: int = 2840,
    language_code: str = "en",
) -> models.ContentResult:
    """Detect blog activity using DataForSEO SERP API.

    Data Source: DataForSEO SERP > Google > Organic/Live/Regular
    API docs: https://docs.dataforseo.com/v3/serp-se-type-live-regular/

    How it works:
        Searches Google for 'site:{domain} inurl:blog' to find indexed blog
        pages. Returns se_results_count (Google's total blog page estimate)
        plus actual URLs from the top 10 results.

        The raw result (blog_urls) goes into the JSON file for detailed review.
        The summary signal (blog_pages + blog_activity) is what the LLM sees.

    Args:
        domain: Company domain (e.g., 'falabella.com').
        location_code: DataForSEO location code (default 2840 = US).
        language_code: ISO language code (default 'en').

    Returns:
        ContentResult with blog_pages, blog_activity, and blog_urls.

    Env vars required: DATAFORSEO_API_KEY (or DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD)
    """
    login, password = _get_dataforseo_auth()

    if not login or not password:
        return models.ContentResult(note='DATAFORSEO credentials not configured')

    try:
        url = "https://api.dataforseo.com/v3/serp/google/organic/live/regular"
        auth = requests.auth.HTTPBasicAuth(login, password)

        payload = [{
            "keyword": f"site:{domain} inurl:blog",
            "location_code": location_code,
            "language_code": language_code,
            "depth": 10,
        }]

        response = requests.post(url, json=payload, auth=auth, timeout=30)

        blog_pages = 0
        blog_urls = []
        task_cost = 0.0

        if response.status_code == 200:
            data = response.json()

            if data.get('status_code') == 20000 and data.get('tasks'):
                task = data['tasks'][0]
                task_cost = task.get('cost', 0)
                results = task.get('result') or []
                if results:
                    result = results[0]
                    blog_pages = result.get('se_results_count', 0)
                    items = result.get('items') or []
                    blog_urls = [
                        item['url'] for item in items
                        if item.get('type') == 'organic' and item.get('url')
                    ]

        blog_activity = 'active' if blog_pages > 50 else 'moderate' if blog_pages > 10 else 'inactive'

        return models.ContentResult(
            blog_pages=blog_pages,
            blog_activity=blog_activity,
            blog_urls=blog_urls,
            api_cost=task_cost,
        )

    except Exception as e:
        logger.error("Error detecting content activity: %s", e)
        return models.ContentResult()




# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_all_signals(
    company_name: str,
    domain: str,
    include_extended: bool = True,
    location_config: Optional[Dict] = None,
) -> Tuple[models.CompanySignals, models.RawSignals]:
    """Detect all marketing signals from multiple sources.

    Orchestrates all signal detection functions and combines results into a
    single CompanySignals object (LLM-friendly summary) plus a RawSignals
    object with full per-source data (for saving individual JSON files).

    Core signals (always collected):
        - Google Ads (DataForSEO Ranked Keywords API)
        - Meta Ads (Facebook/Instagram Ad Library API)
        - LinkedIn jobs (DataForSEO SERP API)
        - YouTube mentions (YouTube Data API)

    Extended signals (when include_extended=True):
        - SEO performance (DataForSEO Labs API)
        - Content activity (DataForSEO SERP API)

    Args:
        company_name: Company name.
        domain: Company domain (e.g., 'falabella.com').
        include_extended: Whether to run extended signal detectors.
        location_config: Override location settings (location_code, language_code, etc.).

    Returns:
        Tuple of:
            - CompanySignals: summary with key metrics for LLM and scoring.
            - RawSignals: typed raw data per source for individual file storage.
    """
    config = _load_config()
    signals_config = config.get('signals', {})

    loc = location_config or signals_config.get('location', {})
    location_code = loc.get('location_code', 2840)
    language_code = loc.get('language_code', 'en')
    country_code = loc.get('country_code', 'US')
    ad_reached_countries = loc.get('ad_reached_countries', 'US')
    limits = signals_config.get('limits', {})
    max_google_ads_keywords = limits.get('google_ads_keywords', 5)
    max_meta_ads = limits.get('meta_ads_to_analyze', 5)
    max_ad_themes = limits.get('meta_ad_themes', 3)
    max_seo_keywords = limits.get('seo_top_keywords', 5)
    hiring_cap = limits.get('hiring_velocity_cap', 50)

    logger.info("Detecting signals for %s (%s) [location_code=%d, language=%s]",
                company_name, domain, location_code, language_code)

    # Core signals: ads, hiring, social
    google_ads = _search_google_ads_transparency(domain, location_code=location_code,
                                                  language_code=language_code,
                                                  max_keywords=max_google_ads_keywords)
    logger.info("Google Ads result: has_ads=%s, platforms=%s, keywords=%s",
                google_ads.has_ads, google_ads.platforms, google_ads.keywords)

    meta_ads = _search_meta_ads_library(company_name, ad_reached_countries=ad_reached_countries,
                                        max_ads_to_analyze=max_meta_ads)
    logger.info("Meta Ads result: has_ads=%s, count=%s, platforms=%s",
                meta_ads.has_ads, meta_ads.count, meta_ads.platforms)

    linkedin_jobs = _search_linkedin_jobs(company_name, location_code=location_code,
                                          language_code=language_code,
                                          hiring_velocity_cap=hiring_cap)
    logger.info("LinkedIn jobs result: hiring_velocity=%d, marketing_hiring=%s, marketing_roles=%s",
                linkedin_jobs.hiring_velocity, linkedin_jobs.marketing_hiring,
                linkedin_jobs.marketing_roles[:3])

    youtube_data = _search_youtube_mentions(company_name, region_code=country_code)
    logger.info("YouTube result: total_results=%d, views=%d, likes=%d, comments=%d",
                youtube_data.total_results, youtube_data.total_views,
                youtube_data.total_likes, youtube_data.total_comments)

    # Build one signal per detector function
    google_ads_signal = models.GoogleAdsSignal(
        active_campaigns=google_ads.has_ads,
        platforms=google_ads.platforms,
        keywords=google_ads.keywords[:max_ad_themes],
        paid_keywords_count=google_ads.paid_keywords_count,
        estimated_paid_traffic=google_ads.estimated_paid_traffic,
        estimated_paid_cost_usd=google_ads.estimated_paid_cost_usd,
    )

    meta_ads_signal = models.MetaAdsSignal(
        active_campaigns=meta_ads.has_ads,
        platforms=[p.lower() for p in meta_ads.platforms],
        themes=meta_ads.themes[:max_ad_themes],
        ad_count=meta_ads.count,
    )

    # Sort marketing roles by seniority for the LLM summary.
    # Raw LinkedInJobsResult keeps all roles in original order.
    senior_keywords = ['cmo', 'chief', 'vp', 'vice president', 'head', 'director',
                       'gerente', 'subgerente', 'director/a', 'manager']
    all_marketing_roles = linkedin_jobs.marketing_roles
    senior_roles = [r for r in all_marketing_roles
                    if any(kw in r.lower() for kw in senior_keywords)]
    other_roles = [r for r in all_marketing_roles if r not in senior_roles]
    sorted_marketing_roles = senior_roles + other_roles

    linkedin_jobs_signal = models.LinkedInJobsSignal(
        hiring_velocity=linkedin_jobs.hiring_velocity,
        marketing_hiring=linkedin_jobs.marketing_hiring,
        marketing_roles=sorted_marketing_roles,
    )

    youtube_signal = models.YouTubeSignal(
        video_estimate=youtube_data.total_results,
        total_views=youtube_data.total_views,
        total_likes=youtube_data.total_likes,
        total_comments=youtube_data.total_comments,
    )

    # Extended signals — remain None when include_extended=False
    seo_signal: Optional[models.SEOSignal] = None
    content_signal: Optional[models.ContentSignal] = None

    seo_data: Optional[models.SEOResult] = None
    content_data: Optional[models.ContentResult] = None

    if include_extended:
        logger.info("Running extended signal analysis...")

        seo_data = _detect_seo_performance(domain, location_code=location_code,
                                            language_code=language_code,
                                            max_top_keywords=max_seo_keywords)
        logger.info("SEO result: organic_traffic_volume=%.1f, organic_value=$%.1f, keywords=%d",
                    seo_data.organic_traffic_volume, seo_data.organic_traffic_value_usd,
                    seo_data.keywords_count)

        seo_signal = models.SEOSignal(
            organic_traffic_volume=seo_data.organic_traffic_volume,
            organic_traffic_value_usd=seo_data.organic_traffic_value_usd,
            keywords_count=seo_data.keywords_count,
            top_keywords=seo_data.top_keywords,
            keywords_is_new=seo_data.keywords_is_new,
            keywords_is_up=seo_data.keywords_is_up,
            keywords_is_down=seo_data.keywords_is_down,
            keywords_is_lost=seo_data.keywords_is_lost,
        )

        content_data = _detect_content_activity(domain, location_code=location_code,
                                                 language_code=language_code)
        logger.info("Content result: blog_pages=%d, blog_activity=%s, blog_urls=%d",
                    content_data.blog_pages, content_data.blog_activity, len(content_data.blog_urls))

        content_signal = models.ContentSignal(
            blog_pages=content_data.blog_pages,
        )

    total_api_cost = sum(
        r.api_cost for r in [google_ads, linkedin_jobs, seo_data, content_data] if r
    )

    signals = models.CompanySignals(
        google_ads=google_ads_signal,
        meta_ads=meta_ads_signal,
        linkedin_jobs=linkedin_jobs_signal,
        youtube=youtube_signal,
        seo=seo_signal,
        content=content_signal,
        total_api_cost=total_api_cost,
    )

    raw_signals = models.RawSignals(
        google_ads=google_ads,
        meta_ads=meta_ads,
        linkedin_jobs=linkedin_jobs,
        youtube=youtube_data,
        seo=seo_data,
        content=content_data,
    )

    return signals, raw_signals
