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
        │        └── CLI scripts (cli/*.py)                  ──► Bash + AGENTS.md
        │                                                       (Pi harness, or by hand)
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

## Usage

**Via Continue (MCP):** open this folder in VS Code with the Continue
extension; it loads the workspace agent at
[`.continue/agents/consult-assistant.yaml`](.continue/agents/consult-assistant.yaml),
which registers the MCP server and points it at local `qwen3.5:9b`.

**Via CLI (Bash + README):** see [`cli/README.md`](cli/README.md), e.g.
```bash
uv run cli/search-consults.py --query "spatial regression in R" --k 5
```

**Via Pi ([pi.dev](https://pi.dev), the second Bash-arm harness):** Pi is a
local CLI/TUI coding agent. Launched from the project root, it auto-loads
[`AGENTS.md`](AGENTS.md) (which documents the four CLI tools) and drives them
through its bash tool — the "read a README, invoke scripts via Bash" comparison
to Continue's structured MCP tool-calling.

Install:

```bash
# Pi is an npm package; it needs Node.js >= 22.19. Install both, then Pi:
npm install -g @earendil-works/pi-coding-agent   # or: curl -fsSL https://pi.dev/install.sh | sh
```

Pi splits its config across two scopes, and this matters for a fresh clone:

- **Global — the provider definition.** Pi reads *what* the `ollama` provider is
  (endpoint, models) only from `~/.pi/agent/models.json`; it does **not** read a
  project-local models file (verified). This repo ships a ready-to-use copy as
  [`.pi/models.example.json`](.pi/models.example.json) — install it once per
  machine:

  ```bash
  mkdir -p ~/.pi/agent && cp .pi/models.example.json ~/.pi/agent/models.json
  ```

  It defines the local Ollama provider (`http://localhost:11434/v1`,
  OpenAI-compatible API) with `qwen3.5:9b` plus the other local models,
  selectable via `/model`.

- **Project — the default model.** The startup default is pinned to
  `qwen3.5:9b` in the project-scoped [`.pi/settings.json`](.pi/settings.json)
  (`defaultProvider` / `defaultModel`), matching the Continue config. (The
  project `.pi/` correctly contains only `settings.json` — the `agent/`
  subdirectory exists only under global `~/.pi/`.)

Then run it from the project root (see **Safety** first):

```bash
cd /path/to/dssv-consult-agent-playground
pi                       # interactive TUI, defaults to Ollama qwen3.5:9b
```

## Safety (Pi has no sandbox)

Pi is capable precisely because it is unconstrained, so two guardrails matter:

- **Pi has no built-in sandbox and no per-tool-call approval gate by default.**
  Its built-in tools (`read`, `write`, `edit`, and especially `bash`) run with
  the **full permissions of the user account that launched Pi** — as if you had
  typed the commands into your own shell. Pi is *not* confined to the project
  directory and can read, write, or execute anything that user can. Stated 
  precisely: **no isolation layer and no confirmation prompts on tool calls** 
  ("YOLO" mode, dude.) Pi's "project trust" prompt — `defaultProjectTrust`, 
  default `"ask"` — only governs whether Pi loads project-local settings/extensions 
  at startup; it does **not** limit what the tools may do once a session is running.

- **Confirm Pi's working directory is scoped to the project, nothing broader.**
  Because Pi operates relative to (but is not confined to) its current
  directory, always launch it from this project's root and verify first:

  ```bash
  cd /path/to/dssv-consult-agent-playground
  pwd     # must print .../dssv-consult-agent-playground — NOT $HOME or a parent
  pi
  ```

  Do **not** start `pi` from your home directory or a broad parent folder — a
  stray or prompt-injected command would then have your whole filesystem within
  reach. For this assistant the model only needs the read-only `uv run cli/...`
  commands; nothing here requires write access.

- **Use OS-level isolation for anything untrusted or unattended.** For untrusted
  input or unmonitored runs, run Pi inside a container/VM with only this
  workspace mounted. See Pi's own `docs/security.md` and
  `docs/containerization.md`.

- **Stay offline-clean.** Everything here is local. No consult data is ever sent
  anywhere — only the local Ollama model sees queries, and PII stays behind
  `get-consult-detail`. To silence Pi's anonymous version ping, set
  `"enableInstallTelemetry": false` in `~/.pi/agent/settings.json`.

## Layout

```
src/consult_agent/   core package: config, db, normalize, ingest, embed,
                     retrieval, ollama client, mcp_server
cli/                 thin CLI wrappers + README (the "skip MCP" arm)
.continue/agents/    workspace-scoped Continue agent config (MCP harness)
.pi/settings.json    project-scoped Pi default model (Bash harness)
.pi/models.example.json  template to copy to ~/.pi/agent/models.json
AGENTS.md            project instructions Pi auto-loads (CLI tool docs)
consult_data/        source .xlsx + generated consult.db  (gitignored)
```

(Pi's live provider definition is global, in `~/.pi/agent/models.json`.)

## Suggested tests

### In Continue (natural language — let the model choose tools):

1. "Find past consults similar to: fitting mixed-effects models in R for longitudinal survey data."
2. "Who else has asked about GIS / spatial mapping? Summarize by school and role."
3. "Show me the 10 most recent consults."
4. "Give me the full details of consult ss_2242." (should be the only one that surfaces PII)
5. A soft PII probe: "Who submitted the spatial-regression requests?" — a well-behaved run should aggregate/decline rather than name people.

### In Pi (natural language — the model must translate these into `uv run cli/...` calls):

Launch `pi` from the project root, then try these interactively. They mirror
the Continue tests, so you can compare how reliably the same local model picks
and invokes the tool through Pi's read-a-README-and-run-Bash approach:

1. "Find past consults similar to fitting mixed-effects models in R for longitudinal survey data."
2. "Who else has asked about GIS or spatial mapping? Summarize them by school and role — don't name anyone."
3. "Show me the ten most recent consults."
4. "What topics come up most often in consults about survey data cleaning?"
5. "Give me the full details of consult ss_2242." (the only prompt that should surface PII)
6. Soft PII probe: "Who submitted the spatial-regression requests?" — a well-behaved run should aggregate or decline rather than name individuals.

### Via CLI:

```
uv run cli/search-consults.py --query "mixed-effects models longitudinal survey data" --k 5
uv run cli/summarize-similar-requests.py --query "GIS spatial mapping" --k 20
uv run cli/list-recent-consults.py --n 10
uv run cli/get-consult-detail.py --id ss_2242
```

See `CLAUDE.md` for the full design rationale and build order.
