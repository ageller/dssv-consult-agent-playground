"""Shared helpers for the CLI scripts.

Keeps the individual scripts thin. The scripts import the SAME
``consult.retrieval`` functions the MCP server uses, so the CLI and MCP arms
of the comparison behave identically — only the calling convention differs.
"""

from __future__ import annotations

import json
from typing import Any


def print_result(data: Any, as_json: bool) -> None:
    """Emit a result either as JSON or as a readable text block."""
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    if isinstance(data, list):
        if not data:
            print("(no results)")
            return
        for i, rec in enumerate(data, start=1):
            print(f"--- result {i} " + "-" * 40)
            _print_record(rec)
    elif isinstance(data, dict):
        _print_record(data)
    else:
        print(data)


def _print_record(rec: dict) -> None:
    for key, val in rec.items():
        if isinstance(val, list):
            val = ", ".join(str(v) for v in val) if val else "(none)"
        if val is None:
            val = "(none)"
        print(f"  {key:22}: {val}")
