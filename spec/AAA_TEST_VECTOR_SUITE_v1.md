# AAA Test Vector Suite v1

**Document ID:** AAA-TVS-V1
**Version:** 1.0.0
**Status:** Canonical Test Vector Suite for AAA v1
**Depends On:**
- AAA-ARCH-V1 (v1.0.0)
- AAA-CONF-V1 (v1.0.0)

**Last Updated:** 2026-03-01

---

## 1. Purpose

This document defines the mandatory test vectors and verification procedures required to validate conformance with:

> AAA v1 Conformance Profile (Levels A, B, C)

This suite verifies:

- Deterministic canonicalization
- Hash stability
- Failure precedence
- Receipt determinism
- Governance pin enforcement
- Replay integrity
- Environment independence

**All test vectors are normative.**

---

## 2. Normative Test Environment Requirements

Implementations MUST:

- Use UTF-8 encoding
- Use SHA-256 (minimum) for hashing
- Use RFC3339 timestamps
- Exclude trailing newline from canonical byte stream
- Define deterministic field ordering (lexicographic key sort)

Time MUST NOT influence canonical hash unless explicitly included in canonical payload.

---

## 3. Canonical Intent Contract Schema (Test Baseline)

For all vectors below, assume canonical minimal schema:

```json
{
  "intent_id": "string",
  "version": "string",
  "authority": "string",
  "action": "string",
  "parameters": "object",
  "governance_version": "string"
}
```

Field ordering MUST be lexicographically sorted for canonicalization.

---

## 4. Determinism Vectors (Level A Required)

### TV-A1 -- Basic Deterministic Canonicalization

**Input (Unordered JSON):**
```json
{
  "action": "deploy",
  "authority": "human",
  "parameters": {"env": "prod"},
  "intent_id": "abc-123",
  "version": "1.0",
  "governance_version": "v1.0"
}
```

**Expected Canonical Form (Lexicographic Ordering):**
```
{"action":"deploy","authority":"human","governance_version":"v1.0","intent_id":"abc-123","parameters":{"env":"prod"},"version":"1.0"}
```

**Expected SHA-256:**

Implementations MUST compute SHA-256 over exact byte stream of canonical form.

**Validation:**
- Reordering fields MUST produce identical canonical output.
- Whitespace variations MUST NOT affect canonical output.

### TV-A2 -- Whitespace Stability

**Input Variant:** Same as TV-A1 but with arbitrary whitespace.

**Expected:** Canonical output identical to TV-A1 canonical form.

### TV-A3 -- Nested Object Ordering

**Input:**
```json
{
  "intent_id": "abc-124",
  "version": "1.0",
  "authority": "human",
  "action": "deploy",
  "parameters": {"b": 2, "a": 1},
  "governance_version": "v1.0"
}
```

**Expected Canonical Form:**
```
{"action":"deploy","authority":"human","governance_version":"v1.0","intent_id":"abc-124","parameters":{"a":1,"b":2},"version":"1.0"}
```

Nested objects MUST be lexicographically sorted.

### TV-A4 -- Replay Determinism

**Procedure:**
1. Submit identical Intent Contract twice.

**Verify:**
- Canonical hash identical.
- Receipt identical (excluding timestamp if outside canonical payload).
- Failure/success classification identical.

### TV-A5 -- Failure Precedence

**Input (Invalid Schema):** Missing required field: `authority`.

**Expected:**
- Deterministic failure code (e.g., `E_INPUT_MALFORMED`).
- Failure classification MUST NOT vary across runs.
- No partial success allowed.

---

## 5. Failure Taxonomy Vectors (Level A Required)

### TV-F1 -- Multiple Violations

**Input includes:**
- Missing required field
- Unsupported governance version

**Expected:**
- Deterministic primary failure code according to defined precedence.
- Precedence order MUST be documented and enforced.

### TV-F2 -- Governance Version Mismatch

**Input:**
```json
"governance_version": "v2.0"
```

If implementation pinned to v1.x:

**Expected:**
- Deterministic compatibility classification.
- Failure or conditional classification per rules.

---

## 6. Receipt Integrity Vectors (Level B Required)

### TV-B1 -- Receipt Structure Validation

Receipt MUST include:

- `intent_hash`
- `canonical_hash`
- `failure_code` or `success_code`
- `governance_version`
- `implementation_version`
- `timestamp`
- `schema_version`

Receipt MUST validate against published receipt schema.

### TV-B2 -- Signature Verification

For Level B+:

- Receipt MUST be cryptographically signed.
- Signature verification MUST succeed.
- Tampering with any field MUST invalidate signature.

### TV-B3 -- Receipt Replay Protection

Two identical inputs:

- MAY produce identical canonical hashes.
- MUST produce distinct receipt identifiers if replay detection is implemented.
- Replay flag MUST be deterministic if required by policy.

---

## 7. Environment Independence Vectors

### TV-E1 -- Cross-Machine Hash Stability

**Procedure:**
1. Execute TV-A1 on two separate machines.
2. Compare canonical hash.

**Expected:** Identical SHA-256 output.

### TV-E2 -- Locale Independence

Change locale settings.

**Expected:** No variation in canonical output or hash.

---

## 8. Governance Integration Vectors (Level C Required)

### TV-C1 -- MRCC Compatibility

Receipt MUST be embed-compatible with MRCC schema.

**Validation:** MRCC parser MUST accept evidence bundle.

### TV-C2 -- Cross-Repo Monotonicity

**Procedure:**
1. Issue receipt referencing governance v1.0.
2. Attempt downgrade to v0.9.

**Expected:**
- Rejection.
- Deterministic failure classification.

### TV-C3 -- Epoch Anchoring

If epoch system implemented:

- Receipt MUST include epoch reference.
- Epoch rollback attempt MUST fail deterministically.

---

## 9. Prohibited Behavior Vectors

### TV-P1 -- Hidden State Mutation

**Procedure:**
1. Execute identical input twice.
2. Internal mutable state changes between runs.

**Expected:**
- Detection of non-determinism.
- Conformance failure.

### TV-P2 -- Tool Invocation Attempt

If kernel attempts direct tool invocation:

**Expected:** Automatic conformance failure.

---

## 10. Required Public Artifacts

To claim compliance, implementation MUST publish:

1. Canonical test vectors (exact JSON)
2. Expected canonical outputs
3. Expected SHA-256 hashes
4. Expected receipts (signed if Level B+)
5. Failure code enumeration
6. Canonicalization rules

---

## 11. Determinism Certification Checklist

Implementation passes AAA-TVS-V1 if:

- [ ] All TV-A tests pass.
- [ ] All TV-F tests pass.
- [ ] All TV-B tests pass (Level B+).
- [ ] All TV-C tests pass (Level C).
- [ ] No prohibited behavior detected.

**Failure of any mandatory test invalidates conformance.**

---

## 12. Mapping to Existing EAL Conformance Fixtures

The existing `conformance/fixtures/` directory implements a superset of these vectors:

| AAA-TVS Vector | EAL Fixture(s) | Notes |
|----------------|-----------------|-------|
| TV-A1 (Canonicalization) | All T1-T10 | Every fixture includes `expected_report_sha256` |
| TV-A2 (Whitespace) | Implicit | Canonical JSON guarantees this |
| TV-A3 (Nested ordering) | T1, T3 | Action params include nested objects |
| TV-A4 (Replay) | `verify_conformance.py` repeat runs | Makefile target: `make verify-repeat` |
| TV-A5 (Failure precedence) | T2, T3, T5 | Invalid/Indeterminate fixtures |
| TV-F1 (Multiple violations) | Planned | Extend fixture set |
| TV-F2 (Governance mismatch) | C1-C9 | Compatibility fixtures |
| TV-B1 (Receipt structure) | R1-R5 | Receipt schema validation |
| TV-B2 (Signatures) | T2 (`E_SIG_INVALID`) | Signature failure detection |
| TV-C1 (MRCC) | Planned | Level C extension |
| TV-C2 (Monotonicity) | Planned | Level C extension |
| TV-C3 (Epoch anchoring) | T4, T6-T10 | Temporal validation fixtures |
| TV-P1 (Hidden state) | `verify_conformance.py` | Pure functions, no mutable state |
| TV-P2 (No tool invocation) | By design | Kernel has no tool dependencies |

---

## 13. Versioning Policy

**TVS v1.x:** Additional vectors only.

**v2.0:** May alter canonicalization invariants.

Changes require L7 authorization.
