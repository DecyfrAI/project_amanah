"""Deterministic inference cache keys (B-S13.4).

`spec.md` section 11.2 says cache by content hash, model, prompt version, and
taxonomy version, and never regenerate an unchanged summary on page load. The key
built here is that requirement in one function, so no caller can construct a
narrower one and quietly serve output produced under different rules.

The store is in-process and bounded. That is the honest scope for a hackathon
deployment: it removes the repeat work inside one ETL run and one API process,
and it makes no claim to be shared across replicas. Durable caching of *insights*
is a different mechanism — `insight_snapshots` rows, keyed by the same versions —
because those are published artifacts that must survive a restart.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict

from pydantic import BaseModel

#: A NUL byte cannot appear in any of the joined values, so two different field
#: splits cannot collide into one digest.
_FIELD_SEPARATOR = "\x00"

#: Entries held before the oldest is evicted. Sized for one ETL batch rather than
#: for a long-lived shared cache, which this is not.
DEFAULT_CACHE_CAPACITY = 512


def inference_cache_key(
    *,
    content_hash: str,
    model_name: str,
    prompt_id: str,
    prompt_version: str,
    taxonomy_version: str,
    inference_version: str,
) -> str:
    """Identify one inference by everything that could change its output.

    Every version that shapes the answer is in the key. Omitting one would let a
    prompt or taxonomy change serve a cached result generated under the old
    rules — a silent correctness failure with no error to notice.
    """
    return hashlib.sha256(
        _FIELD_SEPARATOR.join(
            (
                content_hash,
                model_name,
                prompt_id,
                prompt_version,
                taxonomy_version,
                inference_version,
            )
        ).encode("utf-8")
    ).hexdigest()


class InferenceCache:
    """A bounded in-process cache of validated payloads, oldest evicted first.

    Values are `BaseModel` instances rather than raw JSON: only output that has
    already passed schema validation is worth keeping, and storing the parsed
    object means a hit cannot re-run a validation that could now fail.
    """

    def __init__(self, capacity: int = DEFAULT_CACHE_CAPACITY) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self._capacity = capacity
        self._entries: OrderedDict[str, BaseModel] = OrderedDict()

    def get(self, key: str) -> BaseModel | None:
        """Return a cached payload and mark it recently used."""
        if key not in self._entries:
            return None
        self._entries.move_to_end(key)
        return self._entries[key]

    def set(self, key: str, payload: BaseModel) -> None:
        self._entries[key] = payload
        self._entries.move_to_end(key)
        while len(self._entries) > self._capacity:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)
