"""Consult Triage & Knowledge Assistant.

A local, agentic system to triage incoming data-science consult requests by
surfacing similar past consults. Runs entirely locally (Ollama + SQLite).

Layout:
- config.py     : paths, model names, constants (the one place to change them)
- ollama.py     : thin client for the local Ollama HTTP API (embeddings)
- db.py         : SQLite connection helpers + sqlite-vec loading + schema
- normalize.py  : Excel row -> normalized record (pure, testable)
- ingest.py     : script — Excel file -> normalized rows in SQLite
- embed.py      : script — embed records -> vectors in sqlite-vec
- retrieval.py  : core retrieval functions (plain Python, PII-safe)
- mcp_server.py : MCP server exposing the retrieval functions as tools

The retrieval logic lives once in retrieval.py; both the MCP server and the
CLI scripts in ../../cli are thin wrappers around it, so behaviour is
identical across the two interfaces (see CLAUDE.md "CLI comparison harness").
"""
