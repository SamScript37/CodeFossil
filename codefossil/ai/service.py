"""AI integration service for dependency migration advice."""

from __future__ import annotations

import sys
from typing import Any



class AIProviderError(RuntimeError):
    """Raised when an AI provider request fails."""


class BaseProvider:
    """Base provider interface."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def generate_migration_advice(self, dependency: dict[str, Any]) -> str:
        raise NotImplementedError


class OpenAIProvider(BaseProvider):
    def generate_migration_advice(self, dependency: dict[str, Any]) -> str:
        prompt = _build_prompt(dependency)
        headers = {"Authorization": f"Bearer {self.api_key}"}
        body = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You generate concise migration advice for software dependencies."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        import httpx

        with httpx.Client(timeout=20.0) as client:
            resp = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
        return str(data["choices"][0]["message"]["content"]).strip()


class AnthropicProvider(BaseProvider):
    def generate_migration_advice(self, dependency: dict[str, Any]) -> str:
        prompt = _build_prompt(dependency)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        body = {
            "model": "claude-3-5-haiku-latest",
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt}],
        }
        import httpx

        with httpx.Client(timeout=20.0) as client:
            resp = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
        return str(data["content"][0]["text"]).strip()


class GroqProvider(BaseProvider):
    def generate_migration_advice(self, dependency: dict[str, Any]) -> str:
        prompt = _build_prompt(dependency)
        headers = {"Authorization": f"Bearer {self.api_key}"}
        body = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": "You generate concise migration advice for software dependencies."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        import httpx

        with httpx.Client(timeout=20.0) as client:
            resp = client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
        return str(data["choices"][0]["message"]["content"]).strip()


def get_provider(provider_name: str, api_key: str) -> BaseProvider:
    """Return provider implementation by name."""
    normalized = provider_name.lower().strip()
    if normalized == "openai":
        return OpenAIProvider(api_key)
    if normalized == "anthropic":
        return AnthropicProvider(api_key)
    if normalized == "groq":
        return GroqProvider(api_key)
    raise AIProviderError(f"Unsupported AI provider: {provider_name}")


def generate_advice_for_dependencies(
    deps: list[dict[str, Any]],
    provider_name: str,
    api_key: str,
    top_n: int,
) -> list[dict[str, Any]]:
    """Generate migration advice for top-N risky dependencies and inject ai_advice."""
    if top_n <= 0 or not deps:
        return deps

    provider = get_provider(provider_name, api_key)
    ranked = sorted(deps, key=lambda row: int(row.get("risk_score", 0)), reverse=True)
    selected = ranked[:top_n]

    for dep in selected:
        if dep.get("ai_advice"):
            continue

        try:
            dep["ai_advice"] = provider.generate_migration_advice(dep)
        except Exception as exc:  # pragma: no cover - network/provider failures
            print(f"Warning: failed to generate AI advice for {dep.get('name')}: {exc}", file=sys.stderr)

    return deps


def _build_prompt(dependency: dict[str, Any]) -> str:
    return (
        "Provide practical migration advice for this npm dependency. "
        "Respond in Markdown with: why it's risky, upgrade path, potential breaking changes, and quick validation steps.\n\n"
        f"Package: {dependency.get('name')}\n"
        f"Version: {dependency.get('version')}\n"
        f"Risk score: {dependency.get('risk_score')}\n"
        f"Years since update: {dependency.get('last_update_years')}"
    )
