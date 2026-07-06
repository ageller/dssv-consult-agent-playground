"""Thin client for the local Ollama HTTP API.

Only what we need: a single embedding call. Kept tiny and dependency-light so
it's obvious exactly what leaves the process (nothing but localhost traffic).
"""

from __future__ import annotations

import httpx

from . import config


def embed(text: str, *, model: str | None = None, timeout: float = 60.0) -> list[float]:
    """Return the embedding vector for ``text`` from the local Ollama model.

    Raises httpx.HTTPError on transport/HTTP failure and ValueError if the
    response doesn't contain an embedding, so callers fail loudly rather than
    silently storing empty vectors.
    """
    model = model or config.EMBED_MODEL
    resp = httpx.post(
        f"{config.OLLAMA_HOST}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    vec = data.get("embedding")
    if not vec:
        raise ValueError(f"Ollama returned no embedding for model {model!r}: {data!r}")
    return vec
