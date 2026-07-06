#!/usr/bin/env python3
"""Semantic search over past consults (PII-free).

Thin CLI wrapper around consult.retrieval.search_past_consults.

Examples:
    uv run cli/search-consults.py --query "spatial regression in R"
    uv run cli/search-consults.py --query "power analysis" --k 8 --json
"""

from __future__ import annotations

import argparse
import sys

from _common import print_result

from consult_agent import retrieval


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--query", "-q", required=True, help="natural-language search query")
    p.add_argument("--k", type=int, default=5, help="number of matches to return (default 5)")
    p.add_argument("--json", action="store_true", help="output raw JSON instead of text")
    args = p.parse_args()

    results = retrieval.search_past_consults(args.query, k=args.k)
    print_result(results, args.json)
    if not results and not args.json:
        print("(no matches — is the DB embedded? run: uv run consult-embed)", file=sys.stderr)


if __name__ == "__main__":
    main()
