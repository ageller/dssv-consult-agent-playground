# Consult Triage & Knowledge Assistant

## Project Goal

Build a local, agentic system that triages incoming data science consult
requests by surfacing similar past consults. Everything runs locally — Ollama
for the model, a local MCP server for retrieval tools, and Continue (the VS
Code extension) as the initial harness. No data leaves the machine: no external
APIs, no cloud calls.

This is a learning project about building agentic systems (tool-calling,
retrieval-as-tool, MCP servers vs. plain CLI tools) as much as a practical
consulting tool. Favor clarity and inspectability over cleverness — I want to
see exactly what the agent decided to call and why.

The specific thing I want to learn: whether a small local model (8–9B) is more
reliable calling tools via a structured schema (MCP / Ollama native
tool-calling) or via reading a README and invoking plain CLI scripts through
Bash (the "skip MCP" approach). So the retrieval logic is implemented **once**
as plain Python functions, then exposed both ways (see Components) — both
tested against the same data and the same models.

## Source Data

A local Excel file in `consult_data/` with historical consult records. Columns:

```
Smartsheet Row ID, NetID, Created, Status, First Name, Last Name, Email,
Affiliation, Role, Work for, Brief Description, Python, R, SQL/Databases,
Statistics, Stata, SPSS, Data Visualization, Geographic Data,
Data Management, Qualitative Analysis, Something Else/I'm Not Sure,
Drop-in, Library Consult, AI-generated code, Initial Response by,
Initial Response Date, Assigned to, Status Notes, Notes, Outcome, Survey,
Quest
```

Data-quality notes:
- `Brief Description` is client-filled and almost always present — the primary
  field for semantic matching.
- `Status Notes`, `Notes`, `Outcome` are consultant-filled and **sometimes
  incomplete**. Ingestion must tolerate missing values here, not error or drop
  rows.
- The topic columns (Python … Something Else/I'm Not Sure) are `TRUE`/blank —
  inspect actual values before writing normalization logic; don't guess.
- Watch for whitespace/encoding artifacts in free-text fields.

## Privacy Note

The source file contains real names, emails, and NetIDs. As a rule, keep these
**out of embedded text and out of anything passed as a tool-call argument or
reasoning input to the model.** Aggregate by Affiliation/Role/topic instead of
by name when summarizing patterns.

The one deliberate exception is `get_consult_detail(id)`, which returns the full
record (including PII) when a specific consult is explicitly requested by id.
This is intentional — I sometimes need the actual detail, not an anonymized
summary — not an oversight. All *other* tools must stay PII-free, including the
ids they surface, which must be internal identifiers only (no names/emails
encoded into them).

**IMPORTANT — PII must never leave my machine.** You (Claude) must never send
any of this data to your server. If you need to inspect data on your server,
exclude the `NetID`, `First Name`, `Last Name`, `Email`, and `Work for`
columns. Only local (Ollama) models may ever access PII, and only local models
may ever run `get_consult_detail(id)`.

## Components

Build order and testing-specific steps live under the phases below; this
section is the reference for *what* each piece is.

1. **Ingestion** (`ingest.py`): read the Excel file, normalize each row into:
   ```
   {
     id, date, affiliation, role, work_for, status,
     brief_description, notes_combined (Status Notes + Notes + Outcome,
       joined with clear separators, empty-tolerant),
     topics (list, derived from checkbox columns),
     assigned_to, initial_response_by, initial_response_date,
     is_incomplete (bool — true if none of Status Notes/Notes/Outcome filled)
   }
   ```
   Output to a local SQLite database (or JSON — propose one and explain
   tradeoffs briefly before proceeding).

2. **Embedding**: embed `brief_description` + `notes_combined` (when present)
   via Ollama's embedding endpoint with `nomic-embed-text`. Store vectors
   alongside records — `sqlite-vec` preferred so everything lives in one file,
   but propose alternatives if there's a good reason.

3. **Retrieval functions** (plain Python, importable, independently testable):
   - `get_consult_detail(id)` — full record for one consult, including all PII.
   - `search_past_consults(query, k=5)` — semantic search; returns matches with
     brief_description, topics, affiliation/role, notes_combined (if present),
     and an `is_incomplete` flag. No PII, but includes an internal id usable
     with `get_consult_detail`.
   - `list_recent_consults(n=10)` — chronological browse, same output level as
     `search_past_consults` (no PII).
   - `summarize_similar_requests(query, k=10)` — runs search, then aggregates by
     affiliation/role/topic to answer "who else has asked about this" without
     naming individuals (no PII).
   - `create_figure(...)` — given search/summarize results, generate a
     matplotlib figure (e.g. a bar chart of similar consults by affiliation, or
     a timeline of related requests) and return the `matplotlib.figure.Figure`.
     PII-free like the other aggregate tools — no names in charts. How the
     figure surfaces depends on the harness (see phases): the CLI arm writes a
     PNG to disk; the FastAPI dashboard streams it as an inline PNG; Gradio
     renders the Figure inline with no extra plumbing.

4. **MCP server**: expose the retrieval functions as MCP tools (Python,
   official `mcp` SDK).

5. **CLI comparison harness**: expose the *same* functions as small independent
   CLI scripts (e.g. `search-consults.py --query "..." --k 5`), each with clear
   `--help` text, plus one README.md documenting them all. This is the other
   arm of the comparison from the Project Goal, not a fallback. Keep the scripts
   thin wrappers around the shared functions so only the calling convention
   differs from the MCP arm.

6. **Continue harness config**: a workspace-scoped Continue config at
   `.continue/agents/consult-assistant.yaml` (not the global
   `~/.continue/config.yaml` — keep this project's setup separate). Register the
   MCP server there, pointed at a local Ollama model (`qwen3.5:9b`,
   `gemma4:e2b`, `llama3.1:8b`, `granite4.1:8b` available — default to
   `qwen3.5:9b` unless there's a reason to prefer another).

## Testing Phase

### 1. Initial setup (Continue + CLI)

**Purpose**: build the agent system and test both the MCP and CLI arms
interactively in VS Code (extensions + terminal).

#### Build Order

1. Confirm actual checkbox/data values by inspecting a sample of real rows
   before writing normalization logic. Exclude PII from anything sent to your
   server.
2. Build Components 1→5 in order: ingestion + store, embedding, retrieval
   functions (including `create_figure`), MCP server, CLI scripts + README.
   In this phase `create_figure` won't render inline (CLI writes a PNG; Continue
   may or may not display it) — the test here is whether the model *chooses to
   call it correctly*; inline rendering lands in the FastAPI/Gradio phases.
3. Wire the MCP server into `.continue/agents/consult-assistant.yaml`
   (Component 6).
4. Update the project root `README.md` with a short description of the project.
5. Give me a handful of real queries to try in Continue and in the CLI/Bash
   version — don't run them; I'll do that manually.
6. Stop and review with me before adding anything beyond this.

### 2. Add the Pi harness

**Purpose**: set up Pi (https://pi.dev) as a second harness for testing the
CLI/Bash arm.

#### Build Order

1. Check if Pi is available on PATH.  If not, install Pi: 
   `curl -fsSL https://pi.dev/install.sh | sh`, then verify it's on PATH.
2. Write an `AGENTS.md` at the project root (Pi loads this automatically at
   startup). Document the CLI scripts from Component 5 — one section per script,
   with usage syntax and a short description, in the same style as their README.
   Reuse that README's content rather than rewriting it, so the two stay in
   sync.
3. Configure Pi to use Ollama as the provider, defaulting to `qwen3.5:9b` (match
   `.continue/agents/consult-assistant.yaml`), pointed at my local Ollama
   instance. Add whatever config file Pi needs (check its docs for the
   provider/model format — likely `models.json` or similar) rather than guessing
   the syntax.
4. Give me 5–6 plain-language test queries (not CLI syntax) mirroring the ones
   in the root `README.md`. Don't run them; I'll run them in Pi's TUI and report
   back.
5. Stop and review with me before adding anything beyond this.

### 3. FastAPI comparison dashboard

**Purpose**: a local web UI that runs one input through multiple arms
side-by-side so I can inspect what each does. A working tool for testing, not a
polished product — prioritize visibility over aesthetics. Same PII rules apply
(see Privacy Note); no relaxing them just because it's local.

#### Build Order

1. One FastAPI endpoint accepting the query + selected model. Run each arm as a
   parallel async task (not sequential, so timing comparisons are fair), and
   stream all arms' events over Server-Sent Events tagged by arm
   (`{"arm": "mcp", "type": "tool_call", ...}`). Import the retrieval functions
   directly — no need to go through the MCP transport or shell out to the CLI
   scripts unless that's meaningfully easier; the point is comparing how the
   model calls tools, not re-implementing transports per arm.
2. Arms shown side by side: MCP and CLI/Bash. Add Pi as a third column only if
   it's not disproportionately hard given it runs as its own process — use its
   `--mode json`/RPC output, not TUI screen-scraping. If Pi becomes a time sink,
   ship with two columns and add it later; say so rather than forcing it.
3. Minimal frontend: plain HTML/JS, one `EventSource` routing events to the
   right column by the `arm` field (no framework). Each column streams, in
   order: every tool call with its arguments, every tool result, any
   intermediate reasoning/text, and the final answer. `create_figure` results
   render as an inline PNG here.
4. A shared model-picker dropdown across all arms (for fair comparison):
   `qwen3.5:9b`, `gemma4:e2b`, `llama3.1:8b`, `granite4.1:8b`.
5. A per-column stats panel showing whatever's cheaply available: total
   wall-clock time, tool-call count, retries/errors, token counts if Ollama's
   response metadata provides them. Surface only real metrics; say clearly if
   one isn't available for a given arm.
6. Stop and review with me before adding anything beyond this.

## Final Product (Post-Testing): Gradio App

**Do not start this section until the testing phase is complete and I've told
you which arm (MCP vs. CLI, possibly Pi) and which model won.** This is the
"boring and stable" version for daily use — a different design goal from the
FastAPI dashboard.

**Purpose**: a stable single-file chat app on the winning arm + model, not
another experiment.

#### Build Order

1. A `gr.ChatInterface` app, hardcoded (or defaulted) to the winning model and
   winning tool-calling approach. Keep the model dropdown only if genuinely
   useful, not as a leftover from testing. No side-by-side, no per-arm stats.
2. Wire in the retrieval tools, including `create_figure` (already built in the
   initial phase) — Gradio renders the returned `matplotlib.figure.Figure`
   inline in the chat with no extra plumbing.
3. Keep tool-call visibility lightweight and unobtrusive if it's cheap (e.g. a
   collapsed/expandable step in the chat rather than a whole column). A
   lightweight trace is fine; I don't need the full testing-UI introspection
   here.
4. Same PII rules apply (see Privacy Note).

Constraints: single file, minimal dependencies, meant to leave running and just
use. If the underlying agent logic needs debugging, go back to the FastAPI
dashboard or Pi/Continue rather than adding debug tooling to this app.

## Working Conventions

- Use `uv` for environment management — create the usual `pyproject.toml` etc. Prefer standard library /
  minimal dependencies where reasonable.
- Ask before assuming file paths, exact column values, or schema choices where
  the data hasn't been inspected yet — don't guess when you could check.
- Keep ingestion and embedding as separate, independently runnable scripts (not
  bundled into the MCP server) so they can be re-run/debugged in isolation.
- Flag any row-level data-quality issues during ingestion (missing Brief
  Description, ambiguous checkbox values, encoding issues) rather than silently
  dropping or guessing.
