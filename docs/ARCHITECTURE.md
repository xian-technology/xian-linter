# Architecture

`xian-linter` packages the Xian linting surface as a standalone tool.

Main areas:

- `xian_linter/`: package code
- `tests/`: package tests

This repo stays thin and consumes authoritative Rust compiler diagnostics
through `contracting.artifacts`.

Both public mode names use that same compiler path. `mode="xian_vm_v1"` is a
wrapper mode, not a separate rule implementation; it additionally asks
`xian_vm_core` to validate emitted IR when the native VM package is installed.
