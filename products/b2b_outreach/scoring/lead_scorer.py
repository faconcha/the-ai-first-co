"""
Lead Scorer — Per-Signal CMO-Driven Scoring
=============================================

Scores each signal data structure independently (0-100), then combines
into a global score via weighted sum. All parameters are loaded from
config/scoring.yaml — nothing is hardcoded.

Scoring philosophy:
- No vanity metrics: scores reflect actual investment levels, not mere existence.
- Honest caps: signals with poor data quality are capped to avoid overweighting.
- Continuous scoring: piecewise linear curves instead of coarse step functions.
- CMO weights: SEO and visibility gap dominate because they directly indicate
  search dependency (our ICP) and problem size (our value prop).
"""

import os
import yaml
from typing import Dict, Any, Optional, List

from products.b2b_outreach import models
from products.b2b_outreach.scoring import models as scoring_models


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def _load_config() -> Dict[str, Any]:
    """Load scoring configuration from YAML."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'scoring.yaml')
    with open(config_path) as f:
        return yaml.safe_load(f)


def _weights_from_config(config: Dict[str, Any]) -> scoring_models.ScoringWeights:
    """Extract scoring weights from config."""
    w = config.get('weights', {})
    return scoring_models.ScoringWeights(
        seo=w.get('seo', 0.25),
        visibility_gap=w.get('visibility_gap', 0.20),
        google_ads=w.get('google_ads', 0.15),
        linkedin_jobs=w.get('linkedin_jobs', 0.15),
        content=w.get('content', 0.10),
        meta_ads=w.get('meta_ads', 0.10),
        youtube=w.get('youtube', 0.05),
    )


# ---------------------------------------------------------------------------
# Generic scoring utilities
# ---------------------------------------------------------------------------


def _piecewise_score(value: float, anchors: List[List[float]]) -> float:
    """Piecewise linear interpolation from config anchors.

    Anchors are [[input_value, output_score], ...] sorted ascending by input.
    Interpolates linearly between adjacent anchor points.
    Values below first anchor return first anchor's score.
    Values above last anchor return last anchor's score.
    """
    if not anchors:
        return 0.0

    if value <= anchors[0][0]:
        return float(anchors[0][1])

    for i in range(1, len(anchors)):
        if value < anchors[i][0]:
            x0, y0 = anchors[i - 1]
            x1, y1 = anchors[i]
            return y0 + (value - x0) / (x1 - x0) * (y1 - y0)

    return float(anchors[-1][1])


def _tier_score(value: float, tiers: List[List[float]]) -> float:
    """Step function: returns the bonus of the highest exceeded threshold.

    Tiers are [[threshold, bonus], ...] sorted ascending by threshold.
    """
    result = 0.0
    for threshold, bonus in tiers:
        if value > threshold:
            result = bonus
    return result


# ---------------------------------------------------------------------------
# Per-signal scoring functions (each returns 0-100)
# ---------------------------------------------------------------------------


def _score_google_ads(signal: models.GoogleAdsSignal, cfg: Dict[str, Any]) -> float:
    """Score paid search investment level.

    Primary driver: estimated_paid_cost_usd (monthly ad spend estimate).
    No points just for having active campaigns — the spend level matters.
    """
    cost = signal.estimated_paid_cost_usd
    if cost <= 0:
        return 0.0

    score = _piecewise_score(cost, cfg.get('anchors', []))

    bonus_per = cfg.get('keyword_bonus_per', 0.1)
    bonus_max = cfg.get('keyword_bonus_max', 5.0)
    keyword_bonus = min(signal.paid_keywords_count * bonus_per, bonus_max)

    return min(score + keyword_bonus, 100.0)


def _score_meta_ads(signal: models.MetaAdsSignal, cfg: Dict[str, Any]) -> float:
    """Score paid social investment level.

    Capped because we have no spend data, only ad count and platforms.
    """
    if not signal.active_campaigns or signal.ad_count <= 0:
        return 0.0

    cap = cfg.get('cap', 80)
    score = _piecewise_score(signal.ad_count, cfg.get('anchors', []))

    bonus_per = cfg.get('platform_bonus_per', 10)
    bonus_max = cfg.get('platform_bonus_max', 20)
    platform_bonus = min((len(signal.platforms) - 1) * bonus_per, bonus_max)

    return min(score + platform_bonus, cap)


def _score_seo(signal: Optional[models.SEOSignal], cfg: Dict[str, Any]) -> float:
    """Score organic search strength.

    Most valuable signal. Primary driver: organic_traffic_value_usd.
    Trend modifier from net keyword movement. Breadth bonus from keyword count.
    """
    if signal is None:
        return 0.0

    value = signal.organic_traffic_value_usd
    if value <= 0:
        return 0.0

    base = _piecewise_score(value, cfg.get('anchors', []))

    # Trend modifier from keyword movement direction
    total_keywords = max(signal.keywords_count, 1)
    net_movement = (
        (signal.keywords_is_new + signal.keywords_is_up)
        - (signal.keywords_is_down + signal.keywords_is_lost)
    )
    trend_ratio = net_movement / total_keywords
    trend_multiplier = cfg.get('trend_multiplier', 50)
    trend_max = cfg.get('trend_max', 10)
    trend_modifier = max(min(trend_ratio * trend_multiplier, trend_max), -trend_max)

    breadth_per = cfg.get('breadth_bonus_per', 0.001)
    breadth_max = cfg.get('breadth_bonus_max', 5.0)
    breadth_bonus = min(signal.keywords_count * breadth_per, breadth_max)

    return max(min(base + trend_modifier + breadth_bonus, 100.0), 0.0)


def _score_content(signal: Optional[models.ContentSignal], cfg: Dict[str, Any]) -> float:
    """Score content marketing investment.

    Capped because blog_pages is a crude count with no quality indicator.
    """
    if signal is None or signal.blog_pages <= 0:
        return 0.0

    cap = cfg.get('cap', 70)
    score = _piecewise_score(signal.blog_pages, cfg.get('anchors', []))

    return min(score, cap)


def _score_linkedin_jobs(signal: models.LinkedInJobsSignal, cfg: Dict[str, Any]) -> float:
    """Score growth trajectory and buying readiness.

    Hiring velocity shows general growth. Marketing hiring is a strong
    buying intent signal. Executive-level roles suggest strategic
    investment decisions are imminent.
    """
    score = 0.0

    velocity = signal.hiring_velocity
    if velocity > 0:
        score = _piecewise_score(velocity, cfg.get('velocity_anchors', []))

    if signal.marketing_hiring:
        score += cfg.get('marketing_hiring_bonus', 25)

        role_per = cfg.get('role_bonus_per', 2)
        role_max = cfg.get('role_bonus_max', 10)
        score += min(len(signal.marketing_roles) * role_per, role_max)

    # Executive-level hiring
    exec_keywords = cfg.get('exec_keywords', [])
    roles_lower = [r.lower() for r in signal.marketing_roles]
    has_exec = any(kw in role for role in roles_lower for kw in exec_keywords)
    if has_exec:
        score += cfg.get('exec_bonus', 20)

    return min(score, 100.0)


def _score_youtube(signal: models.YouTubeSignal, cfg: Dict[str, Any]) -> float:
    """Score brand presence on YouTube.

    Capped because video_estimate is unreliable and engagement stats
    are sampled from top 50 videos only.
    """
    if signal.video_estimate <= 0:
        return 0.0

    cap = cfg.get('cap', 55)
    score = _piecewise_score(signal.video_estimate, cfg.get('video_anchors', []))

    score += _tier_score(signal.total_views, cfg.get('views_tiers', []))
    score += _tier_score(signal.total_comments, cfg.get('comments_tiers', []))

    return min(score, cap)


def _score_visibility_gap(visibility_metrics: Dict[str, Any], cfg: Dict[str, Any]) -> float:
    """Score the AI visibility opportunity.

    Inverse relationship: lower AI mention rate = bigger opportunity = higher score.
    Uses a continuous power curve. Citation gap modifier adds bonus when
    company is mentioned but rarely cited.
    """
    default_score = cfg.get('default_score', 50)

    if not visibility_metrics:
        return float(default_score)

    nested = visibility_metrics.get('total', visibility_metrics)
    mention_rate = nested.get('mention_rate', None)
    citation_rate = nested.get('citation_rate', None)

    if mention_rate is None:
        return float(default_score)

    max_score = cfg.get('max_score', 95.0)
    exponent = cfg.get('power_exponent', 1.3)
    base = max_score * ((1.0 - min(mention_rate, 1.0)) ** exponent)

    citation_mention_min = cfg.get('citation_mention_min', 0.1)
    citation_gap_threshold = cfg.get('citation_gap_threshold', 0.2)
    citation_gap_bonus = cfg.get('citation_gap_bonus', 5)

    if citation_rate is not None and mention_rate > citation_mention_min:
        citation_gap = mention_rate - citation_rate
        if citation_gap > citation_gap_threshold:
            base += citation_gap_bonus

    return min(max(base, 0.0), 100.0)


# ---------------------------------------------------------------------------
# Tier determination
# ---------------------------------------------------------------------------


def _determine_tier(total_score: float, config: Dict[str, Any]) -> scoring_models.ScoreTier:
    """Map the total score to a tier (HOT/WARM/COLD) using configurable thresholds."""
    thresholds = config.get('thresholds', {})
    hot_threshold = thresholds.get('hot', 70)
    warm_threshold = thresholds.get('warm', 40)

    if total_score >= hot_threshold:
        return scoring_models.ScoreTier.HOT
    elif total_score >= warm_threshold:
        return scoring_models.ScoreTier.WARM
    else:
        return scoring_models.ScoreTier.COLD


# ---------------------------------------------------------------------------
# Reasoning builder
# ---------------------------------------------------------------------------


def _build_reasoning(
    company_research: models.CompanyResearch,
    signal_scores: scoring_models.SignalScores,
    weights: scoring_models.ScoringWeights,
    total_score: float,
    tier: scoring_models.ScoreTier,
    signals: Optional[models.CompanySignals],
    visibility_metrics: Dict[str, Any],
) -> str:
    """Build a CMO-readable explanation of the lead score.

    Each line explains one signal's score with concrete numbers.
    No vague qualifiers — every statement is backed by data.
    """
    parts = []

    # SEO (highest weight)
    if signals and signals.seo and signals.seo.organic_traffic_value_usd > 0:
        seo = signals.seo
        net = (seo.keywords_is_new + seo.keywords_is_up) - (seo.keywords_is_down + seo.keywords_is_lost)
        trend_label = "growing" if net > 0 else "declining" if net < 0 else "stable"
        parts.append(
            f"SEO ({signal_scores.seo:.0f}/100, weight {weights.seo:.0%}): "
            f"Organic traffic valued at ${seo.organic_traffic_value_usd:,.0f}/mo "
            f"across {seo.keywords_count:,} keywords ({trend_label})."
        )
    else:
        parts.append(f"SEO ({signal_scores.seo:.0f}/100): No organic traffic data.")

    # Visibility gap
    nested = visibility_metrics.get('total', visibility_metrics) if visibility_metrics else {}
    mention_rate = nested.get('mention_rate')
    if mention_rate is not None:
        parts.append(
            f"Visibility gap ({signal_scores.visibility_gap:.0f}/100, weight {weights.visibility_gap:.0%}): "
            f"AI mention rate {mention_rate:.1%}."
        )
    else:
        parts.append(f"Visibility gap ({signal_scores.visibility_gap:.0f}/100): No visibility data.")

    # Google Ads
    if signals and signals.google_ads.estimated_paid_cost_usd > 0:
        g = signals.google_ads
        parts.append(
            f"Google Ads ({signal_scores.google_ads:.0f}/100, weight {weights.google_ads:.0%}): "
            f"Est. ${g.estimated_paid_cost_usd:,.0f}/mo on {g.paid_keywords_count} keywords."
        )
    else:
        parts.append(f"Google Ads ({signal_scores.google_ads:.0f}/100): No paid search activity.")

    # LinkedIn hiring
    if signals and signals.linkedin_jobs.hiring_velocity > 0:
        jobs = signals.linkedin_jobs
        mkt_note = ""
        if jobs.marketing_hiring:
            roles_str = ", ".join(jobs.marketing_roles[:3])
            mkt_note = f" Marketing roles: {roles_str}."
        parts.append(
            f"LinkedIn hiring ({signal_scores.linkedin_jobs:.0f}/100, weight {weights.linkedin_jobs:.0%}): "
            f"{jobs.hiring_velocity} open positions.{mkt_note}"
        )
    else:
        parts.append(f"LinkedIn hiring ({signal_scores.linkedin_jobs:.0f}/100): No hiring activity.")

    # Content
    if signals and signals.content and signals.content.blog_pages > 0:
        parts.append(
            f"Content ({signal_scores.content:.0f}/100, weight {weights.content:.0%}): "
            f"{signals.content.blog_pages} indexed blog pages."
        )
    else:
        parts.append(f"Content ({signal_scores.content:.0f}/100): No blog activity.")

    # Meta Ads
    if signals and signals.meta_ads.active_campaigns:
        m = signals.meta_ads
        parts.append(
            f"Meta Ads ({signal_scores.meta_ads:.0f}/100, weight {weights.meta_ads:.0%}): "
            f"{m.ad_count} active ads on {', '.join(m.platforms)}."
        )
    else:
        parts.append(f"Meta Ads ({signal_scores.meta_ads:.0f}/100): No Meta ad activity.")

    # YouTube
    if signals and signals.youtube.video_estimate > 0:
        yt = signals.youtube
        parts.append(
            f"YouTube ({signal_scores.youtube:.0f}/100, weight {weights.youtube:.0%}): "
            f"~{yt.video_estimate} videos, {yt.total_views:,} views sampled."
        )
    else:
        parts.append(f"YouTube ({signal_scores.youtube:.0f}/100): No YouTube presence.")

    # Industry context (informational, not scored)
    industry = company_research.industry or "unknown"
    parts.append(f"Industry: {industry}.")

    parts.append(f"Global score: {total_score:.1f}/100 — Tier: {tier.value.upper()}.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def score_lead(
    company_research: models.CompanyResearch,
    signals: Optional[models.CompanySignals],
    visibility_metrics: Dict[str, Any],
    weights: Optional[scoring_models.ScoringWeights] = None,
) -> scoring_models.LeadScore:
    """Score a lead across 7 independent signal dimensions and assign a priority tier.

    Each signal data structure is scored independently (0-100), then combined
    via weighted sum. All parameters (weights, thresholds, anchors, bonuses)
    are loaded from config/scoring.yaml.

    Args:
        company_research: CompanyResearch object with company details.
        signals: CompanySignals object (can be None if signals were skipped).
        visibility_metrics: Dict with 'total' key containing mention_rate, citation_rate.
        weights: Optional override for scoring weights. If None, loaded from config.

    Returns:
        LeadScore with total_score, tier, per-signal scores, and reasoning.
    """
    config = _load_config()

    if weights is None:
        weights = _weights_from_config(config)

    # Score each signal independently, passing its config section
    ss = scoring_models.SignalScores(
        google_ads=round(_score_google_ads(
            signals.google_ads if signals else models.GoogleAdsSignal(),
            config.get('google_ads', {}),
        ), 2),
        meta_ads=round(_score_meta_ads(
            signals.meta_ads if signals else models.MetaAdsSignal(),
            config.get('meta_ads', {}),
        ), 2),
        seo=round(_score_seo(
            signals.seo if signals else None,
            config.get('seo', {}),
        ), 2),
        content=round(_score_content(
            signals.content if signals else None,
            config.get('content', {}),
        ), 2),
        linkedin_jobs=round(_score_linkedin_jobs(
            signals.linkedin_jobs if signals else models.LinkedInJobsSignal(),
            config.get('linkedin_jobs', {}),
        ), 2),
        youtube=round(_score_youtube(
            signals.youtube if signals else models.YouTubeSignal(),
            config.get('youtube', {}),
        ), 2),
        visibility_gap=round(_score_visibility_gap(
            visibility_metrics,
            config.get('visibility_gap', {}),
        ), 2),
    )

    # Weighted sum
    total_score = (
        ss.seo * weights.seo
        + ss.visibility_gap * weights.visibility_gap
        + ss.google_ads * weights.google_ads
        + ss.linkedin_jobs * weights.linkedin_jobs
        + ss.content * weights.content
        + ss.meta_ads * weights.meta_ads
        + ss.youtube * weights.youtube
    )

    tier = _determine_tier(total_score, config)

    reasoning = _build_reasoning(
        company_research, ss, weights, total_score, tier, signals, visibility_metrics
    )

    return scoring_models.LeadScore(
        total_score=round(total_score, 2),
        tier=tier,
        signal_scores=ss,
        reasoning=reasoning,
    )
