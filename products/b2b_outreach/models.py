"""
B2B Outreach Models
===================

Pydantic models for the B2B outreach pipeline. All data flowing between
pipeline steps has a strictly typed schema. Two layers:

1. Raw signal results: what each detector function returns (full API data).
2. Summary signal models: what the LLM and scoring engine consume (key metrics only).
"""

import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Raw signal results (returned by each _search_* / _detect_* function)
# ---------------------------------------------------------------------------


class GoogleAdsResult(BaseModel):
    """Raw result from _search_google_ads_transparency (DataForSEO ranked_keywords)."""
    has_ads: bool = False
    platforms: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    paid_keywords_count: int = 0
    estimated_paid_traffic: float = 0.0
    estimated_paid_cost_usd: float = 0.0
    note: Optional[str] = None


class MetaAdsResult(BaseModel):
    """Raw result from _search_meta_ads_library (Meta Ad Library API)."""
    has_ads: bool = False
    platforms: List[str] = Field(default_factory=list)
    themes: List[str] = Field(default_factory=list)
    count: int = 0
    note: Optional[str] = None


class LinkedInJobsResult(BaseModel):
    """Raw result from _search_linkedin_jobs (DataForSEO SERP API)."""
    hiring_velocity: int = 0
    roles: List[str] = Field(default_factory=list)
    marketing_hiring: bool = False
    marketing_roles: List[str] = Field(default_factory=list)
    source: str = ""
    note: Optional[str] = None


class YouTubeResult(BaseModel):
    """Raw result from _search_youtube_mentions (YouTube Data API v3).

    Uses search.list to find videos mentioning the brand (last 30 days),
    then videos.list to fetch engagement stats for the returned videos.
    """
    total_results: int = 0
    total_views: int = 0
    total_likes: int = 0
    total_comments: int = 0
    estimated_media_value_usd: float = 0.0
    note: Optional[str] = None


class SEOResult(BaseModel):
    """Raw result from _detect_seo_performance (DataForSEO ranked_keywords organic)."""
    organic_traffic: float = 0.0
    organic_traffic_value_usd: float = 0.0
    keywords_count: int = 0
    top_keywords: List[str] = Field(default_factory=list)
    note: Optional[str] = None


class ContentResult(BaseModel):
    """Raw result from _detect_content_activity (DataForSEO SERP API)."""
    blog_pages: int = 0
    blog_activity: str = "unknown"
    blog_urls: List[str] = Field(default_factory=list)
    note: Optional[str] = None


class ProspectionResult(BaseModel):
    """Raw result from _detect_prospection_signals (computed from other signals)."""
    is_prospecting: bool = False
    confidence: float = 0.0
    indicators: List[str] = Field(default_factory=list)
    signal_strength: str = "weak"
    explanation: str = ""


class FundingResult(BaseModel):
    """Raw result from _detect_funding_signals (Crunchbase API)."""
    has_recent_funding: bool = False
    last_round_type: str = ""
    last_round_amount_usd: int = 0
    last_round_date: Optional[str] = None
    total_funding_usd: int = 0
    investors: List[str] = Field(default_factory=list)
    note: Optional[str] = None


class NewsResult(BaseModel):
    """Raw result from _detect_news_signals (Google News RSS)."""
    recent_news_count: int = 0
    has_product_launch: bool = False
    has_partnership_news: bool = False
    has_acquisition_news: bool = False
    top_headlines: List[str] = Field(default_factory=list)
    last_news_date: Optional[str] = None
    note: Optional[str] = None


class IntentResult(BaseModel):
    """Raw result from _detect_intent_signals (G2 reviews)."""
    has_recent_reviews: bool = False
    review_sentiment: str = ""
    review_count: int = 0
    has_competitor_comparisons: bool = False
    intent_score: float = 0.0
    note: Optional[str] = None


class RawSignals(BaseModel):
    """All raw signal results, one field per detector. Saved as individual JSON files."""
    google_ads: GoogleAdsResult = Field(default_factory=GoogleAdsResult)
    meta_ads: MetaAdsResult = Field(default_factory=MetaAdsResult)
    linkedin_jobs: LinkedInJobsResult = Field(default_factory=LinkedInJobsResult)
    youtube: YouTubeResult = Field(default_factory=YouTubeResult)
    seo: Optional[SEOResult] = None
    content: Optional[ContentResult] = None
    prospection: Optional[ProspectionResult] = None
    funding: Optional[FundingResult] = None
    news: Optional[NewsResult] = None
    intent: Optional[IntentResult] = None


# ---------------------------------------------------------------------------
# Company Research
# ---------------------------------------------------------------------------


class CompanyResearch(BaseModel):
    """Company research results — optimized for B2B sales intelligence."""
    # Core profile
    name: str
    domain: str
    industry: str
    products: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    value_proposition: str = ""
    target_audience: str = ""
    pain_points: List[str] = Field(default_factory=list)
    country: Optional[str] = None
    city: Optional[str] = None
    aliases: Optional[List[str]] = None
    competitors: Optional[List[str]] = None
    # B2B sales intelligence
    business_context: Optional[List[str]] = None
    strategic_priorities: Optional[List[str]] = None
    company_challenges: Optional[List[str]] = None
    tech_stack: Optional[List[str]] = None
    buying_triggers: Optional[List[str]] = None
    annual_revenue: Optional[str] = None
    employee_count: Optional[str] = None


# ---------------------------------------------------------------------------
# Summary signal models (LLM-facing — key metrics and conclusions only)
# ---------------------------------------------------------------------------


class AdsSignal(BaseModel):
    """Advertising activity signal."""
    active_campaigns: bool = False
    platforms: List[str] = Field(default_factory=list)
    themes: List[str] = Field(default_factory=list)
    estimated_paid_traffic: float = 0.0
    estimated_paid_cost_usd: float = 0.0
    paid_keywords_count: int = 0
    paid_search_ratio: float = 0.0
    last_seen: Optional[datetime.datetime] = None
    ad_count: int = 0


class GrowthSignal(BaseModel):
    """Company growth signal."""
    hiring_velocity: int = 0
    roles: List[str] = Field(default_factory=list)
    marketing_hiring: bool = False
    marketing_roles: List[str] = Field(default_factory=list)
    funding_news: List[Dict[str, Any]] = Field(default_factory=list)
    growth_indicators: List[str] = Field(default_factory=list)


class SocialSignal(BaseModel):
    """Social media activity signal."""
    linkedin_activity: int = 0
    youtube_total_results: int = 0
    youtube_total_views: int = 0
    youtube_total_likes: int = 0
    youtube_total_comments: int = 0
    youtube_estimated_media_value_usd: float = 0.0


class SEOSignal(BaseModel):
    """SEO and organic search performance signal."""
    organic_traffic_value_usd: float = 0.0


class ContentSignal(BaseModel):
    """Content marketing activity signal."""
    blog_pages: int = 0
    blog_activity: str = ""


class ProspectionSignal(BaseModel):
    """Active prospection indicators."""
    is_prospecting: bool = False
    confidence: float = 0.0
    indicators: List[str] = Field(default_factory=list)
    signal_strength: str = ""
    explanation: str = ""


class FundingSignal(BaseModel):
    """Funding round signal."""
    has_recent_funding: bool = False
    last_round_type: str = ""
    last_round_amount_usd: int = 0
    last_round_date: Optional[str] = None
    total_funding_usd: int = 0
    investors: List[str] = Field(default_factory=list)


class NewsSignal(BaseModel):
    """News and press signal."""
    recent_news_count: int = 0
    has_product_launch: bool = False
    has_partnership_news: bool = False
    has_acquisition_news: bool = False
    top_headlines: List[str] = Field(default_factory=list)
    last_news_date: Optional[str] = None


class IntentSignal(BaseModel):
    """Buyer intent signal."""
    has_recent_reviews: bool = False
    review_sentiment: str = ""
    review_count: int = 0
    has_competitor_comparisons: bool = False
    intent_score: float = 0.0


class CompanySignals(BaseModel):
    """All detected signals for a company."""
    ads: AdsSignal = Field(default_factory=AdsSignal)
    growth: GrowthSignal = Field(default_factory=GrowthSignal)
    social: SocialSignal = Field(default_factory=SocialSignal)
    seo: Optional[SEOSignal] = None
    content: Optional[ContentSignal] = None
    prospection: Optional[ProspectionSignal] = None
    funding: Optional[FundingSignal] = None
    news: Optional[NewsSignal] = None
    intent: Optional[IntentSignal] = None
    detected_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


# ---------------------------------------------------------------------------
# Contact & Outreach
# ---------------------------------------------------------------------------


class Contact(BaseModel):
    """Contact information from Supabase."""
    id: str
    name: str
    company_id: str
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None


class OutreachPackage(BaseModel):
    """Complete outreach package."""
    company_id: str
    report_pdf_bytes: bytes = Field(default=b'', exclude=True)
    report_url: str = ""
    visibility_metrics: Dict[str, Any] = Field(default_factory=dict)
    signals: Optional[CompanySignals] = None
    messages: Dict[str, str] = Field(default_factory=dict)
    prompt_ids: List[str] = Field(default_factory=list)
    company_research: Optional[CompanyResearch] = None
    lead_score: Optional[Any] = None
