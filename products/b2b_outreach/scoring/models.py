from typing import Optional
from enum import Enum

from pydantic import BaseModel


class ScoreTier(str, Enum):
    HOT = "hot"    # >= 70
    WARM = "warm"  # 40-69
    COLD = "cold"  # < 40


class ScoringWeights(BaseModel):
    icp_match: float = 0.3
    signal_strength: float = 0.3
    visibility_gap: float = 0.2
    buying_intent: float = 0.2


class LeadScore(BaseModel):
    total_score: float            # 0-100
    tier: ScoreTier
    icp_match_score: float        # 0-100
    signal_strength_score: float  # 0-100
    visibility_gap_score: float   # 0-100
    buying_intent_score: float    # 0-100
    reasoning: str
