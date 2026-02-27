# AAA (Assured Agentic Architecture)

Validation-first assurance artifacts for autonomous execution under evolving governance.

This repository is intentionally scoped to the assurance layer:

- deterministic validation outputs
- reason-code taxonomy with precedence
- canonical report schema
- minimal receipt schema
- deterministic compatibility calculus
- golden conformance fixtures
- hash-stable verification harness

It excludes runtime orchestration and model routing.

## Quick Start

```bash
make verify
```

## Layout

- `SPEC.md` - normative assurance spec
- `conformance/` - schemas, fixtures, canonicalization rules, verifier

## Determinism Contract

Conformance requires stable:

- `classification`
- `primary_reason_code`
- `reason_codes` (precedence-ordered)
- canonical report hash (`SHA-256` over canonical JSON bytes)
