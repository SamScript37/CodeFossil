"""CLI smoke tests."""

from pathlib import Path

from typer.testing import CliRunner

from codefossil.cli.main import app


def test_cli_help_smoke() -> None:
    """Ensure CLI help executes without crashing."""
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Scan projects for outdated dependencies." in result.stdout


def test_scan_accepts_project_path_argument() -> None:
    """Ensure `scan .` is parsed as a command argument, not an unexpected token."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        Path("package.json").write_text('{"dependencies": {}}', encoding="utf-8")
        result = runner.invoke(app, ["scan", ".", "--format", "json"])

    assert result.exit_code == 0
    assert result.stdout.strip().startswith("[")
