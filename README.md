# xian-linter

`xian-linter` is a Python linter specifically for Xian smart contracts. It
combines PyFlakes with the structured linter exposed by `xian-contracting`, so
rule violations include stable error codes and source positions.

The published PyPI package name is `xian-tech-linter`. The import package and
console command remain `xian_linter` and `xian-linter`.

## Quick Start

Base package:

```bash
pip install xian-tech-linter
```

Inline use:

```python
from xian_linter import lint_code_inline

errors = lint_code_inline("def transfer():\n    pass\n")
```

Structured sync API:

```python
from xian_linter import LintErrorModel, lint_code_sync

errors: list[LintErrorModel] = lint_code_sync(
    "@export\ndef transfer():\n    return missing_name\n"
)
```

## Principles

- Keep the package focused on contract linting, not runtime execution.
- Expose the same rule surface in both inline and server modes.
- Prefer stable error codes and positions so tooling can build on top of the
  linter reliably.
- Keep the structured result types importable from the package root so callers
  do not need to reach into internal modules.
- Keep server mode optional. The core package should still be useful as a local
  linting dependency.

## Key Directories

- `xian_linter/`: package code, server entrypoints, and inline API
- `tests/`: package and server-mode coverage
- `docs/`: repo-local notes and backlog

## Validation

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Related Docs

- [AGENTS.md](AGENTS.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/BACKLOG.md](docs/BACKLOG.md)
- [docs/README.md](docs/README.md)

## Usage Modes

- Inline/programmatic usage:

```python
from xian_linter import lint_code_inline, lint_code_sync

inline_errors = lint_code_inline("def transfer():\n    pass\n")
sync_errors = lint_code_sync("def transfer():\n    pass\n")
```

- Standalone server mode:

```bash
pip install "xian-tech-linter[server]"
xian-linter
uvicorn xian_linter.server:create_app --factory --host 0.0.0.0 --port 8000
```
