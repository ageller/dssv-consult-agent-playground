#!/usr/bin/env python3
"""Aggregate summary of who has asked about a topic (PII-free, no names).

Thin CLI wrapper around consult.retrieval.summarize_similar_requests.

Examples:
    uv run cli/summarize-similar-requests.py --query "survey data analysis"
    uv run cli/summarize-similar-requests.py --query "GIS mapping" --k 20 --json
"""

from __future__ import annotations

import argparse

from _common import print_result

from consult_agent import retrieval


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--query", "-q", required=True, help="natural-language topic query")
    p.add_argument("--k", type=int, default=10, help="matches to aggregate over (default 10)")
    p.add_argument("--json", action="store_true", help="output raw JSON instead of text")
    args = p.parse_args()

    print_result(retrieval.summarize_similar_requests(args.query, k=args.k), args.json)


if __name__ == "__main__":
    main()
