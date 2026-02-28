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
make feature-gate
make protection-audit
make release-check
# after a tag push
make release-receipt TAG=vX.Y.Z
```

## CLI

Run from repo root:

```bash
./eal verify-receipt --contract contract.json --receipt receipt.json
./eal revalidate --contract-origin contract_e1.json --contract-target contract_e2.json --receipt receipt.json
./eal compat --contract-a contract_a.json --contract-b contract_b.json
```

Flags:

- `--out <path>` write report JSON to file
- `--pretty` emit indented JSON (default is canonical compact JSON)
- `--print-hash` print report SHA-256 to stderr
- `--schema-check` validate output against conformance schema

Exit codes:

- `verify-receipt`: `0=VALID`, `10=INVALID`, `11=INVALIDATED`, `12=INDETERMINATE`
- `revalidate`: `0=VALID`, `10=INVALID`, `11=INVALIDATED`, `12=INDETERMINATE`
- `compat`: `0=BACKWARD_COMPATIBLE`, `20=CONDITIONAL`, `21=INCOMPATIBLE`

## Layout

- `SPEC.md` - normative assurance spec
- `conformance/` - schemas, fixtures, canonicalization rules, verifier
  - includes `experimental_feature_gate.json` and `verify_feature_gate.py`
- `CONTRIBUTING.md` - PR/merge protocol and branch policy expectations
- `RELEASE_POLICY.md` - tagging and release discipline
- `OPERATING_MODEL.md` - operator authority, rollback protocol, release receipts

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
