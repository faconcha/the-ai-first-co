import argparse
import sys

from products.cmo.flow import CMOFlow


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


def main():
    parser = argparse.ArgumentParser(description="The AI-First Co - Agent Products")
    subparsers = parser.add_subparsers(dest="product", help="Product to run")

    cmo_parser = subparsers.add_parser("cmo", help="Run the CMO content pipeline")
    cmo_parser.add_argument("--topic", required=True, help="Content topic")
    cmo_parser.add_argument("--audience", required=True, help="Target audience")
    cmo_parser.add_argument("--platform", default="linkedin", choices=["linkedin", "blog", "twitter", "instagram"], help="Target platform")
    cmo_parser.add_argument("--language", default="en", choices=["en", "es"], help="Content language")

    args = parser.parse_args()

    if args.product is None:
        parser.print_help()
        sys.exit(1)

    if args.product == "cmo":
        run_cmo(args)


if __name__ == "__main__":
    main()
