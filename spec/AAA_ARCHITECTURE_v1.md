# AAA Reference Architecture v1

**Document ID:** AAA-ARCH-V1
**Version:** 1.0.0
**Status:** Canonical (Proposed v1 Baseline)
**Applies To:** Assured Agentic Architecture (AAA) Kernel and Surrounding Stratified System
**Last Updated:** 2026-03-01

---

## 1. Purpose

This document defines the formal 10-layer AAA Reference Architecture v1.

It specifies:

- Layer boundaries
- Invariants
- Authority gradients
- Failure domains
- Explicit non-goals
- Cross-layer constraints

This document is **normative**.

---

## 2. Architectural Principles

The AAA Reference Architecture v1 is built on the following principles:

1. Deterministic enforcement boundary
2. Explicit authority partitioning
3. Cryptographic auditability
4. Version-locked governance
5. Explicit non-goals per layer
6. Monotonic epistemic evolution
7. Thin kernel philosophy (L3.5)
8. No implicit execution authority
9. No hidden state
10. Separation of execution, intent, and governance

---

## 3. Layered Stratification

### 3.1 Canonical Stack (Bottom to Top)

```
[L7]   Strategic Evolution
[L6]   Epistemic Stability
[L5]   Canonical Knowledge Field (SMMF)
[L4]   Governance & Assurance
[L3.5] AAA Deterministic Boundary
[L3]   Intent & Delegation
[L2]   Invocation & Transport
[L1]   Tool Surface
[L0]   Infrastructure
[L-1]  Physical Substrate
```

### 3.2 Layer Index

| ID   | Name                          | Class           |
|------|-------------------------------|-----------------|
| L-1  | Physical Substrate            | Causal          |
| L0   | Infrastructure Substrate      | Runtime         |
| L1   | Tool Surface                  | Capability      |
| L2   | Invocation & Transport        | Execution       |
| L3   | Intent & Delegation           | Semantic        |
| L3.5 | AAA Deterministic Boundary    | Enforcement     |
| L4   | Governance & Assurance        | Constraint      |
| L5   | Canonical Knowledge Field     | Epistemic       |
| L6   | Epistemic Stability           | Integrity       |
| L7   | Strategic Evolution           | Meta-Governance |

---

## 4. Layer Specifications

### L-1 -- Physical Substrate

**Scope:**
- Human cognition
- Hardware (silicon, semiconductor supply chain)
- Power systems
- RF spectrum

**Invariants:**
- No software semantics
- No policy logic
- No execution contract enforcement

**Failure Domain:**
- Hardware compromise
- Power failure
- Physical tampering

**Non-Goals:**
- Not directly governed by AAA

---

### L0 -- Infrastructure Substrate

**Scope:**
- Kernel
- Virtualization
- Filesystems
- Networking

**Invariants:**
- Resource isolation
- Deterministic clock source
- No semantic awareness of intent

**Failure Domain:**
- Kernel panic
- Resource exhaustion
- Network partition

---

### L1 -- Tool Surface Layer

**Scope:**
- APIs (OpenAI, Anthropic, xAI, etc.)
- MCP endpoints
- Databases
- CLI tools
- External services

**Invariants:**
- Parameterized callable interface
- No intrinsic policy enforcement
- No authority model

**Failure Domain:**
- Authentication errors
- API drift
- Schema mismatch

---

### L2 -- Invocation & Transport Layer

**Scope:**
- RPC mechanisms
- Message buses (including TSV coordination bus)
- Deterministic CLI execution
- Protocol routing

**Invariants:**
- Invocation traceability
- Idempotency where declared
- Explicit call boundaries

**Failure Domain:**
- Message loss
- Replay attacks
- Ordering drift

---

### L3 -- Intent & Delegation Layer

**Scope:**
- Human Intent (HITL)
- Spec-driven workflows
- Poly-AI orchestration
- Role partitioning
- Run specifications

**Invariants:**
- Intent must be serializable
- Delegation must be explicit
- Authority must be bounded
- No implicit tool execution

**Failure Domain:**
- Intent drift
- Over-delegation
- Role ambiguity

**Explicit Non-Goals:**
- No execution enforcement
- No cryptographic assurance

---

### L3.5 -- AAA Deterministic Execution Boundary (Kernel)

This is the core AAA layer. It is implemented by the `aaa_eal` package.

**Scope:**
- Intent Contract validation
- Canonical serialization (`canonical_json_bytes`)
- Cryptographic hashing (`sha256_hex`)
- Failure code precedence (`EAL_PRECEDENCE`)
- Receipt emission (validation reports)
- Merge/exit gating (CLI exit codes)
- EAL assurance enforcement

**Invariants:**
- Deterministic canonicalization (sorted keys, compact JSON, UTF-8, no trailing newline)
- Hash-stable execution artifacts
- Explicit failure taxonomy (13 codes, deterministic precedence)
- No hidden mutable state
- No business logic

**Authority:**
- May block execution (exit code != 0)
- May emit receipts (validation/compatibility reports)
- May fail closed (`INDETERMINATE` on malformed input)

**Failure Domain:**
- Contract violation (`E_CONTRACT_VERSION_COLLISION`)
- Evidence insufficiency (`E_EVIDENCE_MISSING`)
- Hash mismatch (`E_HASH_MISMATCH`)
- Schema non-compliance (`E_INPUT_MALFORMED`)

**Explicit Non-Goals:**
- No orchestration
- No reasoning
- No tool invocation logic
- No governance modification authority

**AAA is a thin enforcement kernel.**

---

### L4 -- Governance & Assurance Layer

**Scope:**
- HUMMBL Base120 (frozen v1)
- MRCC lifecycle automaton
- CAES Action Enumeration (as defined in `governance/CAES_SPEC.md`)
- Singularity Monitoring Protocol
- Epoch governance
- Cross-repo monotonicity

**Invariants:**
- Version pinning required
- Claims must be evidence-backed
- Non-claims must be explicit
- Cryptographic signatures required
- Governance must be monotonic

**Failure Domain:**
- Governance drift
- Unauthorized claim issuance
- Epoch rollback attempt

**Non-Goals:**
- No runtime execution authority

---

### L5 -- Canonical Knowledge Field (SMMF)

**Scope:**
- Stratified Mental Model Field
- Layer x Time x Agency axes
- Cross-domain model taxonomy

**Invariants:**
- Model position must be declared
- Historical and predictive roles must be distinct
- Constraint stack must be preserved

**Failure Domain:**
- Taxonomic ambiguity
- Model collapse
- Category drift

---

### L6 -- Epistemic Stability Layer

**Scope:**
- Epistemic drift detection
- Assurance thresholds
- Cross-system consistency
- Singularity risk monitoring

**Invariants:**
- Knowledge claims must be monotonic
- Drift must be detectable
- Assurance thresholds explicitly declared

**Failure Domain:**
- Silent epistemic mutation
- Undetected divergence
- Assurance inflation

---

### L7 -- Strategic Evolution Layer

**Scope:**
- Major version authorization (v1.x vs v2)
- Canonical boundary shifts
- Governance amendments
- Architectural refactor authority

**Invariants:**
- Formal change proposal required
- Compatibility classification required
- Non-claims must be restated
- Governance state must remain auditable

**Failure Domain:**
- Unauthorized structural mutation
- Boundary ambiguity
- Governance capture

---

## 5. Authority Gradient

Execution power increases downward. Governance authority increases upward.

| Layer | Authority Type      |
|-------|---------------------|
| L7    | Structural authority |
| L6    | Epistemic authority  |
| L5    | Taxonomic authority  |
| L4    | Governance authority |
| L3.5  | Enforcement authority |
| L3    | Intent authority     |
| L2    | Invocation authority |
| L1    | Capability exposure  |
| L0    | Resource control     |
| L-1   | Physical causality   |

**No layer may exceed its authority classification.**

Key authority relationships:
- L3 generates intent.
- L3.5 constrains execution.
- L4 constrains legitimacy.
- L6 constrains epistemic validity.
- L7 constrains change itself.

---

## 6. Cross-Layer Constraints

1. L3 intent must pass L3.5 validation before execution.
2. L3.5 must emit cryptographic receipts for all enforcement decisions.
3. L4 governance rules must not mutate L3.5 enforcement determinism.
4. L6 must monitor L4 claims for drift.
5. L7 may only modify architecture through formal version transitions.

---

## 7. Non-Goals of AAA v1

The following are explicitly out of scope:

- Autonomous reasoning systems
- Tool orchestration frameworks
- UI/UX layers
- Business logic execution
- Domain-specific intelligence

**AAA v1 is a deterministic enforcement boundary within a stratified system.**

---

## 8. Conformance Requirements

An implementation claiming AAA v1 compliance MUST:

1. Implement L3.5 invariants exactly.
2. Provide deterministic canonicalization.
3. Emit cryptographically verifiable receipts.
4. Enforce explicit failure taxonomy.
5. Pin governance versions.
6. Declare non-goals explicitly.

Failure to meet any of the above invalidates compliance.

See **AAA-CONF-V1** for detailed conformance levels.

---

## 9. Versioning Policy

- **v1.x:** Backward compatible clarifications only.
- **v2.0:** Structural layer mutation permitted.
- All changes require L7 authorization.

---

## 10. Security Posture

AAA v1 is:

- Fail-closed
- Hash-addressable
- Evidence-emitting
- Version-locked
- Deterministic

**No silent mutation permitted.**

---

## 11. Design Properties Summary

1. Thin enforcement kernel
2. Cryptographic auditability
3. Deterministic execution boundary
4. Layer isolation
5. Explicit non-goals at every layer
6. No implicit authority
7. Version-locked governance
8. Epistemic drift awareness
9. Strategic mutation gating
10. Field-level taxonomy integration

---

## 12. Companion Documents

| Document ID | Title | Status |
|-------------|-------|--------|
| AAA-CONF-V1 | [Conformance Profile](AAA_CONFORMANCE_PROFILE_v1.md) | v1.0.0 |
| AAA-TVS-V1  | [Test Vector Suite](AAA_TEST_VECTOR_SUITE_v1.md) | v1.0.0 |
| AAA-KRO-V1  | [Kernel Reference Outline](AAA_KERNEL_REFERENCE_OUTLINE_v1.md) | v1.0.0 |
