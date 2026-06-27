"""CLI smoke tests."""

from pathlib import Path

from typer.testing import CliRunner

from codefossil.cli import main as cli_main


def test_cli_help_smoke() -> None:
    """Ensure CLI help executes without crashing."""
    runner = CliRunner()
    result = runner.invoke(cli_main.app, ["--help"])

    assert result.exit_code == 0
    assert "Scan projects for outdated dependencies." in result.stdout


def test_scan_accepts_project_path_argument(tmp_path: Path) -> None:
    """Ensure `scan .` is parsed as a command argument, not an unexpected token."""
    runner = CliRunner()

    (tmp_path / "package.json").write_text('{"dependencies": {}}', encoding="utf-8")
    result = runner.invoke(cli_main.app, ["scan", str(tmp_path), "--format", "json"])

    assert result.exit_code == 0
    assert result.stdout.strip().startswith("[")


def test_scan_table_output_writes_rendered_report(tmp_path: Path, monkeypatch) -> None:
    """Table reports written to disk should contain rendered text, not object reprs."""

    def fake_analyze_project(
        _project_path: Path,
        include_dev: bool = False,
    ) -> list[dict[str, object]]:
        return [
            {
                "name": "legacy-lib",
                "version": "1.0.0",
                "last_update_years": 4.2,
                "risk_score": 70,
                "risk_label": "HIGH",
            }
        ]

    monkeypatch.setattr(cli_main, "analyze_project", fake_analyze_project)

    output_path = tmp_path / "report.txt"
    result = CliRunner().invoke(
        cli_main.app,
        ["scan", str(tmp_path), "--output", str(output_path)],
    )

    assert result.exit_code == 0
    report = output_path.read_text(encoding="utf-8")
    assert "CodeFossil Dependency Risk Report" in report
    assert "legacy-lib" in report
    assert "<rich.table.Table" not in report
