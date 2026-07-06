"""Central configuration: paths, model names, and shared constants.

Everything that might reasonably change lives here so the rest of the code
doesn't hard-code paths or model names. Values can be overridden with
environment variables where that's useful for experimentation.
"""

from __future__ import annotations

import os
from pathlib import Path

# --- Paths -----------------------------------------------------------------
# Project root = two levels up from this file (src/consult_agent/config.py).
PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONSULT_DATA_DIR = PROJECT_ROOT / "consult_data"
# The source spreadsheet. Overridable in case the file gets renamed.
SOURCE_XLSX = Path(
    os.environ.get(
        "CONSULT_XLSX",
        CONSULT_DATA_DIR / "Research Data Services Consult Requests.xlsx",
    )
)

# Single SQLite file holding both normalized records and vectors. Lives in
# consult_data/ alongside the source spreadsheet — that whole directory is
# gitignored, so the DB (which contains PII) never reaches version control.
DB_PATH = Path(os.environ.get("CONSULT_DB", CONSULT_DATA_DIR / "consult.db"))

# --- Ollama ----------------------------------------------------------------
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = os.environ.get("CONSULT_EMBED_MODEL", "nomic-embed-text")
# nomic-embed-text produces 768-dim vectors (verified against the local model).
EMBED_DIM = int(os.environ.get("CONSULT_EMBED_DIM", "768"))
# Chat model used by the Continue harness (documented here for reference).
CHAT_MODEL = os.environ.get("CONSULT_CHAT_MODEL", "qwen3.5:9b")

# --- Data semantics --------------------------------------------------------
# Checkbox columns in the spreadsheet -> the topic label we store. Values are
# TRUE (openpyxl -> Python True) or blank (None); verified by inspection.
TOPIC_COLUMNS = [
    "Python",
    "R",
    "SQL/Databases",
    "Statistics",
    "Stata",
    "SPSS",
    "Data Visualization",
    "Geographic Data",
    "Data Management",
    "Qualitative Analysis",
    "Something Else/I'm Not Sure",
]

# Fields that combine into notes_combined, in this order.
NOTES_FIELDS = ["Status Notes", "Notes", "Outcome"]

# PII columns that must NEVER be embedded or sent to a remote model, and must
# never appear in tool output other than get_consult_detail.
#   - NetID / First Name / Last Name / Email : the client's identity.
#   - Work for : the client's PI/faculty name (a real person's name).
PII_COLUMNS = ["NetID", "First Name", "Last Name", "Email", "Work for"]
