"""NPM dependency scanner."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from codefossil.utils.cache import CacheStore

NPM_REGISTRY_URL = "https://registry.npmjs.org"


class PackageJsonError(ValueError):
    """Raised when package.json content is invalid."""


def score_risk(years_since_update: float) -> int:
    """Map years-since-update to a fixed risk score."""
    if years_since_update >= 5:
        return 90
    if years_since_update >= 3:
        return 70
    if years_since_update >= 2:
        return 50
    if years_since_update >= 1:
        return 30
    return 10


def load_package_json(path: Path) -> dict[str, Any]:
    """Safely load and validate package.json."""
    if not path.exists():
        raise FileNotFoundError(f"package.json not found: {path}")

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PackageJsonError(f"Unable to read package.json: {exc}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PackageJsonError(f"Invalid package.json JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise PackageJsonError("package.json root must be an object")

    for field in ("dependencies", "devDependencies"):
        if field in payload and not isinstance(payload[field], dict):
            raise PackageJsonError(f"{field} must be an object when present")

    if "dependencies" not in payload and "devDependencies" not in payload:
        raise PackageJsonError(
            "package.json must include dependencies or devDependencies"
        )

    return payload


def collect_dependencies(payload: dict[str, Any], include_dev: bool) -> dict[str, str]:
    """Return dependencies from package.json payload."""
    dependencies = dict(payload.get("dependencies", {}))
    if include_dev:
        dependencies.update(payload.get("devDependencies", {}))
    return {name: str(version) for name, version in dependencies.items()}


def scan_npm_dependencies(
    project_path: Path, include_dev: bool = False
) -> list[dict[str, Any]]:
    """Scan package.json dependencies and return structured staleness results."""
    payload = load_package_json(project_path / "package.json")
    dependencies = collect_dependencies(payload, include_dev=include_dev)

    cache = CacheStore(project_path / ".codefossil_cache.json")
    now = datetime.now(tz=UTC)
    results: list[dict[str, Any]] = []

    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        for name, version in sorted(dependencies.items()):
            cached = cache.get(name)
            if cached is not None:
                results.append(
                    {
                        "name": name,
                        "version": version,
                        "last_update_years": float(cached["last_update_years"]),
                        "risk_score": int(cached["risk_score"]),
                    }
                )
                continue

            years = fetch_years_since_latest_release(client, name, now)
            risk = score_risk(years)
            results.append(
                {
                    "name": name,
                    "version": version,
                    "last_update_years": years,
                    "risk_score": risk,
                }
            )
            cache.set(name, {"last_update_years": years, "risk_score": risk})

    cache.save()
    return results


def fetch_years_since_latest_release(
    client: httpx.Client, package: str, now: datetime
) -> float:
    """Fetch npm metadata and compute years since latest version timestamp."""
    url = f"{NPM_REGISTRY_URL}/{package}"
    try:
        response = client.get(url)
        response.raise_for_status()
    except httpx.HTTPError:
        return 99.0

    data = response.json()
    time_data = data.get("time") or {}

    latest_version = (data.get("dist-tags") or {}).get("latest")
    latest_timestamp = time_data.get(latest_version) if latest_version else None
    if not latest_timestamp:
        latest_timestamp = time_data.get("modified")

    if not latest_timestamp:
        return 99.0

    try:
        updated_at = datetime.fromisoformat(latest_timestamp.replace("Z", "+00:00"))
    except ValueError:
        return 99.0

    elapsed_days = max((now - updated_at).total_seconds(), 0.0) / 86_400
    return elapsed_days / 365.25


def analyze_dependency_versions(
    dependency_versions: dict[str, str],
) -> list[dict[str, Any]]:
    """Analyze a provided dependency map without reading project files."""
    now = datetime.now(tz=UTC)
    results: list[dict[str, Any]] = []
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        for name, version in sorted(dependency_versions.items()):
            years = fetch_years_since_latest_release(client, name, now)
            results.append(
                {
                    "name": name,
                    "version": version,
                    "last_update_years": years,
                    "risk_score": score_risk(years),
                }
            )
    return results
