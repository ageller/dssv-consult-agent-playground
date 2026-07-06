# Consult Triage & Knowledge Assistant

## Project Goal

Build a local, agentic system that helps triage incoming data science consult 
requests by surfacing similar past consults. This runs entirely locally: 
Ollama for the model, a local MCP server for retrieval tools, and Continue 
(VS Code extension) as the initial harness for talking to the agent. 
No data leaves the machine — no external APIs, no cloud calls.

This is a learning project about building agentic systems (tool-calling,
retrieval-as-tool, MCP servers vs. plain CLI tools) as much as it is a
practical tool for my consulting work. Favor clarity and inspectability over 
cleverness; I want to be able to see exactly what the agent decided to call 
and why.

A specific thing I want to learn from this project: whether a small local
model (8-9B) is more reliable calling tools via a structured schema (MCP /
Ollama native tool-calling) or via reading a README and invoking plain CLI
scripts through Bash (the "skip MCP" approach). The retrieval logic should
therefore be implemented once as plain Python functions, then exposed two
ways — see "CLI comparison harness" below — so both can be tested against
the same underlying data and the same models.

## Source Data

A local Excel file in the `consult_data` directory containing
historical consult records with these columns:

```
Smartsheet Row ID, NetID, Created, Status, First Name, Last Name, Email,
Affiliation, Role, Work for, Brief Description, Python, R, SQL/Databases,
Statistics, Stata, SPSS, Data Visualization, Geographic Data,
Data Management, Qualitative Analysis, Something Else/I'm Not Sure,
Drop-in, Library Consult, AI-generated code, Initial Response by,
Initial Response Date, Assigned to, Status Notes, Notes, Outcome, Survey,
Quest
```

Notes on data quality :
- `Brief Description` is client-filled and should almost always be present —
  this is the primary field for semantic matching.
- `Status Notes`, `Notes`, `Outcome` are filled in by consultants and are
  **sometimes incomplete**. Ingestion must tolerate missing values in these
  fields rather than erroring or dropping rows.
- The topic columns (Python, R, SQL/Databases, Statistics, Stata, SPSS, Data
  Visualization, Geographic Data, Data Management, Qualitative Analysis,
  Something Else/I'm Not Sure) are `TRUE`/blank — inspect actual
  before writing normalization logic; don't guess.
- Watch for whitespace/encoding artifacts in free-text fields.

## Privacy Note

The source file contains real names, emails, and NetIDs. As a general rule,
keep these fields **out of embedded text and out of anything passed as a
tool-call argument or reasoning input to the model.** Aggregate by
Affiliation/Role/topic instead of by name when summarizing patterns.

The one deliberate exception is `get_consult_detail(id)`, which returns the
full record including PII when a specific consult is explicitly requested by
id — see tool list below. This is an intentional design choice (I sometimes
need the actual detail, not just an anonymized summary), not an oversight.
All *other* tools must remain PII-free, including the ids they surface,
which should be internal identifiers only (no names/emails encoded into
them).

**IMPORTANT**:
PII data should never leave my machine.  Therefore you (Claude) should never send
any of this data to your server.  If you need to inspect any of the data on your server, 
you must exclude the NetID, First Name, Last Name, Email and Work for, columns.  
Only local (Ollama) models should ever have access to PII, and only local (Ollama) models 
should ever run `get_consult_details(id)`.


## Architecture

1. **Ingestion script** (`ingest.py`): reads the Excel file, normalizes each
   row into a consistent record:
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
   Output to a local SQLite database (or JSON — your call, propose one and
   explain tradeoffs briefly before proceeding).

2. **Embedding step**: embed `brief_description` + `notes_combined` (when
   present) using Ollama's embedding endpoint with `nomic-embed-text`. Store
   vectors alongside records — `sqlite-vec` extension is preferred so
   everything lives in one file, but propose alternatives if there's a good
   reason.

3. **Retrieval logic + MCP server**: implement the retrieval/aggregation
   logic as plain Python functions first (importable, independently
   testable), then expose them as MCP tools (Python, using the official
   `mcp` SDK):
   - `get_consult_detail(id)` — full record for one consult including
     all PII.
   - `search_past_consults(query, k=5)` — semantic search, returns matches
     with brief_description, topics, affiliation/role, notes_combined (if
     present), and an `is_incomplete` flag. No names/emails/NetIDs; no PII. 
     But provides an (internal) id that can be used with `get_consult_detail` 
     to retrieve all information.
   - `list_recent_consults(n=10)` — chronological browse, same level of output
     as `search_past_consults` (no PII).
   - `summarize_similar_requests(query, k=10)` — runs search, then
     aggregates results by affiliation/role/topic to answer "who else has
     asked about this kind of thing" without naming individuals. Same level
     of output as `search_past_consults` (no PII).

3a. **CLI comparison harness**: expose the same four functions as small,
    independent CLI scripts (e.g. `search-consults.py --query "..." --k 5`),
    each with clear `--help` text, plus a single README.md documenting all
    of them (à la the "skip MCP, use Bash + a README" approach). This isn't
    a fallback — it's the other arm of the comparison described in the
    Project Goal above. Keep the CLI scripts thin wrappers around the same
    underlying functions used by the MCP server, so behavior stays
    identical between the two interfaces and only the calling convention
    differs.

4. **Harness**: create a workspace-scoped Continue config at
   `.continue/agents/consult-assistant.yaml` in this project (not the global
   `~/.continue/config.yaml` — keep this project's model/tool setup separate
   from my generic local config). Register the MCP server there, pointed at
   a local Ollama model (I have `qwen3.5:9b`, `gemma4:e2b`, `llama3.1:8b`,
   `granite4.1:8b` available — default to `qwen3.5:9b` unless there's a
   reason to prefer another). 

5. **Use uv**: Use `uv` to install the necessary libraries (and create the usual
   `pypoject.toml` and other files).

6. **README.md** : update the `README.md` file with a short description of the project.

## Build Order

1. Confirm actual checkbox/data values by inspecting a sample of real rows
   before writing normalization logic.  If you send anything to your server, 
   exclude PII.
2. Ingestion script + normalized store.
3. Embedding step.
4. Core retrieval functions (plain Python), then the MCP server wrapping
   them.
5. CLI wrapper scripts + README around the same core functions.
6. Wire the MCP version into `.continue/agents/consult-assistant.yaml`. 
7. Provide me with a handful or real queries I could try for sanity checks
   using Continue and also the CLI/Bash version (no MCP).  
   Do not run these.  I will do that manually.
8. Stop and review with me before adding anything beyond this.

## Extension to test the Pi harness

I want to set up Pi (https://pi.dev) as a second harness for testing the CLI/Bash 
arm of the tool-calling comparison described in CLAUDE.md (step 5). Please:

1. Install Pi: `curl -fsSL https://pi.dev/install.sh | sh`, then verify it's on PATH.
2. Write an `AGENTS.md` at the project root. Pi loads this automatically from the 
   current directory at startup, so it should document the CLI scripts we already built in step 3a, 
   one section per script, each with usage syntax and a short description, in the same style as the 
   README we already wrote for those scripts. Reuse that README's content rather than rewriting it 
   from scratch — I want the two to stay in sync.
3. Configure Pi to use Ollama as the provider, defaulting to `qwen3.5:9b`, matching what's already 
   set up in `.continue/agents/consult-assistant.yaml`. Point it at my local Ollama instance. Add 
   whatever config file Pi needs for this (check its docs for the provider/model config format — 
   I believe it's `models.json` or similar) rather than guessing at the syntax.
4. Give me 5-6 test queries in plain language (not the CLI syntax) that mirror the requests you already provided.
   (These are currently in the `README.md` file in the project root). Don't run these queries yourself. I will run 
   them interactively in Pi's TUI and report back what happened, the same way I tested the Continue/MCP side.


## Working Conventions

- Ask before assuming file paths, exact column values, or schema choices
  where the data hasn't actually been inspected yet — don't guess when you
  could check.
- Prefer standard library / minimal dependencies where reasonable (uv for
  environment management, consistent with other local projects).
- Keep the ingestion and embedding steps as separate, independently
  runnable scripts (not bundled into the MCP server) so they can be
  re-run/debugged in isolation.
- Flag any row-level data quality issues encountered during ingestion
  (missing Brief Description, ambiguous checkbox values, encoding issues)
  rather than silently dropping or guessing.