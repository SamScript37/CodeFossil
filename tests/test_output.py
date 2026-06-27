"""Output formatter tests."""

from __future__ import annotations

import json

from codefossil.output.formatter import to_json, to_markdown

SAMPLE_RESULTS = [
    {
        "name": "ancient-lib",
        "version": "1.0.0",
        "last_update_years": 5.2,
        "risk_score": 90,
        "risk_label": "HIGH",
        "ai_advice": "Upgrade to 2.x and run the compatibility suite.",
    },
    {
        "name": "fresh-lib",
        "version": "3.1.0",
        "last_update_years": 0.4,
        "risk_score": 10,
        "risk_label": "LOW",
    },
]


def test_to_json_returns_parseable_pretty_json() -> None:
    """JSON output should be machine-friendly and lossless."""
    rendered = to_json(SAMPLE_RESULTS)

    assert json.loads(rendered) == SAMPLE_RESULTS
    assert rendered.startswith("[\n  {")


def test_to_markdown_includes_summary_dependency_details_and_ai_advice() -> None:
    """Markdown output should be readable for humans and include optional AI advice."""
    rendered = to_markdown(SAMPLE_RESULTS)

    assert "# CodeFossil Report" in rendered
    assert "- Total dependencies: 2" in rendered
    assert "- High risk: 1" in rendered
    assert "- Medium risk: 0" in rendered
    assert "### ancient-lib" in rendered
    assert "- Risk score: 90" in rendered
    assert "- Status: HIGH" in rendered
    assert "- AI advice: Upgrade to 2.x and run the compatibility suite." in rendered
    assert "### fresh-lib" in rendered
