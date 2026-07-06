"""Embedding step: embed each record's PII-free text and store vectors.

Runs after ingest.py, independently:

    uv run consult-embed
    uv run python -m consult_agent.embed --db consult.db

Uses the local Ollama embedding model (config.EMBED_MODEL). Only ``embed_text``
(brief_description + notes_combined, already PII-free) is sent to Ollama —
never names, emails, NetIDs, or the PI ("Work for") field.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

from . import config, db, ollama


def _pack(vec: list[float]) -> bytes:
    """Pack a float vector into the little-endian float32 blob sqlite-vec wants."""
    return struct.pack(f"{len(vec)}f", *vec)


def embed_all(db_path: Path, *, model: str | None = None) -> None:
    conn = db.connect(db_path)
    db.init_schema(conn)

    rows = conn.execute(
        "SELECT rowid, id, embed_text FROM consults ORDER BY rowid"
    ).fetchall()
    print(f"Embedding {len(rows)} records with {model or config.EMBED_MODEL}...", file=sys.stderr)

    conn.execute("DELETE FROM consult_vec")

    embedded = 0
    empty = 0
    for n, row in enumerate(rows, start=1):
        text = row["embed_text"]
        if not text or not text.strip():
            # No brief description and no notes — nothing to embed. Left out of
            # the vector index (won't surface in semantic search) but still in
            # the record store for get_consult_detail / list_recent_consults.
            empty += 1
            continue
        vec = ollama.embed(text, model=model)
        if len(vec) != config.EMBED_DIM:
            raise ValueError(
                f"id={row['id']}: embedding dim {len(vec)} != expected {config.EMBED_DIM}"
            )
        conn.execute(
            "INSERT INTO consult_vec(rowid, embedding) VALUES (?, ?)",
            (row["rowid"], _pack(vec)),
        )
        embedded += 1
        if n % 200 == 0:
            print(f"  ...{n}/{len(rows)}", file=sys.stderr)
            conn.commit()

    conn.commit()
    conn.close()
    print(
        f"\nEmbedding complete: {embedded} vectors stored, "
        f"{empty} records skipped (no embeddable text). DB: {db_path}",
        file=sys.stderr,
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Embed consult records into sqlite-vec.")
    p.add_argument("--db", type=Path, default=config.DB_PATH, help="SQLite file")
    p.add_argument("--model", default=None, help=f"embedding model (default {config.EMBED_MODEL})")
    args = p.parse_args()
    embed_all(args.db, model=args.model)


if __name__ == "__main__":
    main()
