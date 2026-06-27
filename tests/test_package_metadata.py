"""Package metadata tests."""

from __future__ import annotations

import tomllib
from pathlib import Path

import codefossil


def test_package_version_matches_project_metadata() -> None:
    """The runtime package version should match the published project version."""
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    metadata = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    assert codefossil.__version__ == metadata["project"]["version"]
