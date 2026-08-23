"""Bounded, source-aware context assembly (B-S12.3, B-S12.4).

A comment lifted out of its thread reads differently from the same comment under
its parent, and a classifier that never sees the parent will mislabel
counterspeech as agreement. So the context that makes an item interpretable
travels with it — bounded, because an unbounded parent chain is both a cost and a
prompt-injection surface, and explicit, because "no parent" and "parent could not
be retrieved" must stay distinguishable.

Absent fields are omitted rather than stored as empty strings: a key that is not
present says "not collected", where `""` would say "collected and empty".
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from amanah.canonical.text import normalize_text, truncate_excerpt
from amanah.ingestion.contract import ContentContext

#: Per-field caps. Generous enough to carry a real headline or parent comment,
#: tight enough that one item cannot carry a document.
CONTEXT_FIELD_LIMITS: Mapping[str, int] = {
    "title": 400,
    "parent_text": 1_000,
    "root_text": 1_000,
    "caption": 1_000,
}


def assemble_context(context: ContentContext) -> dict[str, Any]:
    """Normalize and bound one item's interpretive context.

    Returns a plain mapping for the `normalized_context` JSONB column. It is
    model input, never a reader-facing field, and no projection has a column
    for it.
    """
    fields = {
        "title": context.title,
        "parent_text": context.parent_text,
        "root_text": context.root_text,
        "caption": context.caption,
    }
    assembled: dict[str, Any] = {}
    for name, value in fields.items():
        normalized = normalize_text(value)
        if not normalized:
            continue
        assembled[name] = truncate_excerpt(normalized, CONTEXT_FIELD_LIMITS[name])
    return assembled
