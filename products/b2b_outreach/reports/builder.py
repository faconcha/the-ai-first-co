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
        if signals.google_ads.active_campaigns:
            signal_parts.append(f"Active Google Ads ({signals.google_ads.paid_keywords_count} paid keywords, est. ${signals.google_ads.estimated_paid_cost_usd:,.0f}/mo)")
        if signals.meta_ads.active_campaigns:
            signal_parts.append(f"Active Meta Ads ({signals.meta_ads.ad_count} ads on {', '.join(signals.meta_ads.platforms)})")
        if signals.seo:
            signal_parts.append(f"Organic traffic valued at ${signals.seo.organic_traffic_value_usd:,.0f}/mo ({signals.seo.keywords_count:,} ranked keywords)")
            if signals.seo.top_keywords:
                signal_parts.append(f"Top organic keywords: {', '.join(signals.seo.top_keywords[:3])}")
        if signals.content:
            signal_parts.append(f"Blog content: {signals.content.blog_pages} indexed pages")
        if signals.linkedin_jobs.hiring_velocity > 0:
            signal_parts.append(f"Hiring {signals.linkedin_jobs.hiring_velocity} positions")
            if signals.linkedin_jobs.marketing_hiring:
                signal_parts.append(f"Actively hiring marketing roles: {', '.join(signals.linkedin_jobs.marketing_roles[:3])}")
        if signals.youtube.video_estimate > 0:
            signal_parts.append(f"YouTube presence: ~{signals.youtube.video_estimate:,} estimated videos, {signals.youtube.total_views:,} views (from top 50)")

        if signal_parts:
            signals_summary = "\n".join(f"- {p}" for p in signal_parts)

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
- Contrast their paid/organic investment with their AI visibility gap
- Highlight biggest opportunity or concern
- Keep under 200 words

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
            'google_ads': {
                'active': signals.google_ads.active_campaigns,
                'keywords': ', '.join(signals.google_ads.keywords[:3]) if signals.google_ads.keywords else 'N/A',
                'paid_keywords_count': signals.google_ads.paid_keywords_count,
                'estimated_paid_traffic': f"{signals.google_ads.estimated_paid_traffic:,.0f}",
                'estimated_paid_cost_usd': f"${signals.google_ads.estimated_paid_cost_usd:,.0f}",
            },
            'meta_ads': {
                'active': signals.meta_ads.active_campaigns,
                'platforms': ', '.join(signals.meta_ads.platforms) if signals.meta_ads.platforms else 'N/A',
                'ad_count': signals.meta_ads.ad_count,
            },
            'linkedin_jobs': {
                'hiring_velocity': signals.linkedin_jobs.hiring_velocity,
                'marketing_hiring': signals.linkedin_jobs.marketing_hiring,
                'marketing_roles': ', '.join(signals.linkedin_jobs.marketing_roles[:3]) if signals.linkedin_jobs.marketing_roles else 'N/A',
            },
            'youtube': {
                'video_estimate': signals.youtube.video_estimate,
                'total_views': f"{signals.youtube.total_views:,}",
            },
            'seo': {
                'organic_traffic_volume': f"{signals.seo.organic_traffic_volume:,.0f}",
                'organic_traffic_value_usd': f"${signals.seo.organic_traffic_value_usd:,.0f}",
                'keywords_count': signals.seo.keywords_count,
                'top_keywords': ', '.join(signals.seo.top_keywords[:3]) if signals.seo.top_keywords else 'N/A',
            } if signals.seo else None,
            'content': {
                'blog_pages': signals.content.blog_pages,
            } if signals.content else None,
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
