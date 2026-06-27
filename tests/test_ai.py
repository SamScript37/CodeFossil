"""AI integration and secret-handling tests."""

from __future__ import annotations

from pathlib import Path

from codefossil.ai.service import AIProviderError, generate_advice_for_dependencies
from codefossil.core import pipeline


def test_generate_advice_skips_dependencies_with_cached_advice(monkeypatch) -> None:
    """Existing advice should be reused without calling the provider again."""

    class ExplodingProvider:
        def generate_migration_advice(self, dependency: dict[str, object]) -> str:
            raise AssertionError("provider should not be called")

    monkeypatch.setattr(
        "codefossil.ai.service.get_provider",
        lambda *_args: ExplodingProvider(),
    )

    deps = [
        {
            "name": "legacy-lib",
            "version": "1.0.0",
            "risk_score": 90,
            "ai_advice": "Already cached.",
        }
    ]

    assert (
        generate_advice_for_dependencies(deps, "openai", "secret-key", top_n=1) == deps
    )


def test_analyze_project_advanced_survives_ai_provider_error_without_persisting_api_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """AI failures should not break scans or write user secrets to cache."""
    (tmp_path / "package.json").write_text(
        '{"dependencies": {"legacy-lib": "1.0.0"}}',
        encoding="utf-8",
    )

    def fake_analyze_dependency_versions(
        _dependency_versions: dict[str, str],
    ) -> list[dict[str, object]]:
        return [
            {
                "name": "legacy-lib",
                "version": "1.0.0",
                "last_update_years": 3.4,
                "risk_score": 70,
            }
        ]

    def raise_ai_provider_error(*_args, **_kwargs):
        raise AIProviderError("provider unavailable")

    monkeypatch.setattr(
        pipeline,
        "analyze_dependency_versions",
        fake_analyze_dependency_versions,
    )
    monkeypatch.setattr(
        pipeline,
        "generate_advice_for_dependencies",
        raise_ai_provider_error,
    )

    results = pipeline.analyze_project_advanced(
        tmp_path,
        ai_provider_name="openai",
        api_key="super-secret-api-key",
        ai_top=1,
    )

    assert results == [
        {
            "name": "legacy-lib",
            "version": "1.0.0",
            "last_update_years": 3.4,
            "risk_score": 70,
            "risk_label": "HIGH",
        }
    ]

    cache_text = (tmp_path / ".codefossil_cache.json").read_text(encoding="utf-8")
    assert "super-secret-api-key" not in cache_text
    assert "api_key" not in cache_text
