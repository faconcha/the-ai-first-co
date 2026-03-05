"""
B2B Outreach Pipeline (Claude Code script)
==========================================

Run the B2B outreach pipeline: company research, signal detection,
lead scoring, prompt generation, report building, and message generation.

All intermediate results and logs are saved to an output directory for auditing.

Usage:
    uv run python products/b2b_outreach/claude/run_pipeline.py --company "Stripe" --domain "stripe.com"
    uv run python products/b2b_outreach/claude/run_pipeline.py --company "Falabella" --domain "falabella.com" --industry "Retail"
    uv run python products/b2b_outreach/claude/run_pipeline.py --company "Stripe" --domain "stripe.com" --skip-research --skip-prompts
"""

import argparse
import datetime
import json
import logging
import os
import yaml
from pathlib import Path

from products.b2b_outreach.signals import marketing_detector
from products.b2b_outreach.scoring import lead_scorer
from products.b2b_outreach.research import company_analyzer
from products.b2b_outreach.prompts import generator
from products.b2b_outreach.reports import builder
from products.b2b_outreach.outreach import message_generator
from products.b2b_outreach.outreach import supabase_client
from products.b2b_outreach import models
from products.b2b_outreach import logging_config

logger = logging.getLogger("b2b_outreach.pipeline")


def _load_config():
    """Load b2b_outreach.yaml configuration."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "config",
        "b2b_outreach.yaml"
    )
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def _save_json(output_dir, filename, data):
    """Save a dict or list as a JSON file in the output directory."""
    filepath = output_dir / filename
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def _create_output_dir(company_name):
    """Create the pipeline output directory based on config.

    Returns:
        Path to the output directory.
    """
    config = _load_config()
    output_config = config.get('output', {})
    base_path = output_config.get('base_path', 'output/b2b_outreach')
    folder_pattern = output_config.get('folder_pattern', 'b2b_outreach_{company_name}')

    company_slug = company_name.lower().replace(' ', '_')
    folder_name = folder_pattern.format(company_name=company_slug)

    output_dir = Path(base_path) / folder_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def run_pipeline(
    company_name,
    domain,
    industry="Unknown",
    include_extended_signals=True,
    skip_research=False,
    skip_prompts=False,
    skip_report=False,
    skip_messages=False,
    n_prompts=3,
    contact_id=None,
    contact_name=None,
    visibility_metrics=None,
    output_report_path=None,
    country=None,
    language="es",
    research_path=None,
):
    """
    Run the B2B outreach pipeline with configurable steps.

    Each step can be skipped via flags. All intermediate results are saved
    to the output directory for auditing. Use skip flags for a lighter run:
    e.g., skip_research=True, skip_prompts=True for signals-only analysis.

    Args:
        company_name: Company name.
        domain: Company domain (e.g., 'stripe.com').
        industry: Company industry.
        include_extended_signals: Include SEO and content signals.
        skip_research: Skip website research (use minimal CompanyResearch).
        skip_prompts: Skip discovery prompt generation.
        skip_report: Skip PDF report generation.
        skip_messages: Skip outreach message generation.
        n_prompts: Number of discovery prompts to generate.
        contact_id: Supabase contact ID for message personalization.
        contact_name: Contact name for message personalization (skips Supabase lookup).
        visibility_metrics: Pre-computed visibility metrics (from AEO pipeline).
        output_report_path: Path to save PDF report.
        country: ISO country code (e.g., 'CL', 'MX'). Auto-detected from research if omitted.
        language: Language code for generated prompts and messages ("es", "en", "pt"). Defaults to "es".
        research_path: Path to a pre-built 01_research.json (from /research-company skill).

    Returns:
        dict with all pipeline results.
    """
    # Create output directory and set up logging
    output_dir = _create_output_dir(company_name)
    logging_config.setup_pipeline_logging(output_dir)

    logger.info("=" * 60)
    logger.info("B2B Outreach Pipeline started for %s (%s)", company_name, domain)
    logger.info("Output directory: %s", output_dir)
    logger.info("=" * 60)

    # Step 1/6: Company research
    logger.info("Step 1/6: Company research")
    existing_research = research_path or (output_dir / "01_research.json")
    if existing_research and Path(existing_research).is_file():
        logger.info("  Loading pre-built research from %s", existing_research)
        with open(existing_research, 'r') as f:
            data = json.load(f)
        research = models.CompanyResearch(**data)
        logger.info("  Loaded. Industry: %s, Products: %d, Services: %d",
                    research.industry, len(research.products), len(research.services))
    elif not skip_research:
        logger.info("  Analyzing website %s...", domain)
        research = company_analyzer.analyze_company_website(domain)
        logger.info("  Research complete. Industry: %s, Products: %d, Services: %d",
                    research.industry, len(research.products), len(research.services))
    else:
        logger.info("  Skipped (using minimal CompanyResearch)")
        research = models.CompanyResearch(
            name=company_name,
            domain=domain,
            industry=industry,
            products=[],
            services=[],
            value_proposition="",
            target_audience="",
            pain_points=[]
        )
    _save_json(output_dir, "01_research.json", research.model_dump(mode='json'))

    # Resolve country → location config for signal detection
    # Priority: explicit --country flag > research.country > YAML defaults
    resolved_country = country or research.country
    location_config = None
    if resolved_country:
        location_config = marketing_detector.location_config_for_country(resolved_country)
        if location_config:
            logger.info("  Location: %s → location_code=%d, language=%s",
                        resolved_country, location_config["location_code"], location_config["language_code"])
        else:
            logger.info("  Country %s not in location map, using YAML defaults", resolved_country)

    # Step 2/6: Signal detection
    logger.info("Step 2/6: Signal detection")
    signals, raw_signals = marketing_detector.detect_all_signals(
        company_name, domain,
        include_extended=include_extended_signals,
        location_config=location_config,
    )
    logger.info("  Signals detected. Google Ads: %s, Hiring: %d, YouTube: %d videos / %d views",
                signals.google_ads.active_campaigns, signals.linkedin_jobs.hiring_velocity,
                signals.youtube.video_estimate, signals.youtube.total_views)
    if signals.seo:
        logger.info("  SEO: $%.2f organic traffic value, %d keywords",
                    signals.seo.organic_traffic_value_usd, signals.seo.keywords_count)
    total_api_cost = sum(
        getattr(v, 'api_cost', 0) for v in
        [raw_signals.google_ads, raw_signals.linkedin_jobs, raw_signals.seo, raw_signals.content]
        if v
    )
    logger.info("  DataForSEO API cost: $%.4f", total_api_cost)

    # Save summary (LLM-friendly) and individual raw signal files
    _save_json(output_dir, "02_signals.json", signals.model_dump(mode='json'))
    signals_dir = output_dir / "02_signals"
    signals_dir.mkdir(exist_ok=True)
    for signal_name, signal_data in raw_signals.model_dump(mode='json').items():
        if signal_data is not None:
            _save_json(signals_dir, f"{signal_name}.json", signal_data)

    # Persist company profile to Supabase (upsert by domain)
    _company_record = supabase_client.upsert_company({
        'company_name': company_name,
        'company_url': domain,
        'industry': research.industry,
        'country': research.country,
        'city': research.city,
        'annual_revenue': research.annual_revenue,
        'employee_count': research.employee_count,
    })
    if _company_record:
        logger.info("  Saved to Supabase company: %s (id: %s)", company_name, _company_record['id'])

    # Step 3/6: Lead scoring
    logger.info("Step 3/6: Lead scoring")
    score = lead_scorer.score_lead(
        company_research=research,
        signals=signals,
        visibility_metrics=visibility_metrics or {}
    )
    logger.info("  Score: %.1f/100, Tier: %s", score.total_score, score.tier.value)
    logger.info("  Breakdown - SEO: %.0f, Visibility: %.0f, Google Ads: %.0f, "
                "LinkedIn: %.0f, Content: %.0f, Meta: %.0f, YouTube: %.0f",
                score.signal_scores.seo, score.signal_scores.visibility_gap,
                score.signal_scores.google_ads, score.signal_scores.linkedin_jobs,
                score.signal_scores.content, score.signal_scores.meta_ads,
                score.signal_scores.youtube)
    _save_json(output_dir, "03_score.json", score.model_dump(mode='json'))

    # Step 4/6: Discovery prompt generation
    logger.info("Step 4/6: Discovery prompt generation")
    prompts = []
    if not skip_prompts:
        prompts = generator.generate_discovery_prompts(research, n_prompts=n_prompts, language=language)
        logger.info("  Generated %d discovery prompts", len(prompts))
    else:
        logger.info("  Skipped")
    _save_json(output_dir, "04_prompts.json", [p.model_dump(mode='json') for p in prompts])

    # Step 5/6: PDF report generation
    logger.info("Step 5/6: PDF report generation")
    report_bytes = b''
    if not skip_report and visibility_metrics:
        report_path = output_report_path or str(output_dir / "05_report.pdf")
        report_bytes = builder.build_outreach_report(
            company_research=research,
            visibility_metrics=visibility_metrics,
            signals=signals,
            output_path=report_path
        )
        logger.info("  Report generated (%d bytes) -> %s", len(report_bytes), report_path)
    else:
        if skip_report:
            logger.info("  Skipped")
        else:
            logger.info("  Skipped (no visibility_metrics provided)")

    # Step 6/6: Outreach message generation
    logger.info("Step 6/6: Outreach message generation")
    messages = {}
    if not skip_messages and visibility_metrics:
        messages = message_generator.generate_personalized_message(
            company_research=research,
            visibility_metrics=visibility_metrics,
            signals=signals,
            contact_id=contact_id,
            contact_name=contact_name,
            language=language,
        )
        logger.info("  Generated messages for channels: %s", list(messages.keys()))
    else:
        if skip_messages:
            logger.info("  Skipped")
        else:
            logger.info("  Skipped (no visibility_metrics provided)")
    _save_json(output_dir, "06_messages.json", messages)

    # Save final combined result
    result = {
        "company": company_name,
        "domain": domain,
        "research": research.model_dump(mode='json'),
        "signals": signals.model_dump(mode='json'),
        "score": score.model_dump(mode='json'),
        "prompts": [p.model_dump(mode='json') for p in prompts],
        "messages": messages,
        "report_generated": len(report_bytes) > 0,
        "output_dir": str(output_dir),
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    _save_json(output_dir, "result.json", result)

    logger.info("=" * 60)
    logger.info("Pipeline complete. Results saved to %s", output_dir)
    logger.info("=" * 60)

    return result


def main():
    """CLI entry point for the B2B outreach pipeline."""
    parser = argparse.ArgumentParser(description="B2B Outreach Pipeline")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--domain", required=True, help="Company domain (e.g. stripe.com)")
    parser.add_argument("--industry", default="Unknown", help="Company industry")
    parser.add_argument("--basic-signals", action="store_true", help="Skip extended signal analysis")
    parser.add_argument("--skip-research", action="store_true", help="Skip website research")
    parser.add_argument("--skip-prompts", action="store_true", help="Skip prompt generation")
    parser.add_argument("--skip-report", action="store_true", help="Skip report generation")
    parser.add_argument("--skip-messages", action="store_true", help="Skip outreach message generation")
    parser.add_argument("--n-prompts", type=int, default=3, help="Number of discovery prompts to generate")
    parser.add_argument("--contact-id", help="Supabase contact ID for message personalization")
    parser.add_argument("--contact-name", help="Contact name for message personalization")
    parser.add_argument("--report-path", help="Output path for PDF report")
    parser.add_argument("--research-path", help="Path to pre-built 01_research.json (from /research-company skill)")
    parser.add_argument("--country", help="ISO country code for signal detection (e.g. CL, MX, US). Auto-detected from research if omitted")
    parser.add_argument("--language", default="es", choices=["es", "en", "pt"], help="Language for prompts and messages (default: es)")
    parser.add_argument("--output", help="Output JSON file path (in addition to output dir)")

    args = parser.parse_args()

    result = run_pipeline(
        company_name=args.company,
        domain=args.domain,
        industry=args.industry,
        include_extended_signals=not args.basic_signals,
        skip_research=args.skip_research,
        skip_prompts=args.skip_prompts,
        skip_report=args.skip_report,
        skip_messages=args.skip_messages,
        n_prompts=args.n_prompts,
        contact_id=args.contact_id,
        contact_name=args.contact_name,
        output_report_path=args.report_path,
        research_path=args.research_path,
        country=args.country,
        language=args.language,
    )

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2, default=str)


if __name__ == "__main__":
    main()
