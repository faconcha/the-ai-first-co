"""
Message Generator
=================

Generate personalized outreach messages for LinkedIn and WhatsApp.
"""

import logging
from typing import Dict, List, Optional

from products.b2b_outreach import models
from products.b2b_outreach.outreach import supabase_client
from products.b2b_outreach.outreach import linkedin_formatter
from products.b2b_outreach.outreach import whatsapp_formatter
from shared import llm_utils

logger = logging.getLogger("b2b_outreach.outreach")


OUTREACH_MESSAGE_TEMPLATE = """Generate a personalized B2B outreach message for the following context:

CONTACT:
- Name: {contact_name}
- Company: {company_name}
- Industry: {industry}

VISIBILITY INSIGHTS (from a real analysis we already ran for their company):
- AI Mention Rate: {mention_rate}
- Citation Rate: {citation_rate}
- Key Finding: {key_insight}

MARKET SIGNALS:
{signals_summary}

LANGUAGE: {language_instruction}

OBJECTIVE:
We already ran a full AEO (AI Engine Optimization) visibility analysis for their company and prepared a personalized report — for free. The goal of this message is to deliver that gift and make the prospect feel genuinely seen and valued, so they are curious and grateful enough to accept a follow-up meeting.

This is NOT a cold sales pitch. It is a warm, value-first introduction where the report is the gift.

MESSAGE TYPE: {channel}
{channel_constraints}

CONSTRAINTS:
- Tone: Warm, confident, and specific — not salesy or generic
- Lead with a specific insight from the analysis (actual number or signal)
- Make clear the report is already done and theirs to keep, no strings attached
- The CTA should feel like an invitation, not a close: suggest a 20-minute call to walk through the findings together
- Reference something specific about their company (signal, industry trend, or finding)
- Do NOT use phrases like "I noticed", "I came across", "I wanted to reach out"
- Do NOT make generic claims; every sentence must feel specific to this company

Structure:
1. Opening: one specific finding about their company (data-driven, not flattery)
2. Context: briefly explain what we analyzed and why it matters for them now
3. Gift: the report is ready and theirs — no strings attached
4. Soft CTA: invite them to a short call to walk through the insights together

Output only the message text, no explanation, no subject line, no labels.
"""

CHANNEL_CONSTRAINTS = {
    "linkedin": """
LINKEDIN CONSTRAINTS:
- Maximum 300 characters for connection request
- No emojis
- Professional, direct tone
- Must fit in a single paragraph
""",
    "whatsapp": """
WHATSAPP CONSTRAINTS:
- Maximum 1000 characters
- Conversational, human tone
- Can use emojis (sparingly, only to highlight key points)
- Short paragraphs with line breaks for readability
""",
}


def _generate_key_insight(visibility_metrics, signals):
    """Generate the most compelling opening insight for the outreach message.

    Prioritizes signal-specific hooks (ads spend vs AI gap, SEO value,
    hiring velocity) over generic mention rate observations, to make each
    message feel personalized and data-driven.
    """
    total_metrics = visibility_metrics.get('total', {})
    mention_rate = total_metrics.get('mention_rate', 0) * 100

    # Signal-specific insights are more compelling than generic mention rates
    if signals:
        if signals.google_ads.active_campaigns and signals.google_ads.estimated_paid_cost_usd > 0:
            return (f"investing ~${signals.google_ads.estimated_paid_cost_usd:,.0f}/mo in Google Ads "
                    f"but appearing in only {mention_rate:.0f}% of AI-generated answers about your category")
        elif signals.seo and signals.seo.organic_traffic_value_usd > 10000:
            return (f"organic SEO worth ${signals.seo.organic_traffic_value_usd:,.0f}/mo across "
                    f"{signals.seo.keywords_count:,} keywords — but AI engines are a different game, "
                    f"and your brand only shows up in {mention_rate:.0f}% of AI answers")
        elif signals.linkedin_jobs.hiring_velocity > 5:
            return (f"scaling fast ({signals.linkedin_jobs.hiring_velocity} open roles) but only "
                    f"{mention_rate:.0f}% AI mention rate — growth spend won't compound if AI engines don't know you")
        elif signals.linkedin_jobs.marketing_hiring:
            roles_str = ', '.join(signals.linkedin_jobs.marketing_roles[:2])
            return (f"building out your marketing team ({roles_str}) — the perfect moment to ensure "
                    f"AI search engines recommend you as often as traditional search does")

    # Fallback to mention rate tiers
    if mention_rate < 30:
        return f"only {mention_rate:.0f}% of AI-generated answers about your category mention your brand"
    elif mention_rate < 60:
        return f"{mention_rate:.0f}% AI mention rate — solid base, but losing ground to competitors who are optimizing for AI search"
    else:
        return f"{mention_rate:.0f}% AI mention rate, with citation quality gaps that reduce trust in AI-driven referrals"


def _generate_signals_summary(signals):
    """Generate a bullet-point summary of detected signals for the LLM prompt.

    Covers all implemented signal categories: ads, SEO, content, hiring, YouTube.
    Each bullet provides a specific data point the LLM can weave into the message.
    """
    if not signals:
        return "No specific marketing signals detected."

    parts = []

    if signals.google_ads.active_campaigns:
        parts.append(f"- Active Google Ads on {', '.join(signals.google_ads.platforms)}")
        if signals.google_ads.paid_keywords_count > 0:
            parts.append(f"- Bidding on {signals.google_ads.paid_keywords_count} paid keywords (est. ${signals.google_ads.estimated_paid_cost_usd:,.0f}/mo)")

    if signals.meta_ads.active_campaigns:
        parts.append(f"- Active Meta Ads: {signals.meta_ads.ad_count} ads on {', '.join(signals.meta_ads.platforms)}")

    if signals.seo:
        if signals.seo.organic_traffic_value_usd > 0:
            parts.append(f"- Organic SEO traffic valued at ${signals.seo.organic_traffic_value_usd:,.0f}/mo ({signals.seo.keywords_count:,} ranked keywords)")
        if signals.seo.top_keywords:
            parts.append(f"- Top organic keywords: {', '.join(signals.seo.top_keywords[:3])}")

    if signals.content and signals.content.blog_pages > 0:
        parts.append(f"- Blog content: {signals.content.blog_pages} indexed pages")

    if signals.linkedin_jobs.hiring_velocity > 0:
        parts.append(f"- Hiring {signals.linkedin_jobs.hiring_velocity} positions (growth phase)")
        if signals.linkedin_jobs.marketing_hiring:
            parts.append(f"- Actively hiring marketing roles: {', '.join(signals.linkedin_jobs.marketing_roles[:3])}")

    if signals.youtube.video_estimate > 0:
        parts.append(f"- YouTube: ~{signals.youtube.video_estimate:,} estimated videos, {signals.youtube.total_views:,} views (from top 50)")

    if not parts:
        return "- Company is established with online presence"

    return "\n".join(parts)


def _resolve_contact_name(contact_id, contact_name):
    """
    Resolve contact name from Supabase or use the provided name directly.
    Returns the name string to use in the message.
    """
    if contact_name:
        return contact_name

    if contact_id:
        try:
            contact = supabase_client.get_prospect_by_id(contact_id)
            if contact:
                return contact.get('person_name', 'there')
        except Exception:
            pass

    return 'there'


LANGUAGE_INSTRUCTIONS = {
    "es": "Write the entire message in Spanish, using natural Latin American business tone.",
    "en": "Write the entire message in English.",
    "pt": "Write the entire message in Portuguese (Brazilian), using natural Brazilian business tone.",
}


def generate_personalized_message(
    company_research,
    visibility_metrics,
    signals,
    contact_id=None,
    contact_name=None,
    channels=None,
    language="es",
):
    """
    Generate personalized outreach messages for specified channels.

    Args:
        company_research: CompanyResearch object.
        visibility_metrics: Visibility analysis results dict.
        signals: CompanySignals object (optional).
        contact_id: Contact ID from Supabase (optional if contact_name is provided).
        contact_name: Contact name to use directly, skipping Supabase lookup (optional).
        channels: List of channels (default: ["linkedin", "whatsapp"]).
        language: Language code for the message ("es", "en", "pt"). Defaults to "es".

    Returns:
        Dictionary mapping channel to message text.
    """
    if channels is None:
        channels = ["linkedin", "whatsapp"]

    resolved_name = _resolve_contact_name(contact_id, contact_name)

    language_instruction = LANGUAGE_INSTRUCTIONS.get(
        language,
        f"Write the entire message in {language}."
    )

    # Pre-compute shared context that goes into every channel's prompt
    total_metrics = visibility_metrics.get('total', {})
    mention_rate = f"{total_metrics.get('mention_rate', 0) * 100:.0f}%"
    citation_rate = f"{total_metrics.get('citation_rate', 0) * 100:.0f}%"

    key_insight = _generate_key_insight(visibility_metrics, signals)
    signals_summary = _generate_signals_summary(signals)

    messages = {}

    # Generate one message per channel, each with its own constraints
    for channel in channels:
        channel_constraints = CHANNEL_CONSTRAINTS.get(channel, "")

        prompt = OUTREACH_MESSAGE_TEMPLATE.format(
            contact_name=resolved_name,
            company_name=company_research.name,
            industry=company_research.industry,
            mention_rate=mention_rate,
            citation_rate=citation_rate,
            key_insight=key_insight,
            signals_summary=signals_summary,
            language_instruction=language_instruction,
            channel=channel.upper(),
            channel_constraints=channel_constraints
        )

        try:
            message_text = llm_utils.query(
                prompt=prompt,
                profile="smart",
                temperature=0.8,
                max_tokens=512
            )

            message_text = message_text.strip()

            # Apply channel-specific formatting (truncation, emoji handling, etc.)
            if channel == "linkedin":
                message_text = linkedin_formatter.format_for_linkedin(message_text, max_length=300)
            elif channel == "whatsapp":
                message_text = whatsapp_formatter.format_for_whatsapp(message_text, max_length=1000)

            messages[channel] = message_text

        except Exception as e:
            logger.error("Error generating %s message: %s", channel, e)
            messages[channel] = f"Hi {resolved_name}, we ran an AI visibility analysis for {company_research.name} and have some specific findings to share. I'd love to send you the report — no strings attached. Worth a quick look?"

    return messages
