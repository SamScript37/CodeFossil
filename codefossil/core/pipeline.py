"""Analysis pipeline for CodeFossil."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from codefossil.ai.service import AIProviderError, generate_advice_for_dependencies
from codefossil.cache.cache import (
    compute_project_hash,
    get_cached_dependency,
    load_cache,
    save_cache,
    update_cache,
)
from codefossil.scanner.npm import (
    analyze_dependency_versions,
    collect_dependencies,
    load_package_json,
    scan_npm_dependencies,
)


def risk_label(score: int) -> str:
    """Convert a numeric risk score to a human-readable label."""
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def analyze_project(path: Path, include_dev: bool = False) -> list[dict[str, Any]]:
    """Analyze a project and return risk-sorted dependency results."""
    results = scan_npm_dependencies(path, include_dev=include_dev)
    return _finalize_results(results)


def analyze_project_advanced(
    path: Path,
    include_dev: bool = False,
    incremental: bool = False,
    ai_provider_name: str | None = None,
    api_key: str | None = None,
    ai_top: int = 3,
) -> list[dict[str, Any]]:
    """Analyze project using optional incremental caching and AI enrichment."""
    payload = load_package_json(path / "package.json")
    dependency_versions = collect_dependencies(payload, include_dev=include_dev)

    cache_path = path / ".codefossil_cache.json"
    cache = load_cache(cache_path)
    current_hash = compute_project_hash(path)

    base_results = _collect_results_with_cache(
        dependency_versions=dependency_versions,
        cache=cache,
        incremental=incremental,
    )
    finalized = _finalize_results(base_results)

    if ai_provider_name and api_key:
        finalized = _apply_ai_advice(
            finalized,
            cache=cache,
            provider_name=ai_provider_name,
            api_key=api_key,
            top_n=ai_top,
        )

    cache["project_hash"] = current_hash
    _rewrite_cache_dependencies(cache, finalized)
    save_cache(cache_path, cache)

    return sorted(finalized, key=lambda row: int(row["risk_score"]), reverse=True)


def _collect_results_with_cache(
    dependency_versions: dict[str, str],
    cache: dict[str, Any],
    incremental: bool,
) -> list[dict[str, Any]]:
    """Return results reusing cache when incremental mode is enabled."""
    if not dependency_versions:
        return []

    if not incremental:
        return analyze_dependency_versions(dependency_versions)

    reused: list[dict[str, Any]] = []
    pending: dict[str, str] = {}

    for name, version in dependency_versions.items():
        cached = get_cached_dependency(cache, name, version)
        if cached is None:
            pending[name] = version
            continue

        reused.append(
            {
                "name": name,
                "version": version,
                "last_update_years": float(cached.get("last_update_years", 99.0)),
                "risk_score": int(cached.get("risk_score", 90)),
                "ai_advice": cached.get("ai_advice"),
            }
        )

    analyzed = analyze_dependency_versions(pending) if pending else []
    return reused + analyzed


def _apply_ai_advice(
    results: list[dict[str, Any]],
    cache: dict[str, Any],
    provider_name: str,
    api_key: str,
    top_n: int,
) -> list[dict[str, Any]]:
    """Attach AI advice to the top risky dependencies when needed."""
    ranked = sorted(results, key=lambda row: int(row["risk_score"]), reverse=True)
    candidates = ranked[: max(top_n, 0)]

    for dep in candidates:
        cached = get_cached_dependency(cache, str(dep["name"]), str(dep["version"]))
        if cached and cached.get("ai_advice"):
            dep["ai_advice"] = cached["ai_advice"]

    try:
        return generate_advice_for_dependencies(results, provider_name, api_key, top_n)
    except AIProviderError:
        return results


def _finalize_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sorted_results = sorted(
        results, key=lambda row: int(row["risk_score"]), reverse=True
    )
    for row in sorted_results:
        row["risk_label"] = risk_label(int(row["risk_score"]))
    return sorted_results


def _rewrite_cache_dependencies(
    cache: dict[str, Any], results: list[dict[str, Any]]
) -> None:
    """Replace dependency cache with latest run results for current dependency set."""
    cache["dependencies"] = {}
    for dependency in results:
        update_cache(cache, dependency)
