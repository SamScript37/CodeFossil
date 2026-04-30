"""Simple JSON cache with TTL support."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from typing import Any


class CacheStore:
    """A simple JSON-backed cache keyed by dependency name."""

    TTL_HOURS = 24

    def __init__(self, cache_file: Path) -> None:
        self.cache_file = cache_file
        self._payload: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.cache_file.exists():
            return {"entries": {}}

        try:
            with self.cache_file.open("r", encoding="utf-8") as handle:
                content = json.load(handle)
                if isinstance(content, dict) and isinstance(content.get("entries"), dict):
                    return content
        except (json.JSONDecodeError, OSError):
            pass
        return {"entries": {}}

    def get(self, key: str) -> dict[str, Any] | None:
        entries = self._payload.setdefault("entries", {})
        item = entries.get(key)
        if not item:
            return None

        checked_at_raw = item.get("checked_at")
        if not checked_at_raw:
            return None

        try:
            checked_at = datetime.fromisoformat(checked_at_raw)
        except ValueError:
            return None

        if datetime.now(tz=UTC) - checked_at > timedelta(hours=self.TTL_HOURS):
            return None

        return item.get("data") if isinstance(item.get("data"), dict) else None

    def set(self, key: str, data: dict[str, Any]) -> None:
        entries = self._payload.setdefault("entries", {})
        entries[key] = {
            "checked_at": datetime.now(tz=UTC).isoformat(),
            "data": data,
        }

    def save(self) -> None:
        with self.cache_file.open("w", encoding="utf-8") as handle:
            json.dump(self._payload, handle, indent=2, sort_keys=True)
