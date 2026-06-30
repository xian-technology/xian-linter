# Repository Guidelines

## Scope
- `xian-linter` is the standalone linting wrapper around the Xian contract rules.
- Keep the authoritative contract-rule semantics in `xian-contracting`; this repo should wrap and expose them cleanly.
- Avoid duplicating runtime semantics here.

## Shared Convention
- Follow the shared repo convention in `xian-meta/docs/REPO_CONVENTIONS.md`.
- Keep this repo aligned with that standard for root docs, backlog notes, and package/folder entrypoints.
- Follow the shared change workflow in `xian-meta/docs/CHANGE_WORKFLOW.md`.
- Before push, review whether `xian-docs-web` needs updates and run the local validation path for this repo.

## Project Layout
- `xian_linter/`: package code and service entrypoints
- `tests/`: package-level tests
- `docs/`: internal architecture and backlog notes

## Workflow
- Favor consuming shared logic from `xian-contracting` instead of copying it.
- Keep the package small and focused on linting UX and integration surfaces.

## Validation
- Preferred setup: `uv sync --group dev`
- Lint: `uv run ruff check .`
- Format check: `uv run ruff format --check .`
- Tests: `uv run pytest`

## Shared Agent Practices
- Keep changes clean, modular, and professional. Prefer small, cohesive modules, clear naming, explicit boundaries, and tests over quick patches.
- When code behavior, public APIs, user workflows, operator workflows, or configuration semantics change, check whether `../xian-docs-web` needs corresponding documentation updates. If this repo is `xian-docs-web`, update the relevant published docs in place. Write durable user/developer documentation, not a changelog entry.
- For codebase questions, use the local graph first when `graphify-out/graph.json` exists: run `graphify query "<question>"`; use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts.
- Dirty `graphify-out/` files are expected after hooks or incremental updates and are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- Use `graphify-out/wiki/index.md` for broad navigation when it exists. Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review or when query/path/explain do not surface enough context.
- For any non-trivial code change, update the local graph before final verification when `graphify-out/graph.json` exists. Run `graphify update .` from the repo root, or `graphify update . --force` when deletions or refactors intentionally shrink the graph.
- After updating the graph, check cross-repo impact before finishing: query the local graph, inspect paths with `graphify path` or `graphify explain`, and note any affected sibling repos.
- If graphify or dependency analysis shows affected sibling repos, update those repos in the same change when the impact is real and the fix is in scope.
- Treat `graphify-out/` as a generated local artifact. Do not commit it.
