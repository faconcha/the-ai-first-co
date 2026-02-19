"""
Prompt Generator
================

Generate realistic product discovery prompts using LLM with Pydantic structured output.
"""

import yaml
import os
import logging

from products.b2b_outreach import schemas
from products.b2b_outreach.prompts import templates
from shared import llm_utils

logger = logging.getLogger("b2b_outreach.prompts")


def _load_config():
    """Load configuration from b2b_outreach.yaml."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "config",
        "b2b_outreach.yaml"
    )

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


LANGUAGE_INSTRUCTIONS = {
    "es": "Write all queries in Spanish, as a Spanish-speaking prospect in Latin America would naturally type them.",
    "en": "Write all queries in English.",
    "pt": "Write all queries in Portuguese (Brazilian), as a Brazilian prospect would naturally type them.",
}


def generate_discovery_prompts(company_research, n_prompts=10, language="es"):
    """
    Generate realistic product discovery prompts using LLM.

    Args:
        company_research: CompanyResearch object with company information.
        n_prompts: Number of prompts to generate (default: 10).
        language: Language code for the generated queries ("es", "en", "pt"). Defaults to "es".

    Returns:
        List of prompt strings.
    """
    # Load LLM settings (temperature, profile, etc.) from config
    yaml_config = _load_config()
    prompt_config = yaml_config.get('prompt_generation', {})

    temperature = prompt_config.get('temperature', 0.8)
    max_tokens = prompt_config.get('max_tokens', 4096)
    profile = prompt_config.get('llm_profile', 'smart')

    language_instruction = LANGUAGE_INSTRUCTIONS.get(
        language,
        f"Write all queries in {language}."
    )

    # Flatten lists to comma-separated strings for the prompt template
    products_str = ', '.join(company_research.products) if company_research.products else 'N/A'
    services_str = ', '.join(company_research.services) if company_research.services else 'N/A'
    pain_points_str = ', '.join(company_research.pain_points) if company_research.pain_points else 'N/A'

    prompt = templates.DISCOVERY_PROMPT_TEMPLATE.format(
        company_name=company_research.name,
        industry=company_research.industry,
        products=products_str,
        services=services_str,
        value_proposition=company_research.value_proposition,
        target_audience=company_research.target_audience,
        pain_points=pain_points_str,
        n_prompts=n_prompts,
        language_instruction=language_instruction,
    )

    try:
        result = llm_utils.query_structured(
            prompt=prompt,
            response_schema=schemas.DiscoveryPromptsResponse,
            profile=profile,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return result.prompts[:n_prompts]

    except Exception as e:
        logger.error("Error generating prompts: %s", e)
        raise
