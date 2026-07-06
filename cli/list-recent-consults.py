#!/usr/bin/env python3
"""List the most recent consults chronologically (PII-free).

Thin CLI wrapper around consult.retrieval.list_recent_consults.

Examples:
    uv run cli/list-recent-consults.py
    uv run cli/list-recent-consults.py --n 20 --json
"""

from __future__ import annotations

import argparse

from _common import print_result

from consult_agent import retrieval


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--n", type=int, default=10, help="number of recent consults (default 10)")
    p.add_argument("--json", action="store_true", help="output raw JSON instead of text")
    args = p.parse_args()

    print_result(retrieval.list_recent_consults(n=args.n), args.json)


if __name__ == "__main__":
    main()
