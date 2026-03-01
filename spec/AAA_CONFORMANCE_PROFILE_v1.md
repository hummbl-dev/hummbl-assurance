# AAA Conformance Profile v1

**Document ID:** AAA-CONF-V1
**Version:** 1.0.0
**Status:** Canonical Conformance Profile for AAA v1
**Depends On:** AAA-ARCH-V1 (v1.0.0)
**Last Updated:** 2026-03-01

---

## 1. Purpose

This document defines the formal conformance requirements for claiming compliance with:

> Assured Agentic Architecture (AAA) v1

It specifies:

- Mandatory requirements
- Optional extensions
- Prohibited behaviors
- Evidence requirements
- Certification levels
- Failure classification
- Test obligations

This document is **normative**.

---

## 2. Conformance Scope

AAA v1 conformance applies only to **L3.5** (AAA Deterministic Boundary) and its integration constraints with adjacent layers (L3 and L4).

No implementation may claim full-stack compliance unless explicitly declared.

---

## 3. Conformance Levels

### 3.1 Level A -- Core Kernel Conformance

Minimum viable AAA compliance.

**MUST:**
- Deterministic canonical serialization.
- Cryptographic hashing of execution artifact.
- Explicit failure code taxonomy.
- Fail-closed enforcement behavior.
- Receipt emission for all enforcement decisions.
- Schema validation for Intent Contract.
- No hidden mutable state.

**MUST NOT:**
- Perform orchestration.
- Perform reasoning.
- Modify governance artifacts.
- Invoke tools directly.
- Maintain implicit authority.

### 3.2 Level B -- Evidence-Hardened Conformance

Includes Level A plus:

**MUST:**
- Cryptographically signed receipts.
- Version pinning of governance dependencies.
- Hash-addressable evidence store.
- Deterministic receipt schema.
- Replay-detectable receipt identifiers.
- Canonical JSON (or equivalent) normalization rules publicly specified.

### 3.3 Level C -- Governance-Integrated Conformance

Includes Level B plus:

**MUST:**
- MRCC issuance compatibility.
- CAES action-space declaration binding.
- Cross-repo monotonicity checks.
- Epoch anchoring support.
- Governance version compatibility classification.
- Explicit non-claims in compliance receipts.

---

## 4. Intent Contract Requirements

All compliant implementations MUST define:

- Deterministic schema
- Authority declaration field
- Version identifier
- Hashable canonical form
- Explicit execution scope

Intent Contracts MUST be:

- Serializable
- Canonicalizable
- Reproducible byte-for-byte

**Failure to reproduce identical hash invalidates compliance.**

---

## 5. Canonicalization Requirements

The implementation MUST:

1. Define ordering rules (lexicographic key sorting).
2. Define whitespace normalization (compact/minified JSON).
3. Define encoding (UTF-8 required).
4. Define numeric normalization rules.
5. Exclude trailing newline variance.
6. Specify deterministic hash algorithm.

**Required:**
- SHA-256 or stronger.
- Hash over canonical byte stream only.

Reference implementation: `aaa_eal.core.canonical_json_bytes()`.

---

## 6. Failure Taxonomy Requirements

A compliant implementation MUST:

1. Define enumerated failure codes.
2. Enforce precedence ordering.
3. Guarantee deterministic failure classification.
4. Emit failure receipts identical across runs.

Failure codes MUST NOT depend on:

- System time (unless explicitly included in canonical data).
- Non-deterministic randomness.
- External service availability (unless declared).

Reference taxonomy: `conformance/FAILURE_CODES.md` (13 codes, 4 output classes).

---

## 7. Receipt Requirements

Every enforcement decision MUST emit a receipt containing:

- Intent Contract hash
- Canonical artifact hash
- Failure code (or success code)
- Governance version pin
- Timestamp (RFC3339)
- Implementation version
- Deterministic receipt schema version

For Level B+:
- Cryptographic signature required.

Receipts MUST be reproducible and verifiable.

---

## 8. Determinism Test Requirements

An implementation MUST pass:

### 8.1 Replay Test
Identical Intent Contract -> identical canonical artifact -> identical hash -> identical receipt.

### 8.2 Order Stability Test
Field reordering -> identical canonical output.

### 8.3 Whitespace Stability Test
Whitespace mutation -> identical canonical output.

### 8.4 Failure Precedence Test
Multiple violations -> identical primary failure classification.

### 8.5 Environment Isolation Test
Different machines -> identical hash.

**Failure of any test invalidates conformance.**

See **AAA-TVS-V1** for the full test vector suite.

---

## 9. Governance Pinning Requirements

For Level B+:

Implementation MUST:

1. Pin governance version.
2. Reject incompatible governance major versions.
3. Emit compatibility classification:
   - `BACKWARD_COMPATIBLE`
   - `CONDITIONAL`
   - `INCOMPATIBLE`
4. Compatibility logic MUST be deterministic.

Reference implementation: `aaa_eal.core.evaluate_compat()`.

---

## 10. Prohibited Behaviors

An AAA v1 implementation MUST NOT:

1. Execute tools.
2. Make policy decisions.
3. Modify governance.
4. Perform dynamic orchestration.
5. Embed adaptive reasoning.
6. Mutate Intent Contracts.
7. Suppress receipt emission.
8. Emit unverifiable claims.

---

## 11. Evidence Model

A compliant system MUST provide:

- Public schema definitions
- Deterministic canonicalization rules
- Hash algorithm specification
- Failure code documentation
- Receipt schema documentation

For Level C:
- MRCC-compatible evidence bundle format

---

## 12. Certification Criteria

To claim AAA v1 compliance, an implementation MUST:

1. Declare conformance level.
2. Publish deterministic spec.
3. Provide reproducible test vectors.
4. Provide canonical sample receipts.
5. Provide hash verification instructions.
6. Provide versioned release tag.

**Failure to provide verifiable artifacts invalidates certification.**

---

## 13. Compatibility Matrix

| Claim | Allowed |
|-------|---------|
| "AAA-Compatible" | Only if Level A |
| "AAA Evidence-Hardened" | Only if Level B |
| "AAA Governance-Integrated" | Only if Level C |
| "AAA Orchestrator" | **PROHIBITED** |
| "AAA Reasoning Engine" | **PROHIBITED** |

---

## 14. Minimal Certifiable Kernel Definition

The minimal certifiable AAA v1 kernel is:

1. Deterministic Intent validator
2. Canonicalizer
3. SHA-256 hash generator
4. Failure taxonomy
5. Receipt emitter
6. Fail-closed gate

Anything beyond this is extension, not core.

---

## 15. Versioning Policy

**Conformance Profile v1.x:**
- Clarifications only.
- No invariant mutation.

**v2.0:**
- May modify required invariants.
- Requires L7 authorization.

---

## 16. Security Model

AAA v1 conformance requires:

- Fail-closed execution
- No silent acceptance
- No implicit state
- No dynamic authority escalation
- No hidden entropy

---

## 17. Conformance Assertion Template

An implementation claiming compliance MUST publish:

```
Implementation Name:
Version:
AAA Conformance Level: (A / B / C)
Canonicalization Algorithm:
Hash Algorithm:
Receipt Schema Version:
Governance Version Pin:
Test Vector Location:
Signature Method (if Level B+):
```

---

## 18. Invalid Claims

The following automatically invalidate compliance:

- Undocumented canonicalization
- Non-deterministic receipts
- Absence of failure taxonomy
- Missing governance pin (Level B+)
- Hidden state mutation
- Tool execution capability in kernel

---

## 19. EAL-AAA v0.2.0 Conformance Assessment

The current `aaa_eal` implementation (v0.2.0) satisfies:

| Requirement | Level A | Level B | Level C |
|-------------|---------|---------|---------|
| Deterministic canonicalization | Yes | Yes | Yes |
| Cryptographic hashing (SHA-256) | Yes | Yes | Yes |
| Failure taxonomy (13 codes) | Yes | Yes | Yes |
| Fail-closed behavior | Yes | Yes | Yes |
| Receipt emission | Yes | Yes | Yes |
| Schema validation | Yes | Yes | Yes |
| No hidden mutable state | Yes | Yes | Yes |
| Signed receipts | -- | Partial | Partial |
| Governance version pinning | -- | Yes | Yes |
| Hash-addressable evidence store | -- | Yes | Yes |
| MRCC issuance | -- | -- | Not yet |
| CAES binding | -- | -- | Partial |
| Cross-repo monotonicity | -- | -- | Not yet |
| Epoch anchoring | -- | -- | Yes |

**Current classification: Level A compliant, Level B partial, Level C in progress.**
