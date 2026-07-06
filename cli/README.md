# Consult tools — CLI (the "skip MCP" arm)

Four small command-line scripts for triaging consult requests against past
consults. They are **thin wrappers** around the same `consult.retrieval`
functions the MCP server uses, so results are identical between the two —
only the calling convention differs. This is the "read a README, invoke plain
scripts via Bash" alternative to structured MCP tool-calling (see the project
`CLAUDE.md` → Project Goal).

Everything runs **locally**: retrieval reads the local SQLite database
(`consult_data/consult.db`) and embeds queries with a local Ollama model
(`nomic-embed-text`). No data leaves the machine.

## Prerequisites

The database must already be built (run once, from the project root):

```bash
uv run consult-ingest    # Excel -> normalized rows in SQLite
uv run consult-embed     # embed each record's text into sqlite-vec (~1 min)
```

Ollama must be running locally (`ollama serve`) with `nomic-embed-text` pulled.

## The four tools

All commands are run from the **project root**. Add `--json` to any of them
for machine-readable output instead of the text format shown here.

### 1. Search similar past consults (PII-free)

```bash
uv run cli/search-consults.py --query "spatial regression in R" --k 5
```
Returns the `k` most semantically similar consults: internal `id`, date,
status, affiliation, role, topics, brief description, consultant notes (if
any), `is_incomplete` flag, and a `similarity` score in [0, 1]. No names or
emails.

### 2. List recent consults (PII-free)

```bash
uv run cli/list-recent-consults.py --n 10
```
The most recent consults chronologically. Same fields as search (no
similarity score).

### 3. Summarize who has asked about a topic (PII-free, no names)

```bash
uv run cli/summarize-similar-requests.py --query "survey data analysis" --k 15
```
Searches, then aggregates the matches by affiliation / role / topic / status
(counts only — never names individuals). Also returns the `match_ids` so you
can drill into a specific one.

### 4. Full detail for one consult — **INCLUDES PII**

```bash
uv run cli/get-consult-detail.py --id ss_2242
```
The complete record for one consult **including the client's name, email,
NetID, and PI ("work for")**. This is the one deliberate PII exception; use it
only for a specific `id` you got from one of the tools above, and only on your
local machine.

## Flags

| flag | tools | meaning |
|------|-------|---------|
| `--query` / `-q` | search, summarize | natural-language query (required) |
| `--k` | search, summarize | number of matches (default 5 / 10) |
| `--n` | list-recent | number of recent consults (default 10) |
| `--id` | get-detail | internal consult id, e.g. `ss_2242` (required) |
| `--json` | all | raw JSON output |

Run any script with `--help` for its full usage.
