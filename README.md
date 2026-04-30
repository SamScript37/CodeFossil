# CodeFossil

CodeFossil is a production-ready Python CLI that scans JavaScript projects for stale npm dependencies, assigns risk scores, and optionally adds AI migration guidance for the highest-risk packages.

## What it does

- Scans npm `dependencies` and (optionally) `devDependencies`
- Queries registry metadata to estimate dependency freshness
- Assigns a deterministic risk score based on update age
- Supports rich terminal table output plus machine-friendly JSON and Markdown reports
- Supports incremental analysis via local cache (`.codefossil_cache.json`)
- Optionally enriches top-risk dependencies with AI advice (`openai`, `anthropic`, `groq`)

## Installation

### Standard install

```bash
pip install .
```

### Editable install for development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Usage

### Basic scan

```bash
codefossil scan .
```

### Common flags

- `--format table|json|markdown`
- `--output <file>`
- `--min-risk <int>`
- `--include-dev`
- `--incremental`
- `--ai-provider openai|anthropic|groq`
- `--api-key <key>`
- `--ai-top <int>`

### Examples

```bash
# JSON output
codefossil scan . --format json

# Markdown report with filtering
codefossil scan . --format markdown --output report.md --include-dev --min-risk 50

# Incremental analysis
codefossil scan . --incremental

# AI advice for top 5 risky dependencies
codefossil scan . --ai-provider openai --api-key sk-xxx --ai-top 5 --format markdown
```

## AI feature (optional)

When `--ai-provider` and `--api-key` are supplied, CodeFossil asks the provider for migration guidance for the top `--ai-top` risky dependencies. If provider calls fail, scanning continues and warnings are emitted.

No API keys are persisted to disk.

## Output schema

Each dependency result includes:

- `name`
- `version`
- `last_update_years`
- `risk_score`
- `risk_label` (`HIGH`, `MEDIUM`, `LOW`)
- `ai_advice` (optional)

## Risk scoring model

- `>= 5` years: `90`
- `>= 3` years: `70`
- `>= 2` years: `50`
- `>= 1` year: `30`
- `< 1` year: `10`

## Development

```bash
pip install -e .[dev]
pytest
ruff check .
black --check .
mypy codefossil
```

A sample manifest is available at `examples/package.sample.json` for manual testing.
