"""
AEO Prospection Pipeline

Fetch prospect and company data from Supabase, call the AEO full-pipeline
endpoint, and return the results.

Usage:
    uv run python products/aeo_prospection/claude/run_prospection.py \
        --email "prospect@example.com" --prompts "prompt 1" "prompt 2"
"""

import argparse
import json
import logging
import sys
from typing import List, Optional

import requests

from products.b2b_outreach.outreach import supabase_client
from products.aeo_prospection import models

logger = logging.getLogger("aeo_prospection.pipeline")

AEO_ENDPOINT = "https://aeo-prod-216762537172.us-central1.run.app/prospect/run-full-pipeline"
DEFAULT_MODELS = ["chatgpt", "perplexity"]
DEFAULT_N_EXECUTIONS = 3


def run_prospection(
    prospect_email: str,
    prompts: Optional[List[str]] = None,
    ai_models: Optional[List[str]] = None,
    n_executions: int = DEFAULT_N_EXECUTIONS,
) -> dict:
    """
    Run the AEO prospection pipeline for a given prospect email.

    Returns dict with the raw endpoint response, or an error dict.
    """
    prospect = supabase_client.get_prospect_by_email(prospect_email)
    if not prospect:
        return {"error": f"Prospect not found: {prospect_email}"}

    company_url = prospect.get("company_url")
    if not company_url:
        return {"error": f"Prospect {prospect_email} has no company_url"}

    company = supabase_client.find_company_by_url(company_url)
    if not company:
        return {"error": f"Company not found: {company_url}"}

    company_name = company.get("company_name")
    if not company_name:
        return {"error": f"Company {company_url} has no company_name"}

    competitors_raw = company.get("competitors") or []
    competitors = [models.Competitor(**c) for c in competitors_raw]

    if not prompts:
        return {
            "error": "No prompts provided. The skill executor must generate prompts based on company context.",
            "company": company,
            "prospect": prospect,
        }

    prospect_name = f"{prospect.get('first_name', '')} {prospect.get('last_name', '')}".strip()
    if not prospect_name:
        prospect_name = prospect_email

    request_body = models.AEOPipelineRequest(
        company_name=company_name,
        company_domain=company_url,
        competitors=competitors,
        prompts=prompts,
        prospect_name=prospect_name,
        prospect_email=prospect_email,
        prospect_company=company_name,
        country=company.get("country"),
        city=company.get("city"),
        models=ai_models or DEFAULT_MODELS,
        n_executions_per_model=n_executions,
        business_aliases=None,
    )

    payload = request_body.model_dump(mode="json", exclude_none=True)

    try:
        response = requests.post(AEO_ENDPOINT, json=payload, timeout=300)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.Timeout:
        return {"error": "AEO endpoint timed out after 300 seconds"}
    except requests.exceptions.HTTPError:
        return {"error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}

    result["report_url"] = supabase_client.prospect_report_url(prospect_email)

    return result


def main():
    parser = argparse.ArgumentParser(description="AEO Prospection Pipeline")
    parser.add_argument("--email", required=True, help="Prospect email")
    parser.add_argument("--prompts", nargs="+", help="Prompts to test")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS, help="AI models to test")
    parser.add_argument("--n-executions", type=int, default=DEFAULT_N_EXECUTIONS, help="Executions per model (1-10)")
    parser.add_argument("--output", help="Output JSON file path")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    result = run_prospection(
        prospect_email=args.email,
        prompts=args.prompts,
        ai_models=args.models,
        n_executions=args.n_executions,
    )

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
