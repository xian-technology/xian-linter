# Architecture

`xian-linter` packages the Xian linting surface as a standalone tool.

Main areas:

- `xian_linter/`: package code
- `tests/`: package tests

This repo should stay thin and depend on the shared authoritative rule surface from `xian-contracting`.

`mode="xian_vm_v1"` is still a wrapper mode, not a separate rule
implementation. It delegates VM compatibility and IR lowering to
`xian-contracting`, then optionally asks `xian_vm_core` to validate the emitted
IR when the native VM package is installed.
