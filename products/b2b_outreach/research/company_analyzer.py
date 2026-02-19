"""
Company Analyzer
================

Analyze company websites and extract structured company information.
"""

import yaml
import os
import logging

from products.b2b_outreach import models
from products.b2b_outreach import schemas
from products.b2b_outreach.research import web_fetcher
from shared import llm_utils

logger = logging.getLogger("b2b_outreach.research")


def _load_config():
    """Load configuration from b2b_outreach.yaml."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "config",
        "b2b_outreach.yaml"
    )

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def _extract_company_info(domain, content_map):
    """
    Extract structured company information using LLM with Pydantic schema.

    Args:
        domain: Company domain.
        content_map: Dictionary of page paths to content.

    Returns:
        CompanyInfoResponse Pydantic model with extracted company information.
    """
    # Concatenate all page contents with separators for the LLM prompt
    combined_content = "\n\n".join([
        f"=== Page: {page} ===\n{content}"
        for page, content in content_map.items()
    ])

    prompt = f"""Analyze the following website content and extract structured company information.

Website domain: {domain}

Content:
{combined_content}

Requirements:
- Be specific and extract real information from the content
- For products/services, include actual names not generic descriptions
- For pain_points, identify problems they solve for customers
"""

    try:
        result = llm_utils.query_structured(
            prompt=prompt,
            response_schema=schemas.CompanyInfoResponse,
            profile="smart",
            temperature=0.3,
            max_tokens=2048
        )
        return result

    except Exception as e:
        logger.error("Error extracting company info: %s", e)
        return None


def analyze_company_website(domain, pages_to_fetch=None, max_pages=10, timeout=180):
    """
    Analyze company website and extract structured data.

    Steps:
    1. Fetch content from key pages (homepage, about, products, etc.)
    2. Use LLM to extract structured company information
    3. Return CompanyResearch object

    Args:
        domain: Company domain (e.g., 'salesforce.com').
        pages_to_fetch: List of page paths to scrape (default from config).
        max_pages: Maximum pages to fetch.
        timeout: Timeout per page in seconds.

    Returns:
        CompanyResearch object with extracted information.
    """
    if pages_to_fetch is None:
        config = _load_config()
        research_config = config.get('research', {})
        pages_to_fetch = research_config.get('pages_to_fetch', ['/', '/about', '/products'])
        max_pages = research_config.get('max_pages_to_scrape', max_pages)
        timeout = research_config.get('timeout_per_page', timeout)

    pages_to_fetch = pages_to_fetch[:max_pages]

    content_map = web_fetcher.fetch_multiple_pages(domain, pages_to_fetch, timeout=timeout)

    if not content_map:
        raise ValueError(f"Failed to fetch any content from {domain}")

    company_info = _extract_company_info(domain, content_map)

    if not company_info:
        raise ValueError("Failed to extract company information")

    return models.CompanyResearch(
        name=company_info.name or domain,
        domain=domain,
        industry=company_info.industry or "Unknown",
        products=company_info.products or [],
        services=company_info.services or [],
        value_proposition=company_info.value_proposition or "",
        target_audience=company_info.target_audience or "",
        pain_points=company_info.pain_points or [],
        country=company_info.country,
        city=company_info.city,
        aliases=company_info.aliases,
        competitors=company_info.competitors,
        business_context=company_info.business_context,
        strategic_priorities=company_info.strategic_priorities,
        company_challenges=company_info.company_challenges,
        tech_stack=company_info.tech_stack,
        buying_triggers=company_info.buying_triggers,
        annual_revenue=company_info.annual_revenue,
        employee_count=company_info.employee_count,
    )
