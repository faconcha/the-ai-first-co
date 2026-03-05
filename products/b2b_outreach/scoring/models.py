from enum import Enum

from pydantic import BaseModel


class ScoreTier(str, Enum):
    HOT = "hot"    # >= 70
    WARM = "warm"  # 40-69
    COLD = "cold"  # < 40


class SignalScores(BaseModel):
    """Per-signal scores (each 0-100). Caps reflect data quality."""
    google_ads: float = 0.0
    meta_ads: float = 0.0        # capped at 80
    seo: float = 0.0
    content: float = 0.0         # capped at 70
    linkedin_jobs: float = 0.0
    youtube: float = 0.0         # capped at 55
    visibility_gap: float = 0.0


class ScoringWeights(BaseModel):
    """CMO-driven weights for each signal. Must sum to 1.0."""
    seo: float = 0.25
    visibility_gap: float = 0.20
    google_ads: float = 0.15
    linkedin_jobs: float = 0.15
    content: float = 0.10
    meta_ads: float = 0.10
    youtube: float = 0.05


class LeadScore(BaseModel):
    total_score: float
    tier: ScoreTier
    signal_scores: SignalScores
    reasoning: str
