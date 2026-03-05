import argparse
import json
import sys

from products.cmo.flow import CMOFlow
from products.author_twin.claude import scrape as author_twin_scrape
from products.author_twin.claude import report as author_twin_report
from products.b2b_outreach.claude import run_pipeline as b2b_outreach_pipeline
from products.aeo_prospection.claude import run_prospection as aeo_prospection


PRODUCTS = {
    "cmo": CMOFlow,
}


def run_cmo(args):
    flow = CMOFlow()
    flow.state.topic = args.topic
    flow.state.audience = args.audience
    flow.state.platform = args.platform
    flow.state.language = args.language
    flow.kickoff()


def run_b2b_outreach(args):
    result = b2b_outreach_pipeline.run_pipeline(
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


def run_aeo_prospection(args):
    result = aeo_prospection.run_prospection(
        prospect_email=args.email,
        prompts=args.prompts,
        ai_models=args.models,
        n_executions=args.n_executions,
    )

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2, default=str)


def run_author_twin(args):
    if args.action == "scrape":
        author_twin_scrape.run_scrape(args.author)
    elif args.action == "report":
        author_twin_report.generate_report(args.author)


def main():
    parser = argparse.ArgumentParser(description="The AI-First Co - Agent Products")
    subparsers = parser.add_subparsers(dest="product", help="Product to run")

    cmo_parser = subparsers.add_parser("cmo", help="Run the CMO content pipeline")
    cmo_parser.add_argument("--topic", required=True, help="Content topic")
    cmo_parser.add_argument("--audience", required=True, help="Target audience")
    cmo_parser.add_argument("--platform", default="linkedin", choices=["linkedin", "blog", "twitter", "instagram"], help="Target platform")
    cmo_parser.add_argument("--language", default="en", choices=["en", "es"], help="Content language")

    at_parser = subparsers.add_parser("author-twin", help="Author twin knowledge builder")
    at_subparsers = at_parser.add_subparsers(dest="action", help="Action to run")

    scrape_parser = at_subparsers.add_parser("scrape", help="Scrape author content")
    scrape_parser.add_argument("--author", required=True, help="Author slug (folder name under authors/)")

    report_parser = at_subparsers.add_parser("report", help="Generate scraping report")
    report_parser.add_argument("--author", required=True, help="Author slug (folder name under authors/)")

    b2b_parser = subparsers.add_parser("b2b-outreach", help="B2B outreach: research, signal detection, lead scoring, report and message generation")
    b2b_parser.add_argument("--company", required=True, help="Company name")
    b2b_parser.add_argument("--domain", required=True, help="Company domain (e.g. stripe.com)")
    b2b_parser.add_argument("--industry", default="Unknown", help="Company industry")
    b2b_parser.add_argument("--basic-signals", action="store_true", help="Skip extended signal analysis (SEO, content, prospection)")
    b2b_parser.add_argument("--output", help="Output JSON file path (in addition to output dir)")
    b2b_parser.add_argument("--skip-research", action="store_true", help="Skip website research")
    b2b_parser.add_argument("--skip-prompts", action="store_true", help="Skip discovery prompt generation")
    b2b_parser.add_argument("--skip-report", action="store_true", help="Skip PDF report generation")
    b2b_parser.add_argument("--skip-messages", action="store_true", help="Skip outreach message generation")
    b2b_parser.add_argument("--n-prompts", type=int, default=3, help="Number of discovery prompts to generate")
    b2b_parser.add_argument("--contact-id", help="Supabase contact ID for message personalization")
    b2b_parser.add_argument("--contact-name", help="Contact name for message personalization")
    b2b_parser.add_argument("--report-path", help="Output path for PDF report file")
    b2b_parser.add_argument("--research-path", help="Path to pre-built 01_research.json (from /research-company skill)")
    b2b_parser.add_argument("--country", help="ISO country code for signal detection (e.g. CL, MX, US). Auto-detected from research if omitted")
    b2b_parser.add_argument("--language", default="es", choices=["es", "en", "pt"], help="Language for prompts and messages (default: es for LATAM)")

    aeo_parser = subparsers.add_parser("aeo-prospection", help="AEO prospection: run full AEO pipeline for a prospect")
    aeo_parser.add_argument("--email", required=True, help="Prospect email (PK in prospects table)")
    aeo_parser.add_argument("--prompts", nargs="+", help="Prompts to test (space-separated)")
    aeo_parser.add_argument("--models", nargs="+", default=["chatgpt", "perplexity"], help="AI models to test")
    aeo_parser.add_argument("--n-executions", type=int, default=3, help="Executions per model (1-10)")
    aeo_parser.add_argument("--output", help="Output JSON file path")

    args = parser.parse_args()

    if args.product is None:
        parser.print_help()
        sys.exit(1)

    if args.product == "cmo":
        run_cmo(args)
    elif args.product == "author-twin":
        run_author_twin(args)
    elif args.product == "b2b-outreach":
        run_b2b_outreach(args)
    elif args.product == "aeo-prospection":
        run_aeo_prospection(args)


if __name__ == "__main__":
    main()
