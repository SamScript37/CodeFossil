"""Output formatters for CodeFossil results."""

from __future__ import annotations

import json
from typing import Any


def to_json(results: list[dict[str, Any]]) -> str:
    """Return formatted JSON output."""
    return json.dumps(results, indent=2)


def to_markdown(results: list[dict[str, Any]]) -> str:
    """Return a readable Markdown report."""
    total = len(results)
    high = sum(1 for item in results if int(item.get("risk_score", 0)) >= 70)
    medium = sum(1 for item in results if 40 <= int(item.get("risk_score", 0)) < 70)

    lines = [
        "# CodeFossil Report",
        "",
        "## Summary",
        f"- Total dependencies: {total}",
        f"- High risk: {high}",
        f"- Medium risk: {medium}",
        "",
        "## Dependencies",
        "",
    ]

    for item in results:
        lines.extend(
            [
                f"### {item['name']}",
                f"- Version: {item['version']}",
                f"- Risk score: {item['risk_score']}",
                f"- Status: {item.get('risk_label', _risk_label(int(item['risk_score'])))}",
                *( [f"- AI advice: {item['ai_advice']}"] if item.get('ai_advice') else [] ),
                "",
            ]
        )

    lines.extend(["---", ""])
    return "\n".join(lines)


def _risk_label(score: int) -> str:
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"
