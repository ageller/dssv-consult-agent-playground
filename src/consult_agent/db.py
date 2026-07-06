"""SQLite connection helpers, sqlite-vec loading, and schema.

Everything lives in one SQLite file (config.DB_PATH): the normalized records
in ``consults`` and the embedding vectors in the ``consult_vec`` virtual table
(sqlite-vec). The two are linked by a shared integer rowid.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import sqlite_vec

from . import config

# The normalized record. PII columns (netid/first/last/email/work_for) are
# stored so get_consult_detail can return them, but never embedded and never
# surfaced by any other tool.
SCHEMA = f"""
CREATE TABLE IF NOT EXISTS consults (
    rowid                 INTEGER PRIMARY KEY,   -- internal; links to consult_vec
    id                    TEXT UNIQUE NOT NULL,  -- public internal id, e.g. ss_2257
    date                  TEXT,                  -- ISO 8601 (from Created)
    status                TEXT,
    affiliation           TEXT,
    role                  TEXT,
    brief_description     TEXT,
    notes_combined        TEXT,                  -- Status Notes + Notes + Outcome
    topics                TEXT,                  -- JSON array of topic labels
    assigned_to           TEXT,                  -- internal staff (not client PII)
    initial_response_by   TEXT,                  -- internal staff (not client PII)
    initial_response_date TEXT,
    is_incomplete         INTEGER NOT NULL,      -- 1 if all notes fields empty
    embed_text            TEXT,                  -- exact text handed to the embedder
    -- PII: returned ONLY by get_consult_detail --------------------------------
    netid                 TEXT,
    first_name            TEXT,
    last_name             TEXT,
    email                 TEXT,
    work_for              TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS consult_vec USING vec0(
    embedding float[{config.EMBED_DIM}] distance_metric=cosine
);
"""


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open the SQLite database with the sqlite-vec extension loaded."""
    path = Path(db_path) if db_path is not None else config.DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't already exist."""
    conn.executescript(SCHEMA)
    conn.commit()
