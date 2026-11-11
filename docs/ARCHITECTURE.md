# Architecture

`xian-linter` packages the Xian linting surface as a standalone tool.

Main areas:

- `xian_linter/`: package code
- `tests/`: package tests

This repo stays thin and consumes authoritative Rust compiler diagnostics
through `contracting.artifacts`.

The default mode is `xian_vm_v2`. The explicit legacy `python` mode runs V1
compiler diagnostics only before PyFlakes. The `xian_vm_v1` and `xian_vm_v2`
modes pass the selected profile to compiler diagnostics and IR lowering, then
ask `xian_vm_core` to validate the emitted IR as a required dependency. PyFlakes
recognizes the numeric helpers provided by the selected profile.
