"""MCP server exposing the four retrieval functions as tools.

Thin wrappers around consult.retrieval — no logic lives here beyond
tool registration and docstrings, so behaviour matches the CLI exactly.

Run over stdio (how Continue launches it):

    uv run consult-mcp
    uv run python -m consult_agent.mcp_server

Privacy: three of the four tools are PII-free by construction (they call the
PII-free retrieval functions). Only get_consult_detail returns PII, and only
for an explicitly supplied id. Because this server talks only to a local
Ollama model via Continue, no data leaves the machine.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import retrieval

mcp = FastMCP("consult-assistant")


@mcp.tool()
def search_past_consults(query: str, k: int = 5) -> list[dict]:
    """Semantically search past data-science consults similar to `query`.

    Returns up to `k` matches, each with: internal `id` (use with
    get_consult_detail), `date`, `status`, `affiliation`, `role`, `topics`,
    `brief_description`, `notes_combined` (null if the consultant left no
    notes), `is_incomplete`, and a `similarity` score in [0,1]. Contains NO
    names, emails, or NetIDs.
    """
    return retrieval.search_past_consults(query, k=k)


@mcp.tool()
def list_recent_consults(n: int = 10) -> list[dict]:
    """List the `n` most recent consults chronologically (newest first).

    Same PII-free fields as search_past_consults (without a similarity score).
    """
    return retrieval.list_recent_consults(n=n)


@mcp.tool()
def summarize_similar_requests(query: str, k: int = 10) -> dict:
    """Summarize who has asked about something like `query`, WITHOUT naming anyone.

    Runs a semantic search over the top `k` matches and aggregates them by
    affiliation, role, topic, and status (counts only). Also returns the
    internal `match_ids` so a specific consult can be inspected with
    get_consult_detail. Use this for "who else has asked about X" questions.
    """
    return retrieval.summarize_similar_requests(query, k=k)


@mcp.tool()
def get_consult_detail(consult_id: str) -> dict | None:
    """Return the FULL record for one consult by its internal `id`, INCLUDING PII.

    This is the only tool that returns personal information (name, email,
    NetID, PI/"work for"). Call it only when the full detail of a specific
    consult is explicitly needed, using an `id` obtained from one of the other
    tools. Returns null if the id is unknown.
    """
    return retrieval.get_consult_detail(consult_id)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
