#!/usr/bin/env python3
"""Full record for one consult by internal id — INCLUDES PII.

Thin CLI wrapper around consult.retrieval.get_consult_detail. This is the one
deliberate PII exception: it returns the client's name, email, NetID, and PI
("work for"). Use it only for a specific id you got from one of the other
tools, and only on your local machine.

Examples:
    uv run cli/get-consult-detail.py --id ss_2242
    uv run cli/get-consult-detail.py --id ss_2242 --json
"""

from __future__ import annotations

import argparse
import sys

from _common import print_result

from consult_agent import retrieval


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--id", required=True, help="internal consult id, e.g. ss_2242")
    p.add_argument("--json", action="store_true", help="output raw JSON instead of text")
    args = p.parse_args()

    detail = retrieval.get_consult_detail(args.id)
    if detail is None:
        print(f"No consult found with id {args.id!r}", file=sys.stderr)
        sys.exit(1)
    print_result(detail, args.json)


if __name__ == "__main__":
    main()
