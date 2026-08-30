"""Thread-safe process-local ESI representation cache."""

from __future__ import annotations

from threading import RLock

from eve_dolphin.esi.models import EsiCacheEntry


class EsiMemoryCache:
    """Keep response representations while the desktop client is running."""

    def __init__(self) -> None:
        self._entries: dict[str, EsiCacheEntry] = {}
        self._lock = RLock()

    def get(self, key: str) -> EsiCacheEntry | None:
        with self._lock:
            return self._entries.get(key)

    def put(self, key: str, entry: EsiCacheEntry) -> None:
        with self._lock:
            self._entries[key] = entry

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
