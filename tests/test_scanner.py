"""Scanner and package.json validation tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from codefossil.scanner.npm import (
    NPM_REGISTRY_URL,
    PackageJsonError,
    collect_dependencies,
    fetch_years_since_latest_release,
    load_package_json,
    score_risk,
)


class DummyResponse:
    """Minimal response double for npm registry calls."""

    def __init__(self, payload: dict[str, Any], error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error

    def raise_for_status(self) -> None:
        if self.error is not None:
            raise self.error

    def json(self) -> dict[str, Any]:
        return self.payload


class DummyClient:
    """Minimal client double that records requested URLs."""

    def __init__(self, response: DummyResponse) -> None:
        self.response = response
        self.requested_url: str | None = None

    def get(self, url: str) -> DummyResponse:
        self.requested_url = url
        return self.response


def test_score_risk_boundaries() -> None:
    """Risk scores should follow the documented age buckets."""
    assert score_risk(5.0) == 90
    assert score_risk(3.0) == 70
    assert score_risk(2.0) == 50
    assert score_risk(1.0) == 30
    assert score_risk(0.99) == 10


def test_load_package_json_requires_file(tmp_path) -> None:
    """Missing package.json should fail clearly."""
    with pytest.raises(FileNotFoundError):
        load_package_json(tmp_path / "package.json")


def test_load_package_json_rejects_invalid_json(tmp_path) -> None:
    """Invalid JSON should be surfaced as a PackageJsonError."""
    package_json = tmp_path / "package.json"
    package_json.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(PackageJsonError, match="Invalid package.json JSON"):
        load_package_json(package_json)


def test_load_package_json_rejects_non_object_root(tmp_path) -> None:
    """package.json must be a JSON object."""
    package_json = tmp_path / "package.json"
    package_json.write_text('["react"]', encoding="utf-8")

    with pytest.raises(PackageJsonError, match="root must be an object"):
        load_package_json(package_json)


def test_load_package_json_rejects_malformed_dependencies(tmp_path) -> None:
    """dependencies and devDependencies must be objects when present."""
    package_json = tmp_path / "package.json"
    package_json.write_text('{"dependencies": ["react"]}', encoding="utf-8")

    with pytest.raises(PackageJsonError, match="dependencies must be an object"):
        load_package_json(package_json)


def test_load_package_json_requires_dependency_sections(tmp_path) -> None:
    """A manifest without dependency sections is not useful to scan."""
    package_json = tmp_path / "package.json"
    package_json.write_text('{"name": "demo"}', encoding="utf-8")

    with pytest.raises(PackageJsonError, match="must include dependencies or devDependencies"):
        load_package_json(package_json)


def test_collect_dependencies_respects_include_dev_flag() -> None:
    """devDependencies should only be included when requested."""
    payload = {
        "dependencies": {"react": "^18.0.0"},
        "devDependencies": {"vitest": "^1.0.0"},
    }

    assert collect_dependencies(payload, include_dev=False) == {"react": "^18.0.0"}
    assert collect_dependencies(payload, include_dev=True) == {
        "react": "^18.0.0",
        "vitest": "^1.0.0",
    }


def test_fetch_years_since_latest_release_uses_latest_tag_timestamp() -> None:
    """Registry metadata should be read without making a real network call."""
    now = datetime(2026, 1, 1, tzinfo=UTC)
    response = DummyResponse(
        {
            "dist-tags": {"latest": "2.0.0"},
            "time": {"2.0.0": "2025-01-01T00:00:00.000Z"},
        }
    )
    client = DummyClient(response)

    years = fetch_years_since_latest_release(client, "left-pad", now)  # type: ignore[arg-type]

    assert client.requested_url == f"{NPM_REGISTRY_URL}/left-pad"
    assert years == pytest.approx(0.999, rel=0.01)


def test_fetch_years_since_latest_release_returns_high_risk_age_on_http_error() -> None:
    """Registry failures should degrade safely instead of crashing scans."""
    now = datetime(2026, 1, 1, tzinfo=UTC)
    client = DummyClient(DummyResponse({}, httpx.HTTPError("registry down")))

    assert fetch_years_since_latest_release(client, "missing-package", now) == 99.0  # type: ignore[arg-type]
