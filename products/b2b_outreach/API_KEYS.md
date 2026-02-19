# B2B Outreach - Required API Keys

All keys should be set as environment variables in the project `.env` file.

| Env Variable | Required | Used By | How to Get |
|---|---|---|---|
| `GEMINI_API_KEY` | Yes | LLM calls (research, prompts, reports, messages) | [Google AI Studio](https://aistudio.google.com/) |
| `ANTHROPIC_API_KEY` | No (fallback) | Alternative LLM provider | [Anthropic Console](https://console.anthropic.com/) |
| `DATAFORSEO_LOGIN` | Yes | Google Ads, SEO, content signals | [dataforseo.com](https://dataforseo.com/) |
| `DATAFORSEO_PASSWORD` | Yes | Google Ads, SEO, content signals | [dataforseo.com](https://dataforseo.com/) |
| `META_ACCESS_TOKEN` | Yes | Meta Ad Library (Facebook/Instagram) | [Meta Business](https://business.facebook.com/) |
| `YOUTUBE_API_KEY` | Yes | YouTube mention detection | [Google Cloud Console](https://console.cloud.google.com/) |
| `CRUNCHBASE_API_KEY` | Yes | Funding signal detection | [crunchbase.com](https://www.crunchbase.com/) |
| `HUNTER_API_KEY` | Yes | Contact enrichment + email verification | [hunter.io](https://hunter.io/) |
| `APOLLO_API_KEY` | No (fallback) | Contact enrichment (second source) | [apollo.io](https://www.apollo.io/) |
| `ROCKETREACH_API_KEY` | No (fallback) | Contact enrichment (third source) | [rocketreach.co](https://rocketreach.co/) |
| `SUPABASE_URL` | Yes | Contact and company data storage | [supabase.com](https://supabase.com/) |
| `SUPABASE_KEY` | Yes | Contact and company data storage | [supabase.com](https://supabase.com/) |

## Signal Functions and Their Keys

| Signal Function | Keys Required |
|---|---|
| `_search_google_ads_transparency` | DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD |
| `_search_meta_ad_library` | META_ACCESS_TOKEN |
| `_search_linkedin_jobs` | None (public scraping) |
| `_search_youtube_mentions` | YOUTUBE_API_KEY |
| `_detect_seo_performance` | DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD |
| `_detect_content_activity` | DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD |
| `_detect_funding_signals` | CRUNCHBASE_API_KEY |
| `_detect_news_signals` | None (Google News RSS, free) |
| `_detect_intent_signals` | None (G2 web scraping) |
