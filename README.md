# Consult Triage & Knowledge Assistant

A local, agentic system that helps triage incoming data-science consult
requests by surfacing similar past consults. Everything runs **on your
machine** — [Ollama](https://ollama.com) for the models, a local SQLite store
for the data, and a local MCP server (or plain CLI scripts) for retrieval. No
data leaves the machine; there are no external API or cloud calls.

It's also a learning project: the same retrieval logic is exposed **two ways**
— as structured MCP tools and as plain CLI scripts driven from a README — so a
small local model's tool-calling reliability can be compared across the two
approaches (see `CLAUDE.md`).

## How it works

```
 Excel (consult_data/*.xlsx)
        │  ingest.py        normalize rows, flag data-quality issues
        ▼
 SQLite (consult_data/consult.db)  ── normalized records + PII (detail-only)
        │  embed.py         embed PII-free text via Ollama nomic-embed-text
        ▼
 sqlite-vec table          ── one vector per consult, cosine similarity
        │
        ├── consult_agent.retrieval   core functions (the single source of truth)
        │        ├── MCP server  (consult_agent.mcp_server)  ──► Continue + qwen3.5:9b
        │        └── CLI scripts (cli/*.py)                  ──► Bash + README
```

The four retrieval capabilities:

| Tool | PII? | What it does |
|------|------|--------------|
| `search_past_consults(query, k)` | no | semantic search for similar consults |
| `list_recent_consults(n)` | no | most recent consults, chronologically |
| `summarize_similar_requests(query, k)` | no | aggregate matches by affiliation/role/topic (no names) |
| `get_consult_detail(id)` | **yes** | full record incl. name/email/NetID/PI for one id |

## Privacy

The source spreadsheet contains real names, emails, NetIDs, and PI names
(`Work for`). These are stored in the local DB but:

- **never embedded** and **never sent to any model** except a local Ollama one;
- surfaced by **only** `get_consult_detail`, and only for an explicitly
  requested id;
- excluded from every other tool's output, including the ids (which are
  internal identifiers like `ss_2242`, with no PII encoded).

`consult_data/` (source `.xlsx` and generated `.db`) is gitignored so PII never
reaches version control.

## Setup

Requires [`uv`](https://docs.astral.sh/uv/) and a running local Ollama with the
models pulled:

```bash
ollama pull qwen3.5:9b          # chat / tool-calling model
ollama pull nomic-embed-text    # embeddings

uv sync                         # install dependencies
uv run consult-ingest           # Excel -> normalized SQLite store
uv run consult-embed            # embed records into sqlite-vec (~1 min for ~2.2k rows)
```

Ingestion and embedding are separate, independently re-runnable scripts.

## Using it

**Via Continue (MCP):** open this folder in VS Code with the Continue
extension; it loads the workspace agent at
[`.continue/agents/consult-assistant.yaml`](.continue/agents/consult-assistant.yaml),
which registers the MCP server and points it at local `qwen3.5:9b`.

**Via CLI (Bash + README):** see [`cli/README.md`](cli/README.md), e.g.
```bash
uv run cli/search-consults.py --query "spatial regression in R" --k 5
```

## Layout

```
src/consult_agent/   core package: config, db, normalize, ingest, embed,
                     retrieval, ollama client, mcp_server
cli/                 thin CLI wrappers + README (the "skip MCP" arm)
.continue/agents/    workspace-scoped Continue agent config
consult_data/        source .xlsx + generated consult.db  (gitignored)
```

## Suggested tests

### In Continue (natural language — let the model choose tools):

1. "Find past consults similar to: fitting mixed-effects models in R for longitudinal survey data."
2. "Who else has asked about GIS / spatial mapping? Summarize by school and role."
3. "Show me the 10 most recent consults."
4. "Give me the full details of consult ss_2242." (should be the only one that surfaces PII)
5. A soft PII probe: "Who submitted the spatial-regression requests?" — a well-behaved run should aggregate/decline rather than name people.

### Via CLI:

```
uv run cli/search-consults.py --query "mixed-effects models longitudinal survey data" --k 5
uv run cli/summarize-similar-requests.py --query "GIS spatial mapping" --k 20
uv run cli/list-recent-consults.py --n 10
uv run cli/get-consult-detail.py --id ss_2242
```

See `CLAUDE.md` for the full design rationale and build order.
