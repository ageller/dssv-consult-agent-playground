"""Core retrieval + aggregation logic — plain, importable Python.

This is the single source of truth for what the assistant can do. Both the MCP
server (mcp_server.py) and the CLI scripts (../../cli/*.py) are thin wrappers
around these functions, so the two interfaces behave identically and only the
calling convention differs (the CLI-vs-MCP comparison in CLAUDE.md).

PII discipline (see CLAUDE.md "Privacy Note"):
  * Only get_consult_detail() returns PII (names, email, NetID, and the
    "Work for" PI name), and only when a specific id is explicitly requested.
  * Every other function returns PII-free records: internal ids, dates,
    status, affiliation, role, topics, brief_description, notes_combined,
    is_incomplete. No names, emails, NetIDs, or PI names — including in the
    ids, which are internal only.
"""

from __future__ import annotations

import json
import sqlite3
import struct
from contextlib import contextmanager

from . import config, db, ollama

# Columns safe to surface from any tool. Deliberately excludes netid,
# first_name, last_name, email, work_for.
_PUBLIC_COLUMNS = [
    "id",
    "date",
    "status",
    "affiliation",
    "role",
    "topics",
    "brief_description",
    "notes_combined",
    "is_incomplete",
]


@contextmanager
def _conn(conn: sqlite3.Connection | None):
    """Use a caller-supplied connection, or open (and close) our own."""
    if conn is not None:
        yield conn
    else:
        c = db.connect()
        try:
            yield c
        finally:
            c.close()


def _public_record(row: sqlite3.Row) -> dict:
    """Project a consults row down to its PII-free public shape."""
    rec = {col: row[col] for col in _PUBLIC_COLUMNS}
    rec["topics"] = json.loads(rec["topics"]) if rec["topics"] else []
    rec["is_incomplete"] = bool(rec["is_incomplete"])
    # notes_combined absent -> None, so callers can distinguish "no notes".
    return rec


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


# --- Tool 1: full detail for one consult (PII included) --------------------
def get_consult_detail(consult_id: str, *, conn: sqlite3.Connection | None = None) -> dict | None:
    """Return the FULL record for one consult, including PII.

    This is the one deliberate PII exception: called only with an explicit id
    (which the user got from a PII-free search/list result). Returns None if
    no such id exists.
    """
    with _conn(conn) as c:
        row = c.execute("SELECT * FROM consults WHERE id = ?", (consult_id,)).fetchone()
    if row is None:
        return None
    rec = _public_record(row)
    rec.update(
        {
            "assigned_to": row["assigned_to"],
            "initial_response_by": row["initial_response_by"],
            "initial_response_date": row["initial_response_date"],
            # PII fields — only here.
            "netid": row["netid"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "email": row["email"],
            "work_for": row["work_for"],
        }
    )
    return rec


# --- Tool 2: semantic search (PII-free) ------------------------------------
def search_past_consults(
    query: str, k: int = 5, *, conn: sqlite3.Connection | None = None
) -> list[dict]:
    """Semantically search past consults for ones similar to ``query``.

    Embeds the query with the local Ollama model, runs a cosine KNN over the
    vector index, and returns the k closest PII-free records with a
    ``similarity`` score in [0, 1] (higher = closer).
    """
    if k <= 0:
        return []
    qvec = ollama.embed(query)
    with _conn(conn) as c:
        hits = c.execute(
            """
            SELECT rowid, distance
            FROM consult_vec
            WHERE embedding MATCH ? AND k = ? ORDER BY distance
            """,
            (_pack(qvec), k),
        ).fetchall()
        results = []
        for hit in hits:
            row = c.execute(
                "SELECT * FROM consults WHERE rowid = ?", (hit["rowid"],)
            ).fetchone()
            if row is None:
                continue
            rec = _public_record(row)
            # cosine distance in [0, 2] -> similarity in [0, 1].
            rec["similarity"] = round(1.0 - hit["distance"] / 2.0, 4)
            results.append(rec)
    return results


# --- Tool 3: recent consults (PII-free) ------------------------------------
def list_recent_consults(n: int = 10, *, conn: sqlite3.Connection | None = None) -> list[dict]:
    """Return the ``n`` most recent consults (by date), PII-free."""
    if n <= 0:
        return []
    with _conn(conn) as c:
        rows = c.execute(
            "SELECT * FROM consults ORDER BY date DESC LIMIT ?", (n,)
        ).fetchall()
    return [_public_record(r) for r in rows]


# --- Tool 4: aggregate summary of similar requests (PII-free) --------------
def summarize_similar_requests(
    query: str, k: int = 10, *, conn: sqlite3.Connection | None = None
) -> dict:
    """Search, then aggregate the matches by affiliation / role / topic.

    Answers "who else has asked about this kind of thing" WITHOUT naming
    individuals — returns counts only, plus the internal ids of the matches
    so a specific one can be drilled into with get_consult_detail.
    """
    matches = search_past_consults(query, k=k, conn=conn)

    by_affiliation: dict[str, int] = {}
    by_role: dict[str, int] = {}
    by_topic: dict[str, int] = {}
    by_status: dict[str, int] = {}
    incomplete = 0

    for m in matches:
        if m["affiliation"]:
            by_affiliation[m["affiliation"]] = by_affiliation.get(m["affiliation"], 0) + 1
        if m["role"]:
            by_role[m["role"]] = by_role.get(m["role"], 0) + 1
        if m["status"]:
            by_status[m["status"]] = by_status.get(m["status"], 0) + 1
        for t in m["topics"]:
            by_topic[t] = by_topic.get(t, 0) + 1
        if m["is_incomplete"]:
            incomplete += 1

    def _sorted(d: dict[str, int]) -> dict[str, int]:
        return dict(sorted(d.items(), key=lambda kv: (-kv[1], kv[0])))

    return {
        "query": query,
        "num_matches": len(matches),
        "num_incomplete": incomplete,
        "by_affiliation": _sorted(by_affiliation),
        "by_role": _sorted(by_role),
        "by_topic": _sorted(by_topic),
        "by_status": _sorted(by_status),
        "match_ids": [m["id"] for m in matches],
    }
