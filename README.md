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
make verify-repeat
make protection-audit
make release-check
```

## Layout

- `SPEC.md` - normative assurance spec
- `conformance/` - schemas, fixtures, canonicalization rules, verifier
- `CONTRIBUTING.md` - PR/merge protocol and branch policy expectations
- `RELEASE_POLICY.md` - tagging and release discipline

## Governance

- Branch protection is expected to enforce PR-first merges and required `verify` checks.
- Run `make protection-audit` to detect protection drift.
- A scheduled GitHub workflow (`protection-audit`) runs daily and uploads audit artifacts.

## Determinism Contract

Conformance requires stable:

- `classification`
- `primary_reason_code`
- `reason_codes` (precedence-ordered)
- canonical report hash (`SHA-256` over canonical JSON bytes)
