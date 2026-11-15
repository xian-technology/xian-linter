# Architecture

`xian-linter` packages the Xian linting surface as a standalone tool.

Main areas:

- `xian_linter/`: package code
- `tests/`: package tests

This repo stays thin and consumes authoritative Rust compiler diagnostics
directly from `xian_compiler_core` (`diagnose_contract`, and
`compile_contract_source` for the IR a node would deploy). Its runtime
dependencies are `xian-tech-compiler-core` and `xian-tech-vm-core`; it does
not need `xian-tech-contracting`.

The default mode is `xian_vm_v2`. The explicit legacy `python` mode runs V1
compiler diagnostics only before PyFlakes. The `xian_vm_v1` and `xian_vm_v2`
modes pass the selected profile to compiler diagnostics and IR lowering, then
ask `xian_vm_core.validate_module_ir_json` to validate the emitted IR as a
required dependency: the VM's IR rules live only in vm-core, so the linter
calls them rather than copying them. PyFlakes
recognizes the numeric helpers provided by the selected profile.
