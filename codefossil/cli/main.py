"""CLI entrypoint for CodeFossil."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from codefossil.core.pipeline import analyze_project, analyze_project_advanced
from codefossil.output.formatter import to_json, to_markdown
from codefossil.scanner.npm import PackageJsonError

app = typer.Typer(help="Scan projects for outdated dependencies.")
console = Console()


@app.callback()
def main() -> None:
    """CodeFossil command group."""


@app.command("scan")
def scan_command(
    project_path: Annotated[
        Path,
        typer.Argument(
            exists=False,
            file_okay=False,
            dir_okay=True,
            help="Project directory to scan (defaults to current directory).",
        ),
    ] = Path("."),
    output_format: Annotated[
        str, typer.Option("--format", help="Output format: table, json, markdown.")
    ] = "table",
    output: Annotated[
        Path | None,
        typer.Option("--output", help="Write output to a file path instead of stdout."),
    ] = None,
    min_risk: Annotated[
        int,
        typer.Option(
            "--min-risk", help="Only show dependencies at or above this risk score."
        ),
    ] = 0,
    include_dev: Annotated[
        bool,
        typer.Option(
            "--include-dev", help="Include devDependencies from package.json."
        ),
    ] = False,
    ai_provider: Annotated[
        str | None,
        typer.Option("--ai-provider", help="AI provider: openai, anthropic, or groq."),
    ] = None,
    api_key: Annotated[
        str | None,
        typer.Option("--api-key", help="API key for the selected AI provider."),
    ] = None,
    ai_top: Annotated[
        int,
        typer.Option("--ai-top", help="Top N high-risk dependencies for AI advice."),
    ] = 3,
    incremental: Annotated[
        bool,
        typer.Option(
            "--incremental", help="Only analyze dependencies changed since last run."
        ),
    ] = False,
) -> None:
    """Scan a project for stale npm dependencies and display a risk report."""
    if ai_provider and not api_key:
        typer.echo(
            "Warning: --ai-provider was set but --api-key is missing. Skipping AI advice.",
            err=True,
        )

    if not project_path.exists() or not project_path.is_dir():
        console.print(
            f"[red]Error:[/red] Project path not found or not a directory: {project_path}"
        )
        raise typer.Exit(code=1)

    try:
        if ai_provider or incremental:
            results = analyze_project_advanced(
                project_path,
                include_dev=include_dev,
                incremental=incremental,
                ai_provider_name=ai_provider,
                api_key=api_key,
                ai_top=ai_top,
            )
        else:
            results = analyze_project(project_path, include_dev=include_dev)
    except (FileNotFoundError, PackageJsonError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # pragma: no cover
        console.print(f"[red]Unexpected error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    filtered = [item for item in results if int(item["risk_score"]) >= min_risk]

    format_key = output_format.lower().strip()
    if format_key not in {"table", "json", "markdown"}:
        console.print(
            "[red]Error:[/red] --format must be one of: table, json, markdown"
        )
        raise typer.Exit(code=2)

    if format_key == "table":
        if not filtered:
            console.print("[yellow]No dependencies matched the risk criteria.[/yellow]")
            return

        table = render_table(filtered)
        if output is not None:
            output.write_text(render_table_text(table), encoding="utf-8")
            console.print(f"[green]Saved report to[/green] {output}")
            return

        console.print(table)
        return

    rendered = to_json(filtered) if format_key == "json" else to_markdown(filtered)

    if output is not None:
        output.write_text(rendered, encoding="utf-8")
        return

    if format_key == "json":
        # Must be pure JSON with no extra text.
        print(rendered)
        return

    console.print(rendered)


def render_table(results: list[dict[str, Any]]) -> Table:
    """Render scan output in a rich table sorted by risk descending."""
    table = Table(title="CodeFossil Dependency Risk Report")
    table.add_column("Package", style="cyan", no_wrap=True)
    table.add_column("Version", style="magenta")
    table.add_column("Years since update", justify="right")
    table.add_column("Risk score", justify="right", style="bold")
    table.add_column("Status", justify="center")

    for item in sorted(results, key=lambda row: int(row["risk_score"]), reverse=True):
        score = int(item["risk_score"])
        years = f"{float(item['last_update_years']):.2f}"
        risk_style = "red" if score >= 70 else "yellow" if score >= 40 else "green"
        table.add_row(
            str(item["name"]),
            str(item["version"]),
            years,
            f"[{risk_style}]{score}[/{risk_style}]",
            f"[{risk_style}]{item.get('risk_label', '')}[/{risk_style}]",
        )

    return table


def render_table_text(table: Table) -> str:
    """Render a Rich table to plain text for file output."""
    buffer = StringIO()
    file_console = Console(file=buffer, force_terminal=False, color_system=None)
    file_console.print(table)
    return buffer.getvalue()


if __name__ == "__main__":
    app()
