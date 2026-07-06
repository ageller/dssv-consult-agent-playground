"""Pure Excel-row -> normalized-record logic.

Kept separate from ingest.py (which does the I/O) so it can be unit-tested and
reasoned about in isolation. Nothing here touches the database or the network.
"""

from __future__ import annotations

import datetime as _dt
import unicodedata
from dataclasses import dataclass, field

from . import config


@dataclass
class Record:
    """A normalized consult record.

    ``embed_text`` is the exact, PII-free text that will be embedded. PII
    fields are carried through for get_consult_detail but must never be
    embedded or surfaced elsewhere.
    """

    id: str
    date: str | None
    status: str | None
    affiliation: str | None
    role: str | None
    brief_description: str | None
    notes_combined: str | None
    topics: list[str]
    assigned_to: str | None
    initial_response_by: str | None
    initial_response_date: str | None
    is_incomplete: bool
    embed_text: str
    # PII — detail-only
    netid: str | None
    first_name: str | None
    last_name: str | None
    email: str | None
    work_for: str | None


def clean(value: object) -> str | None:
    """Normalize a free-text/categorical cell.

    Handles the whitespace/encoding artifacts flagged in CLAUDE.md: NFC
    Unicode normalization, non-breaking spaces (U+00A0), zero-width/BOM
    (U+FEFF), and collapsing of internal whitespace. Returns None for
    empty/blank cells.
    """
    if value is None:
        return None
    s = str(value)
    s = unicodedata.normalize("NFC", s)
    s = s.replace(" ", " ").replace("﻿", "")
    s = " ".join(s.split())  # collapse internal/edge whitespace
    return s or None


def _to_iso(value: object) -> str | None:
    """Render a date/datetime cell as ISO 8601; pass through cleaned strings."""
    if value is None:
        return None
    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.isoformat()
    return clean(value)


def _is_checked(value: object) -> bool:
    """A topic checkbox is 'on' iff the cell is truthy TRUE/True/"TRUE"."""
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().upper() == "TRUE"
    return False


@dataclass
class NormalizeResult:
    record: Record
    issues: list[str] = field(default_factory=list)


def normalize_row(row: dict[str, object]) -> NormalizeResult:
    """Turn a header->value dict for one spreadsheet row into a Record.

    Returns the record plus a list of human-readable data-quality issues
    (missing brief description, unexpected checkbox values, etc.) so ingest.py
    can report rather than silently drop or guess.
    """
    issues: list[str] = []

    rid = clean(row.get("Smartsheet Row ID"))
    if not rid:
        issues.append("missing Smartsheet Row ID")

    # Topics from checkbox columns; flag anything that isn't TRUE/blank.
    topics: list[str] = []
    for col in config.TOPIC_COLUMNS:
        raw = row.get(col)
        if _is_checked(raw):
            topics.append(col)
        elif raw is not None and not (isinstance(raw, str) and raw.strip() == ""):
            issues.append(f"unexpected value in checkbox column {col!r}: {raw!r}")

    brief = clean(row.get("Brief Description"))
    if not brief:
        issues.append("missing Brief Description")

    # notes_combined: join the consultant fields, empty-tolerant, labelled.
    notes_parts: list[str] = []
    for fld in config.NOTES_FIELDS:
        val = clean(row.get(fld))
        if val:
            notes_parts.append(f"[{fld}] {val}")
    notes_combined = "\n---\n".join(notes_parts) if notes_parts else None
    is_incomplete = notes_combined is None

    # embed_text: PII-free. brief_description + notes_combined when present.
    embed_bits = [b for b in (brief, notes_combined) if b]
    embed_text = "\n\n".join(embed_bits)

    record = Record(
        id=rid or "",
        date=_to_iso(row.get("Created")),
        status=clean(row.get("Status")),
        affiliation=clean(row.get("Affiliation")),
        role=clean(row.get("Role")),
        brief_description=brief,
        notes_combined=notes_combined,
        topics=topics,
        assigned_to=clean(row.get("Assigned to")),
        initial_response_by=clean(row.get("Initial Response by")),
        initial_response_date=_to_iso(row.get("Initial Response Date")),
        is_incomplete=is_incomplete,
        embed_text=embed_text,
        netid=clean(row.get("NetID")),
        first_name=clean(row.get("First Name")),
        last_name=clean(row.get("Last Name")),
        email=clean(row.get("Email")),
        work_for=clean(row.get("Work for")),
    )
    return NormalizeResult(record=record, issues=issues)
