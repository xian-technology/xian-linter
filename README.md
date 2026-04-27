# xian-linter

`xian-linter` is a Python linter specifically for Xian smart contracts. It
combines PyFlakes with the structured linter exposed by
[`xian-contracting`](../xian-contracting), so rule violations come back with
stable error codes and source positions that downstream tools can rely on.

The published PyPI package is `xian-tech-linter`. The import package and
console command remain `xian_linter` and `xian-linter`. The package can be
used inline (as a dependency in another tool) or as an HTTP server when the
`server` extra is installed.

## Quick Start

Install the base package:

```bash
pip install xian-tech-linter
```

Lint inline (lightweight, position-only diagnostics):

```python
from xian_linter import lint_code_inline

errors = lint_code_inline("def transfer():\n    pass\n")
```

Get fully-typed structured results:

```python
from xian_linter import LintErrorModel, lint_code_sync

errors: list[LintErrorModel] = lint_code_sync(
    "@export\ndef transfer():\n    return missing_name\n"
)
```

Validate against the `xian_vm_v1` target:

```bash
pip install "xian-tech-linter[vm]"
```

```python
from xian_linter import lint_code_sync

errors = lint_code_sync(source, mode="xian_vm_v1")
```

Run as a standalone HTTP server:

```bash
pip install "xian-tech-linter[server]"
xian-linter
# or, with full ASGI control:
uvicorn xian_linter.server:create_app --factory --host 0.0.0.0 --port 8000
```

## Principles

- **Linting only.** The package focuses on contract linting; runtime
  execution and contract submission belong elsewhere.
- **One rule surface, multiple integration modes.** Inline and server modes
  expose the same rules and error codes.
- **VM-aware without duplicated semantics.** `mode="xian_vm_v1"` delegates to
  `xian-contracting` for VM compatibility and IR lowering, and uses the native
  `xian_vm_core` IR validator when the `vm` extra is installed.
- **Stable codes and positions.** Tooling (IDE plugins, CI gates, the
  contracting hub) can rely on consistent error codes and source positions
  to render diagnostics.
- **Importable from the root.** `LintErrorModel`, `lint_code_inline`, and
  `lint_code_sync` are importable from the package root — callers do not
  reach into internal modules.
- **Optional server.** The core package is useful as a local linting
  dependency without installing the server extra.

## Key Directories

- `xian_linter/` — package code:
  - `linter.py` — core lint engine combining PyFlakes and the structured
    `xian-contracting` linter.
  - `server.py` — optional FastAPI / ASGI server (`server` extra).
  - `__main__.py` — `xian-linter` console entrypoint.
- `tests/` — inline and server-mode coverage.
- `docs/` — architecture and backlog notes.

## Usage Modes

- **Inline / programmatic** — for in-process linting from another Python
  tool:
  ```python
  from xian_linter import lint_code_inline, lint_code_sync
  inline_errors = lint_code_inline("def transfer():\n    pass\n")
  sync_errors   = lint_code_sync("def transfer():\n    pass\n")
  vm_errors     = lint_code_sync(source, mode="xian_vm_v1")
  ```
- **HTTP server** — for editor / IDE integrations, CI runners, or remote
  linting from web frontends:
  ```bash
  pip install "xian-tech-linter[server]"
  xian-linter
  ```
  Select the VM target with `?mode=xian_vm_v1` on `/lint`, `/lint_base64`, or
  `/lint_gzip`. Install `xian-tech-linter[server,vm]` when the server should
  also run native IR validation through `xian_vm_core`.

## Validation

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Related Docs

- [AGENTS.md](AGENTS.md) — repo-specific guidance for AI agents and contributors
- [docs/README.md](docs/README.md) — index of internal docs
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — major components and dependency direction
- [docs/BACKLOG.md](docs/BACKLOG.md) — open work and follow-ups
