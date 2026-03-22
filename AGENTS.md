# Repository Guidelines

## Scope
- `xian-linter` is the standalone linting wrapper around the Xian contract rules.
- Keep the authoritative contract-rule semantics in `xian-contracting`; this repo should wrap and expose them cleanly.
- Avoid duplicating runtime semantics here.

## Project Layout
- `xian_linter/`: package code and service entrypoints
- `tests/`: package-level tests
- `docs/`: internal architecture and backlog notes

## Workflow
- Favor consuming shared logic from `xian-contracting` instead of copying it.
- Keep the package small and focused on linting UX and integration surfaces.

