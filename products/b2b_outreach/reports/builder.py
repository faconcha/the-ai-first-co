"""
Report Builder
==============

Generates PDF reports for B2B outreach with visibility analysis.
"""

import logging
import os
import datetime
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from products.b2b_outreach import models
from shared import llm_utils

logger = logging.getLogger("b2b_outreach.reports")


def _get_templates_dir():
    """Get path to templates directory."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')


def _format_percentage(value):
    """Format float as percentage string."""
    return f"{value * 100:.1f}%"


def _get_metric_display(metrics, key, format_type="percentage"):
    """Format a metric value for PDF display based on its type (percentage, count, or sentiment)."""
    value = metrics.get(key, 0)

    if format_type == "percentage":
        return _format_percentage(value)
    elif format_type == "count":
        return str(int(value))
    elif format_type == "sentiment":
        # Classify sentiment into positive/neutral/negative with threshold bucketing
        if value >= 0.6:
            return f"Positive ({_format_percentage(value)})"
        elif value >= 0.4:
            return f"Neutral ({_format_percentage(value)})"
        else:
            return f"Negative ({_format_percentage(value)})"

    return str(value)


def _generate_executive_summary(company_research, visibility_metrics, signals):
    """
    Generate executive summary using LLM.

    Args:
        company_research: CompanyResearch object.
        visibility_metrics: Visibility analysis results.
        signals: CompanySignals object (optional).

    Returns:
        Executive summary text.
    """
    total_metrics = visibility_metrics.get('total', {})
    mention_rate = _get_metric_display(total_metrics, 'mention_rate', 'percentage')
    citation_rate = _get_metric_display(total_metrics, 'citation_rate', 'percentage')

    signals_summary = "No marketing signals detected."
    if signals:
        signal_parts = []
        if signals.ads and signals.ads.active_campaigns:
            signal_parts.append(f"Active advertising on {', '.join(signals.ads.platforms)}")
        if signals.growth and signals.growth.hiring_velocity > 0:
            signal_parts.append(f"Hiring {signals.growth.hiring_velocity} positions")
        if signals.social and signals.social.linkedin_activity > 0:
            signal_parts.append(f"Active on social media")

        if signal_parts:
            signals_summary = "; ".join(signal_parts)

    prompt = f"""Write a concise executive summary (2-3 paragraphs) for a B2B visibility analysis report.

Company: {company_research.name}
Industry: {company_research.industry}
Products: {', '.join(company_research.products[:3])}

Key Metrics:
- AI Mention Rate: {mention_rate}
- Citation Rate: {citation_rate}

Market Signals:
{signals_summary}

Requirements:
- Professional B2B tone
- Focus on actionable insights
- Highlight biggest opportunity or concern
- Keep under 150 words

Write only the executive summary text, no title or label.
"""

    try:
        return llm_utils.query(
            prompt=prompt,
            profile="smart",
            temperature=0.7,
            max_tokens=512
        ).strip()

    except Exception as e:
        logger.error("Error generating executive summary: %s", e)
        return f"{company_research.name} operates in the {company_research.industry} industry with a current AI visibility mention rate of {mention_rate}. This report analyzes their brand presence across AI-powered search engines and provides recommendations for improvement."


def build_outreach_report(company_research, visibility_metrics, signals=None, output_path=None):
    """
    Generate PDF report for B2B outreach.

    Args:
        company_research: CompanyResearch object.
        visibility_metrics: Visibility analysis results.
        signals: CompanySignals object (optional).
        output_path: Path to save PDF (optional, returns bytes if not provided).

    Returns:
        PDF as bytes.
    """
    # Load the Jinja2 HTML template for PDF rendering
    templates_dir = _get_templates_dir()
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('pdf_template.html')

    total_metrics = visibility_metrics.get('total', {})
    by_model = visibility_metrics.get('by_model', {})

    # Generate the LLM-written executive summary for the report header
    executive_summary = _generate_executive_summary(
        company_research,
        visibility_metrics,
        signals
    )

    # Format per-model metrics (ChatGPT, Claude, etc.) for the comparison table
    model_metrics = []
    for model_name, metrics in by_model.items():
        model_metrics.append({
            'name': model_name.upper(),
            'mention_rate': _get_metric_display(metrics, 'mention_rate', 'percentage'),
            'citation_rate': _get_metric_display(metrics, 'citation_rate', 'percentage'),
            'avg_position': _get_metric_display(metrics, 'avg_position', 'count'),
            'sentiment': _get_metric_display(metrics, 'avg_sentiment', 'sentiment')
        })

    # Flatten signal objects into template-friendly dictionaries
    signals_data = None
    if signals:
        signals_data = {
            'ads': {
                'active': signals.ads.active_campaigns if signals.ads else False,
                'platforms': ', '.join(signals.ads.platforms) if signals.ads and signals.ads.platforms else 'N/A'
            } if signals.ads else None,
            'growth': {
                'hiring': signals.growth.hiring_velocity if signals.growth else 0,
                'roles': ', '.join(signals.growth.roles[:3]) if signals.growth and signals.growth.roles else 'N/A'
            } if signals.growth else None,
            'social': {
                'linkedin_posts': signals.social.linkedin_activity if signals.social else 0,
                'youtube_mentions': signals.social.youtube_mentions if signals.social else 0
            } if signals.social else None,
            'seo': {
                'organic_traffic': f"{signals.seo.organic_traffic_estimate:,}" if signals.seo else 'N/A',
                'keywords_count': signals.seo.organic_keywords_count if signals.seo else 0,
                'top_keywords': ', '.join(signals.seo.top_keywords[:3]) if signals.seo and signals.seo.top_keywords else 'N/A',
                'domain_rank': signals.seo.domain_rank if signals.seo else 0
            } if signals.seo else None,
            'content': {
                'blog_activity': signals.content.blog_activity if signals.content else 'N/A',
                'recent_pages': signals.content.recent_pages_count if signals.content else 0,
                'featured_snippets': signals.content.featured_snippets if signals.content else 0,
                'knowledge_panel': signals.content.knowledge_panel if signals.content else False
            } if signals.content else None,
            'prospection': {
                'is_prospecting': signals.prospection.is_prospecting if signals.prospection else False,
                'confidence': f"{signals.prospection.confidence * 100:.0f}%" if signals.prospection else 'N/A',
                'signal_strength': signals.prospection.signal_strength if signals.prospection else 'N/A',
                'indicators': signals.prospection.indicators if signals.prospection else [],
                'explanation': signals.prospection.explanation if signals.prospection else ''
            } if signals.prospection else None,
            'funding': {
                'has_recent_funding': signals.funding.has_recent_funding if signals.funding else False,
                'last_round_type': signals.funding.last_round_type if signals.funding else '',
                'last_round_amount_usd': signals.funding.last_round_amount_usd if signals.funding else 0,
            } if signals.funding else None,
            'news': {
                'recent_news_count': signals.news.recent_news_count if signals.news else 0,
                'has_product_launch': signals.news.has_product_launch if signals.news else False,
                'top_headlines': signals.news.top_headlines[:3] if signals.news else [],
            } if signals.news else None,
            'intent': {
                'intent_score': signals.intent.intent_score if signals.intent else 0.0,
                'review_sentiment': signals.intent.review_sentiment if signals.intent else '',
                'has_competitor_comparisons': signals.intent.has_competitor_comparisons if signals.intent else False,
            } if signals.intent else None,
        }

    context = {
        'company_name': company_research.name,
        'domain': company_research.domain,
        'industry': company_research.industry,
        'products': ', '.join(company_research.products[:5]),
        'report_date': datetime.date.today().strftime('%B %d, %Y'),
        'executive_summary': executive_summary,
        'mention_rate': _get_metric_display(total_metrics, 'mention_rate', 'percentage'),
        'citation_rate': _get_metric_display(total_metrics, 'citation_rate', 'percentage'),
        'avg_position': _get_metric_display(total_metrics, 'avg_position', 'count'),
        'sentiment': _get_metric_display(total_metrics, 'avg_sentiment', 'sentiment'),
        'model_metrics': model_metrics,
        'signals': signals_data
    }

    # Render the HTML template and convert to PDF via WeasyPrint
    html_content = template.render(**context)

    html_obj = HTML(string=html_content, base_url=templates_dir)
    pdf_bytes = html_obj.write_pdf()

    if output_path:
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)

    return pdf_bytes
