import os
import yaml
from typing import Dict, Any, Optional

from products.b2b_outreach import models
from products.b2b_outreach.scoring import models as scoring_models


def _load_config() -> Dict[str, Any]:
    """Load scoring configuration (weights, thresholds, ICP industries) from YAML."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'scoring.yaml')
    with open(config_path) as f:
        return yaml.safe_load(f)


def _weights_from_config(config: Dict[str, Any]) -> scoring_models.ScoringWeights:
    """Extract scoring dimension weights from config, with defaults summing to 1.0."""
    w = config.get('weights', {})
    return scoring_models.ScoringWeights(
        icp_match=w.get('icp_match', 0.3),
        signal_strength=w.get('signal_strength', 0.3),
        visibility_gap=w.get('visibility_gap', 0.2),
        buying_intent=w.get('buying_intent', 0.2),
    )


def _score_icp_match(
    company_research: models.CompanyResearch,
    signals: Optional[models.CompanySignals],
    icp_industries: list,
) -> float:
    """Score how well the company matches our Ideal Customer Profile (0-100).

    Base score from industry match (70 if match, 30 if not), with bonuses
    for B2B audience (+5), hiring activity (up to +15), and active ads (+10).
    """
    industry = (company_research.industry or "").lower()
    industry_match = any(icp.lower() in industry or industry in icp.lower() for icp in icp_industries)
    base = 70.0 if industry_match else 30.0

    # B2B/enterprise companies are a better fit for our product
    target_audience = (company_research.target_audience or '').lower()
    if 'b2b' in target_audience or 'enterprise' in target_audience:
        base += 5

    if signals is not None:
        # Hiring velocity bonus: each open position adds 2 points, capped at 15
        hiring_velocity = signals.growth.hiring_velocity if signals.growth else 0
        base += min(hiring_velocity * 2, 15)

        # Active ad spend signals marketing budget and willingness to invest
        if signals.ads and signals.ads.active_campaigns:
            base += 10

    return min(base, 100.0)


def _score_signal_strength(signals: Optional[models.CompanySignals]) -> float:
    """Aggregate all detected signals into a single strength score (0-100).

    Each signal category contributes a capped amount: ads (30), hiring (20),
    social (10), SEO (20), content (10), prospection (10), funding (15),
    news (10), intent (15). Total is capped at 100.
    """
    if signals is None:
        return 0.0

    score = 0.0

    if signals.ads and signals.ads.active_campaigns:
        score += 30

    if signals.growth:
        hiring = signals.growth.hiring_velocity
        score += min(hiring * 2, 20)

    if signals.social:
        mentions = signals.social.youtube_mentions
        score += min(mentions * 2, 10)

    # SEO score is tiered by organic traffic volume
    if signals.seo:
        traffic = signals.seo.organic_traffic_estimate
        if traffic >= 100000:
            score += 20
        elif traffic >= 50000:
            score += 15
        elif traffic >= 10000:
            score += 10
        elif traffic >= 1000:
            score += 5

    if signals.content:
        activity = signals.content.blog_activity
        if activity == "active":
            score += 10
        elif activity == "moderate":
            score += 5

    if signals.prospection:
        score += min(signals.prospection.confidence * 10, 10)

    if signals.funding and signals.funding.has_recent_funding:
        score += 15

    if signals.news and signals.news.recent_news_count > 0:
        score += min(signals.news.recent_news_count * 2, 10)

    if signals.intent and signals.intent.intent_score > 0:
        score += min(signals.intent.intent_score * 15, 15)

    return min(score, 100.0)


def _score_visibility_gap(visibility_metrics: Dict[str, Any]) -> float:
    """Score the AI visibility gap (0-100). Lower mention rates = higher opportunity.

    A company with low AI visibility has more to gain from our product,
    so low mention rates yield high scores (e.g., <10% -> 90 points).
    """
    if not visibility_metrics:
        return 60.0

    nested = visibility_metrics.get('total', visibility_metrics)
    mention_rate = nested.get('mention_rate', None)
    if mention_rate is None:
        return 60.0

    # Inverse relationship: less visible = bigger gap = higher score
    if mention_rate < 0.1:
        return 90.0
    elif mention_rate < 0.3:
        return 70.0
    elif mention_rate < 0.5:
        return 50.0
    else:
        return 20.0


def _score_buying_intent(signals: Optional[models.CompanySignals]) -> float:
    """Score buying intent based on growth, funding, news, and executive hiring (0-100).

    Companies with recent funding, product launches, or executive hiring
    are more likely to invest in new solutions.
    """
    if signals is None:
        return 10.0

    growth = signals.growth
    if growth is None:
        return 10.0

    base = 20.0 if growth.growth_indicators else 10.0

    # Funding signals indicate available budget
    if growth.funding_news:
        base += 20

    # Avoid double-counting if funding detected from both growth and funding signals
    if signals.funding and signals.funding.has_recent_funding and not growth.funding_news:
        base += 20

    if signals.news and signals.news.has_product_launch:
        base += 15

    # Executive-level hiring suggests strategic investment decisions ahead
    roles_lower = [r.lower() for r in growth.roles]
    exec_keywords = ['cmo', 'ceo', 'cto', 'coo', 'vp', 'chief', 'president', 'director']
    if any(keyword in role for role in roles_lower for keyword in exec_keywords):
        base += 15

    return min(base, 100.0)


def _determine_tier(total_score: float, config: Dict[str, Any]) -> scoring_models.ScoreTier:
    """Map the total score to a tier (HOT/WARM/COLD) using configurable thresholds.

    Thresholds are loaded from scoring.yaml under 'thresholds.hot' and
    'thresholds.warm'. Defaults: hot >= 70, warm >= 40, cold < 40.

    Tier meanings:
    - HOT: High-priority lead, strong ICP fit + signals + opportunity gap.
      Should be contacted immediately with a personalized outreach.
    - WARM: Moderate fit, worth nurturing. May need more signals or a
      visibility gap to justify immediate outreach.
    - COLD: Low priority. Weak fit or insufficient signals. Can be
      revisited if new signals emerge.

    Args:
        total_score: Weighted final score (0-100).
        config: Full scoring config dict (must contain 'thresholds' key).

    Returns:
        ScoreTier enum value (HOT, WARM, or COLD).
    """
    thresholds = config.get('thresholds', {})
    hot_threshold = thresholds.get('hot', 70)
    warm_threshold = thresholds.get('warm', 40)

    if total_score >= hot_threshold:
        return scoring_models.ScoreTier.HOT
    elif total_score >= warm_threshold:
        return scoring_models.ScoreTier.WARM
    else:
        return scoring_models.ScoreTier.COLD


def _build_reasoning(
    company_research: models.CompanyResearch,
    icp_match: float,
    signal_strength: float,
    visibility_gap: float,
    buying_intent: float,
    total_score: float,
    tier: scoring_models.ScoreTier,
) -> str:
    """Build a human-readable explanation of how the lead score was calculated.

    Produces a single paragraph summarizing each scoring dimension with
    qualitative labels based on thresholds:
    - Signal strength: "strong" (>=60), "moderate" (>=30), "weak" (<30)
    - Visibility gap: "high opportunity" (>=70), "moderate" (>=50), "limited" (<50)
    - Buying intent: "high" (>=50), "limited" (<50)

    The output is designed for both internal review (pipeline logs, audit
    JSON) and customer-facing reports. Each sentence maps to one scoring
    dimension so readers can understand what drove the final tier.

    Args:
        company_research: CompanyResearch with at least industry populated.
        icp_match: ICP match score (0-100).
        signal_strength: Signal strength score (0-100).
        visibility_gap: Visibility gap score (0-100).
        buying_intent: Buying intent score (0-100).
        total_score: Weighted total score (0-100).
        tier: Assigned ScoreTier (HOT/WARM/COLD).

    Returns:
        Multi-sentence reasoning string.
    """
    parts = []

    industry = company_research.industry or "unknown"
    parts.append(f"Industry '{industry}' yielded ICP match score of {icp_match:.0f}/100.")

    if signal_strength >= 60:
        parts.append(f"Strong signal activity detected (score: {signal_strength:.0f}/100).")
    elif signal_strength >= 30:
        parts.append(f"Moderate signals detected (score: {signal_strength:.0f}/100).")
    else:
        parts.append(f"Weak or no signals detected (score: {signal_strength:.0f}/100).")

    if visibility_gap >= 70:
        parts.append(f"Low AI visibility presents a high opportunity gap (score: {visibility_gap:.0f}/100).")
    elif visibility_gap >= 50:
        parts.append(f"Moderate visibility gap detected (score: {visibility_gap:.0f}/100).")
    else:
        parts.append(f"Company has strong AI visibility; gap is limited (score: {visibility_gap:.0f}/100).")

    if buying_intent >= 50:
        parts.append(f"High buying intent indicators present (score: {buying_intent:.0f}/100).")
    else:
        parts.append(f"Limited buying intent signals (score: {buying_intent:.0f}/100).")

    parts.append(f"Total score: {total_score:.1f}/100 — Tier: {tier.value.upper()}.")

    return " ".join(parts)


def score_lead(
    company_research: models.CompanyResearch,
    signals: Optional[models.CompanySignals],
    visibility_metrics: Dict[str, Any],
    weights: Optional[scoring_models.ScoringWeights] = None,
) -> scoring_models.LeadScore:
    """Score a lead across 4 dimensions and assign a priority tier.

    Scoring dimensions (each produces a 0-100 sub-score):
    1. ICP Match: How well the company matches our ideal customer profile
       (industry, audience type, hiring activity, ad spend).
    2. Signal Strength: Aggregate strength of all detected market signals
       (ads, hiring, social, SEO, content, funding, news, intent).
    3. Visibility Gap: How much room the company has to improve in AI search.
       Lower current visibility = higher opportunity score.
    4. Buying Intent: Likelihood the company is actively looking to invest
       (funding, product launches, executive hiring).

    The final score is a weighted sum: total = sum(dimension_i * weight_i).
    Weights are loaded from scoring.yaml (default: ICP 0.3, Signals 0.3,
    Visibility Gap 0.2, Buying Intent 0.2). The total is mapped to a tier
    (HOT/WARM/COLD) using configurable thresholds.

    Args:
        company_research: CompanyResearch object with company details.
        signals: CompanySignals object (can be None if signals were skipped).
        visibility_metrics: Dict with 'total' key containing mention_rate,
            citation_rate, etc. Can be empty if AEO pipeline was not run.
        weights: Optional override for scoring dimension weights. If None,
            weights are loaded from scoring.yaml.

    Returns:
        LeadScore with total_score, tier, per-dimension scores, and reasoning.
    """
    config = _load_config()

    if weights is None:
        weights = _weights_from_config(config)

    icp_industries = config.get('icp_industries', [])

    # Compute each scoring dimension independently (each 0-100)
    icp_match = _score_icp_match(company_research, signals, icp_industries)
    signal_strength = _score_signal_strength(signals)
    visibility_gap = _score_visibility_gap(visibility_metrics)
    buying_intent = _score_buying_intent(signals)

    # Weighted sum produces the final score (0-100)
    total_score = (
        icp_match * weights.icp_match
        + signal_strength * weights.signal_strength
        + visibility_gap * weights.visibility_gap
        + buying_intent * weights.buying_intent
    )

    tier = _determine_tier(total_score, config)

    reasoning = _build_reasoning(
        company_research,
        icp_match,
        signal_strength,
        visibility_gap,
        buying_intent,
        total_score,
        tier,
    )

    return scoring_models.LeadScore(
        total_score=round(total_score, 2),
        tier=tier,
        icp_match_score=round(icp_match, 2),
        signal_strength_score=round(signal_strength, 2),
        visibility_gap_score=round(visibility_gap, 2),
        buying_intent_score=round(buying_intent, 2),
        reasoning=reasoning,
    )
