# AAA Minimal Reference Kernel Outline (Language-Agnostic)

**Document ID:** AAA-KRO-V1
**Version:** 1.0.0
**Targets:** AAA-CONF-V1 Level A (optionally B/C modules)
**Kernel Boundary:** L3.5 only. No orchestration. No tool logic. No reasoning.
**Last Updated:** 2026-03-01

---

## 0. Inputs / Outputs

### Inputs

- **Intent Contract (IC):** JSON accepted at ingress, normalized to internal JSON object.
- **Kernel Config (KC):** Pinned versions, policies, keys, schema refs, canonicalization rules.
- **Evidence Attachments (optional):** External evidence blobs referenced by hash (not fetched by kernel).

### Outputs

- **Execution Decision:** `ALLOW` | `DENY`
- **Receipt (RC):** Deterministic evidence record (plus signature for Level B+)
- **Exit Code:** Deterministic failure code mapping

---

## 1. Mandatory Modules (Level A)

### M1 -- Ingress & Parse

**Responsibility:**
- Accept IC (bytes/string), parse into structured object.
- Reject non-JSON inputs deterministically.

**Invariants:**
- UTF-8 input only (reject otherwise).
- No implicit coercions beyond spec.

**Failure codes:**
- `PARSE_ERROR`
- `ENCODING_ERROR`

**EAL reference:** `E_INPUT_MALFORMED` covers both parse and encoding failures.

### M2 -- Schema Validation (Intent Contract)

**Responsibility:**
- Validate IC against published JSON Schema (Draft 2020-12 or pinned equivalent).

**Invariants:**
- Validation occurs before any other semantic checks.
- Deterministic error classification.

**Failure codes:**
- `SCHEMA_VALIDATION_ERROR`

**EAL reference:** Maps to `E_INPUT_MALFORMED` in the existing failure taxonomy.

### M3 -- Canonicalization

**Responsibility:**
- Convert validated IC into canonical byte stream.

**Normative canonicalization rules:**
- Object keys: lexicographic ordering (Unicode codepoint).
- Arrays: preserve order.
- Strings: UTF-8; no NFC normalization unless explicitly pinned.
- Numbers: preserve as-parsed; prohibit floats unless rules specified.
- Whitespace: none (minified JSON).
- Newlines: no trailing newline.
- Encoding: exact UTF-8 bytes.

**Output:** `canonical_bytes`

**Failure codes:**
- `CANONICALIZATION_ERROR`

**EAL reference:** `aaa_eal.core.canonical_json_bytes()` -- `json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=False).encode("utf-8")`

### M4 -- Hashing

**Responsibility:**
- Compute `intent_hash = SHA-256(canonical_bytes)`.

**Invariants:**
- Hash is over canonical bytes only.
- Hash algorithm and version are pinned.

**Failure codes:**
- `HASH_ERROR`

**EAL reference:** `aaa_eal.core.sha256_hex()`

### M5 -- Policy Gate (AAA-local, deterministic)

**Responsibility:**
- Enforce kernel-local rules that are necessary for boundary safety.

**Allowed checks:**
- Required fields present beyond schema (if schema cannot express them).
- Allowed authority values.
- Allowed action values (if kernel pins action surface).
- Max size limits (bytes, nesting depth) to prevent DoS.
- Governance version pin check (may be delegated to M6).

**Forbidden:**
- Any dynamic decision requiring external calls.
- Any reasoning.
- Any orchestration.

**Failure codes:**
- `POLICY_VIOLATION`

**EAL reference:** Corresponds to `E_ACTION_OUT_OF_SPACE`, `E_BOUNDARY_MISMATCH` in the EAL failure taxonomy.

### M6 -- Governance Version Pin Check

**Responsibility:**
- Verify `governance_version` in IC is compatible with KC pin.

**Outputs:**
- `compat`: `BACKWARD_COMPATIBLE` | `CONDITIONAL` | `INCOMPATIBLE`

**Default behavior:**
- If `INCOMPATIBLE` -> `DENY`
- If `CONDITIONAL` -> either `DENY` or `ALLOW_WITH_WARN` (decision must be deterministic and pinned)

**Failure codes:**
- `GOVERNANCE_INCOMPATIBLE`

**EAL reference:** `aaa_eal.core.evaluate_compat()` with `COMPAT_EXIT_CODES`.

### M7 -- Failure Precedence Resolver

**Responsibility:**
- If multiple checks fail, emit one primary failure code by deterministic precedence order.

**Invariant:**
- Precedence table is a pinned artifact.

**Example precedence (pin exactly):**
1. `ENCODING_ERROR`
2. `PARSE_ERROR`
3. `SCHEMA_VALIDATION_ERROR`
4. `CANONICALIZATION_ERROR`
5. `HASH_ERROR`
6. `GOVERNANCE_INCOMPATIBLE`
7. `POLICY_VIOLATION`

**EAL reference:** `aaa_eal.core.EAL_PRECEDENCE` (13-element ordered list) and `ordered_reason_codes()`.

### M8 -- Receipt Builder

**Responsibility:**
- Build RC from normalized fields.

**Receipt schema (minimum):**
- `receipt_schema_version`
- `kernel_version`
- `governance_version_pin`
- `intent_hash`
- `canonicalization_id` (identifier of the canonicalization ruleset)
- `hash_alg`
- `decision`: `ALLOW` | `DENY`
- `primary_code`
- `compat_class` (if applicable)
- `ts_rfc3339` (timestamp)

**Determinism note:**

Timestamps break bitwise determinism across runs. Two compliant patterns:

**Pattern A (recommended): Timestamp outside determinism domain**
- Receipt has:
  - `receipt_body` (deterministic)
  - `receipt_meta` (non-deterministic: timestamp, host)
- Hash/sign `receipt_body` only.

**Pattern B: Timestamp pinned input**
- Timestamp is part of IC and therefore canonicalized. Rarely desired.

Pick one and pin. Default: Pattern A.

**EAL reference:** `aaa_eal.core.evaluate_validation()` returns a report dict (the receipt). The existing EAL uses a Pattern A variant -- `evaluated_epoch` is deterministic, but the receipt itself does not include a timestamp field (determinism by omission).

### M9 -- Receipt Hash + (Optional) Signature

**Responsibility:**
- Compute `receipt_hash = SHA-256(canonical(receipt_body))`
- Level B+: sign `receipt_hash` (or sign canonical receipt bytes).

**Failure codes:**
- `RECEIPT_BUILD_ERROR`
- `SIGNATURE_ERROR` (Level B+)

**EAL reference:** `conformance/verify_conformance.py` computes `sha256_hex(expected_report)` and compares against `expected_report_sha256`.

### M10 -- Gate Output Adapter

**Responsibility:**
- Convert decision into:
  - Process exit code
  - stdout/stderr messages
  - File outputs (optional)

**Invariant:**
- Exit codes must map 1:1 to failure codes.
- Output format pinned (JSON recommended).

**EAL reference:** `aaa_eal.core.VALIDATION_EXIT_CODES` and `COMPAT_EXIT_CODES` + `aaa_eal/cli.py` command handlers.

---

## 2. Control Flow (Single-Pass, Fail-Closed)

**Algorithm:**

1. Parse input -> `ic_obj` or fail
2. Validate schema -> fail if invalid
3. Canonicalize -> `canonical_bytes` or fail
4. Hash -> `intent_hash` or fail
5. Policy gate checks -> collect violations
6. Governance pin compatibility -> collect violation if incompatible
7. Resolve primary failure by precedence
8. Decide `ALLOW` iff no failures
9. Emit receipt (body deterministic; meta optional)
10. Emit exit code and artifacts

**Fail-closed:** Any unhandled exception treated as deterministic failure code `INTERNAL_ERROR` (avoid by design; only as last resort).

---

## 3. Minimal Data Artifacts (Repo Layout)

```
aaa_kernel/
  spec/
    AAA_ARCHITECTURE_v1.md
    AAA_CONFORMANCE_PROFILE_v1.md
    AAA_TEST_VECTOR_SUITE_v1.md
  schemas/
    intent_contract.schema.json
    receipt.schema.json
  canonicalization/
    canonicalization_rules_v1.md
    canonicalization_id_v1.txt
  failure/
    failure_codes_v1.json
    failure_precedence_v1.json
  fixtures/
    tv-a1.intent.json
    tv-a1.canonical.json
    tv-a1.sha256.txt
    ...
  bin/
    aaa_gate.(sh|cmd)         # thin wrapper
  kernel/
    (implementation files)
```

**EAL mapping:**

| Reference Layout | EAL-AAA Equivalent |
|------------------|--------------------|
| `spec/` | `spec/` (this directory) |
| `schemas/` | `conformance/*.schema.json` |
| `canonicalization/` | `conformance/CANONICALIZATION.md` |
| `failure/` | `conformance/FAILURE_CODES.md` |
| `fixtures/` | `conformance/fixtures/`, `conformance/fixtures_compat/`, etc. |
| `bin/` | `./eal` (CLI entry point) |
| `kernel/` | `aaa_eal/` (Python package) |

---

## 4. Public Interfaces

### CLI Interface (reference)

```bash
aaa-gate verify --intent <path> --out <dir> [--config <path>]
```

**Outputs in `<dir>`:**
- `receipt_body.json`
- `receipt_meta.json` (optional)
- `receipt_body.sha256`
- `receipt.sig` (Level B+)
- `decision.json`

### EAL-AAA CLI (actual)

```bash
./eal verify-receipt  --contract <path> --receipt <path> [--schema-check]
./eal revalidate      --origin <path> --target <path> --receipt <path>
./eal compat          --contract-a <path> --contract-b <path>
```

Exit codes: `0` (VALID/BACKWARD_COMPATIBLE), `10` (INVALID), `11` (INVALIDATED), `12` (INDETERMINATE), `20` (CONDITIONAL), `21` (INCOMPATIBLE).

---

## 5. Deterministic Testing Harness

**Required:**

- Run all vectors from AAA-TVS-V1.
- Verify:
  - Canonical output exact match
  - Hash exact match
  - `receipt_body` exact match
  - Signature validates (Level B+)

**CI gates:**
- Schema validation of all fixtures.
- Hash comparison against expected.
- Non-determinism check: run same vector twice; compare `receipt_body`.

**EAL equivalent:** `make verify` and `make verify-repeat`.

---

## 6. Security Notes (Kernel-Specific)

**Threats:**
- Input DoS (deep nesting, huge payload)
- Parser differentials across languages
- Float / number normalization drift
- Unicode normalization drift
- Time-based nondeterminism
- Secret leakage via receipts/logs

**Mitigations:**
- Size/depth caps (pinned)
- Reject floats unless rules are explicit
- Pin canonicalization algorithm and ID
- Hash/sign deterministic body only
- Never include secrets in IC/RC

---

## 7. Extension Modules (Optional, Levels B/C)

### B1 -- Signing Key Management
- Keys not generated by kernel.
- Kernel only signs; key provisioning external.
- Rotation policy pinned.

### C1 -- MRCC Bundle Emitter
- Emit MRCC-compatible evidence package referencing receipt hashes.
- No claim issuance inside kernel unless explicitly included in conformance level.

### C2 -- Cross-Repo Monotonicity Checker
- Operates on local evidence store only.
- No network calls inside kernel.

---

## 8. Minimal Compliance Claim

A "minimal reference kernel" MUST implement:

- M1-M10 exactly
- Pattern A or B determinism strategy (pinned)
- TV-A and TV-F passing (AAA-TVS-V1)

---

## 9. Implementation Notes for EAL-AAA

The existing `aaa_eal` package (v0.2.0) implements a superset of this reference outline:

| Module | EAL-AAA Status |
|--------|----------------|
| M1 (Ingress) | `normalize_validation_receipt()`, `normalize_validation_contract()` |
| M2 (Schema) | JSON Schema files + `_maybe_schema_validate()` |
| M3 (Canonicalization) | `canonical_json_bytes()` |
| M4 (Hashing) | `sha256_hex()` |
| M5 (Policy Gate) | `evaluate_validation()` (action space, boundary checks) |
| M6 (Governance Pin) | `evaluate_compat()` |
| M7 (Precedence) | `EAL_PRECEDENCE` + `ordered_reason_codes()` |
| M8 (Receipt Builder) | `evaluate_validation()` return dict |
| M9 (Receipt Hash) | `sha256_hex(report)` in conformance verifier |
| M10 (Gate Output) | `VALIDATION_EXIT_CODES`, `COMPAT_EXIT_CODES`, `cli.py` |

The EAL-AAA kernel is **Level A conformant** by construction.
