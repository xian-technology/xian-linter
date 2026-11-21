# Backlog

This is the stable backlog entrypoint for `xian-linter`.

Current themes:

- keeping the package aligned with `xian-contracting`
- improving packaging and service ergonomics without adding rule duplication

## Fully Rust-based linter

Planned future work; no implementation is scheduled yet.

Replace the Python linting implementation and optional HTTP service with a
fully Rust-based linter that can be distributed and run without Python.
The contract rules and IR validation already use the Rust compiler core and
VM core directly; this work removes the remaining Python tooling dependency
rather than changing contract execution or compiler authority.

Scope and acceptance criteria:

- Reuse the existing compiler-core and VM-core crates. Keep authoritative
  contract semantics in those crates rather than duplicating rules here.
- Replace PyFlakes with Rust-based checks that preserve useful warnings,
  including undefined names, and recognize Xian built-ins for each supported
  profile. Compare results against the existing lint fixtures.
- Preserve diagnostic codes, severity, source positions and ordering, custom
  built-in whitelists, and the V2 default. Review legacy modes explicitly
  before changing or removing them.
- Preserve the HTTP API and its transport limits, CORS configuration and local
  bind defaults, or document and coordinate any intentional API changes.
- Provide a standalone native executable. Review inline Python API consumers
  and retain a thin binding if needed; the native tool must not require Python.
- Validate compiler/VM diagnostic parity and warning compatibility, then update
  packaging, release automation, integrations and public documentation as needed.

