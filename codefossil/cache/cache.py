"""Local persistent cache for CodeFossil analysis results."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any


def compute_project_hash(path: Path) -> str:
    """Compute a stable hash from package.json contents."""
    package_json = path / "package.json"
    content = package_json.read_bytes()
    return hashlib.sha256(content).hexdigest()


def load_cache(path: Path) -> dict[str, Any]:
    """Load cache data from disk, returning a safe default on failure."""
    if not path.exists():
        return {"project_hash": "", "dependencies": {}}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"project_hash": "", "dependencies": {}}

    if not isinstance(payload, dict):
        return {"project_hash": "", "dependencies": {}}

    dependencies = payload.get("dependencies", {})
    if not isinstance(dependencies, dict):
        dependencies = {}

    project_hash = payload.get("project_hash", "")
    if not isinstance(project_hash, str):
        project_hash = ""

    return {
        "project_hash": project_hash,
        "dependencies": dependencies,
    }


def save_cache(path: Path, data: dict[str, Any]) -> None:
    """Persist cache data to disk."""
    serializable = {
        "project_hash": str(data.get("project_hash", "")),
        "dependencies": data.get("dependencies", {}),
    }
    path.write_text(json.dumps(serializable, indent=2, sort_keys=True), encoding="utf-8")


def get_cached_dependency(cache: dict[str, Any], name: str, version: str) -> dict[str, Any] | None:
    """Retrieve cached dependency result by package name and version."""
    key = f"{name}@{version}"
    dependencies = cache.get("dependencies", {})
    if not isinstance(dependencies, dict):
        return None

    value = dependencies.get(key)
    return value if isinstance(value, dict) else None


def update_cache(cache: dict[str, Any], dependency: dict[str, Any]) -> None:
    """Update in-memory cache with a dependency analysis result."""
    dependencies = cache.setdefault("dependencies", {})
    if not isinstance(dependencies, dict):
        cache["dependencies"] = {}
        dependencies = cache["dependencies"]

    key = f"{dependency['name']}@{dependency['version']}"
    dependencies[key] = {
        "risk_score": int(dependency.get("risk_score", 0)),
        "last_update_years": float(dependency.get("last_update_years", 0.0)),
        "risk_label": str(dependency.get("risk_label", "")),
        "ai_advice": dependency.get("ai_advice"),
        "last_analyzed": datetime.now(tz=UTC).isoformat(),
    }
