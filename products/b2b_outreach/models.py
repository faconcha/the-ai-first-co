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
    api_cost: float = 0.0
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
    api_cost: float = 0.0
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
    note: Optional[str] = None


class SEOResult(BaseModel):
    """Raw result from _detect_seo_performance (DataForSEO ranked_keywords organic)."""
    organic_traffic_volume: float = 0.0
    organic_traffic_value_usd: float = 0.0
    keywords_count: int = 0
    top_keywords: List[str] = Field(default_factory=list)
    keywords_is_new: int = 0
    keywords_is_up: int = 0
    keywords_is_down: int = 0
    keywords_is_lost: int = 0
    api_cost: float = 0.0
    note: Optional[str] = None


class ContentResult(BaseModel):
    """Raw result from _detect_content_activity (DataForSEO SERP API)."""
    blog_pages: int = 0
    blog_activity: str = "unknown"
    blog_urls: List[str] = Field(default_factory=list)
    api_cost: float = 0.0
    note: Optional[str] = None


class RawSignals(BaseModel):
    """All raw signal results, one field per detector. Saved as individual JSON files."""
    google_ads: GoogleAdsResult = Field(default_factory=GoogleAdsResult)
    meta_ads: MetaAdsResult = Field(default_factory=MetaAdsResult)
    linkedin_jobs: LinkedInJobsResult = Field(default_factory=LinkedInJobsResult)
    youtube: YouTubeResult = Field(default_factory=YouTubeResult)
    seo: Optional[SEOResult] = None
    content: Optional[ContentResult] = None


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


class GoogleAdsSignal(BaseModel):
    """Google Ads signal (from _search_google_ads_transparency)."""
    active_campaigns: bool = False
    platforms: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    paid_keywords_count: int = 0
    estimated_paid_traffic: float = 0.0
    estimated_paid_cost_usd: float = 0.0


class MetaAdsSignal(BaseModel):
    """Meta Ads signal (from _search_meta_ads_library)."""
    active_campaigns: bool = False
    platforms: List[str] = Field(default_factory=list)
    themes: List[str] = Field(default_factory=list)
    ad_count: int = 0


class LinkedInJobsSignal(BaseModel):
    """LinkedIn Jobs signal (from _search_linkedin_jobs)."""
    hiring_velocity: int = 0
    marketing_hiring: bool = False
    marketing_roles: List[str] = Field(default_factory=list)


class YouTubeSignal(BaseModel):
    """YouTube signal (from _search_youtube_mentions)."""
    video_estimate: int = 0
    total_views: int = 0
    total_likes: int = 0
    total_comments: int = 0


class SEOSignal(BaseModel):
    """SEO signal (from _detect_seo_performance)."""
    organic_traffic_volume: float = 0.0
    organic_traffic_value_usd: float = 0.0
    keywords_count: int = 0
    top_keywords: List[str] = Field(default_factory=list)
    keywords_is_new: int = 0
    keywords_is_up: int = 0
    keywords_is_down: int = 0
    keywords_is_lost: int = 0


class ContentSignal(BaseModel):
    """Content signal (from _detect_content_activity)."""
    blog_pages: int = 0


class CompanySignals(BaseModel):
    """All detected signals for a company."""
    google_ads: GoogleAdsSignal = Field(default_factory=GoogleAdsSignal)
    meta_ads: MetaAdsSignal = Field(default_factory=MetaAdsSignal)
    linkedin_jobs: LinkedInJobsSignal = Field(default_factory=LinkedInJobsSignal)
    youtube: YouTubeSignal = Field(default_factory=YouTubeSignal)
    seo: Optional[SEOSignal] = None
    content: Optional[ContentSignal] = None
    total_api_cost: float = 0.0
    detected_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


# ---------------------------------------------------------------------------
# Discovery Prompts
# ---------------------------------------------------------------------------


class DiscoveryPrompt(BaseModel):
    """A single discovery prompt for AEO visibility testing."""
    query: str
    language: str = "es"
    generated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


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
