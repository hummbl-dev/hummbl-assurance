# EAL-AAA Assurance Spec (Normative Draft)

**Version:** 0.2.0  
**Date:** 2026-02-27  
**Status:** Draft for implementation planning

## 1. Scope

This specification defines a validation-only system for adjudicating autonomous execution claims against versioned governance contracts across governance epochs. It excludes runtime orchestration, model routing, live enforcement, and policy authoring workflows.

## 2. Terminology Alignment (Canonical)

This spec aligns with repository-defined terms:

- `CAES` means **Coordination and Execution Standard**, as defined in `PROJECTS/init-system/governance/CAES_SPEC.md`.
- `MRCC` means **Machine-Readable Compliance Claims**, as defined in `workspace/active/HUMMBL-Systems/MRCC/README.md`.

To prevent acronym drift, this document does not use `CAES` to mean action enumeration. Public docs use `Action Space` for permitted actions under a contract and reserve private action-taxonomy logic as internal implementation detail.

## 3. Architecture Relationship

`AAA` and `EAL` are complementary:

- `AAA` (Assured Agentic Architecture) is constructive: it executes intent under constraints and emits artifacts.
- `EAL` (Execution Assurance Layer) is adjudicative: it validates artifacts independently and classifies compliance status across time.

If execution and adjudication are controlled by a single mutable authority boundary, assurance loses independence.

## 4. Formal Problem Statement

Given a set of autonomous executions produced under versioned governance contracts, construct a deterministic assurance system that can:

1. verify conformance at the originating epoch,  
2. classify compatibility under later epochs, and  
3. produce evidence-bound claims suitable for audit.

Success criterion: independent evaluators with identical inputs produce identical classifications and reason codes.

## 5. Minimal Glossary

- `C_e`: immutable governance contract authoritative in epoch `e`
- `Epoch e`: contiguous interval with exactly one authoritative contract
- `A(C_e)`: finite set of permitted canonical action identifiers under `C_e`
- `B(C_e, action_id, params)`: deterministic boundary decision function represented by contract-visible rules
- `R`: immutable execution receipt
- `L`: optional coordination log input
- `V(R, C_e, L?)`: deterministic validation result
- `Compat(C_e, C_e+1)`: deterministic compatibility class for contract evolution
- `M(R, V)`: MRCC claim derived from validation output

## 6. Core Functions (v1 Surface)

1. `A(C_e) -> set[action_id]`
2. `B(C_e, action_id, params) -> {ALLOW, DENY}`
3. `V(R, C_e, L?) -> {VALID, INVALID, INVALIDATED, INDETERMINATE}`
4. `Compat(C_e, C_e+1) -> {BACKWARD_COMPATIBLE, CONDITIONAL, INCOMPATIBLE}`

No additional function is required for v1 conformance.

## 7. Trust Boundaries and Adversary Model

Trust boundaries:

- `TB1 Contract Publisher`: authorized source of contracts and epoch transitions
- `TB2 Receipt Signer`: authorized signer identity for receipts
- `TB3 Bus Writer`: producer of coordination logs (always treated as untrusted input)
- `TB4 Validator Operator`: executes validator, but cannot alter normative logic undetected

Adversary capabilities:

- `A1 Runtime misuse`: attempt actions outside `A(C_e)` or fake boundary outcomes
- `A2 Receipt forgery`: mutation, replay, substitution, or evidence omission
- `A3 Log contamination`: malformed appends, reordering, truncation, retroactive mutation
- `A4 Epoch manipulation`: ambiguous epoch boundaries or unauthorized contract transitions

## 8. Required Artifact Fields

For `R` to be potentially decidable, it must include at minimum:

- Receipt identifier (globally unique)
- Contract version identifier and contract content hash
- Action records and parameter evidence needed for boundary recomputation
- Evidence hash set for referenced artifacts
- Signature envelope and signer key metadata
- Execution timestamp in UTC

If required fields are missing, classification must resolve to `INDETERMINATE` unless direct tamper evidence yields `INVALID`.

## 9. Output Classes and Failure Codes

`V` must return exactly one class:

- `VALID`
- `INVALID`
- `INVALIDATED`
- `INDETERMINATE`

Each result must include deterministic reason codes. Minimum required codes:

- `E_OK_VALID`
- `E_SIG_INVALID`
- `E_HASH_MISMATCH`
- `E_EVIDENCE_MISSING`
- `E_ACTION_OUT_OF_SPACE`
- `E_BOUNDARY_MISMATCH`
- `E_EPOCH_AMBIGUOUS`
- `E_EPOCH_INVALIDATED`
- `E_LOG_CHAIN_BREAK`
- `E_REPLAY_DETECTED`

Normative taxonomy and precedence order are defined in:

- `conformance/FAILURE_CODES.md`

Validation reports MUST include `primary_reason_code` and MUST place that code
at `reason_codes[0]`.

## 10. Normative Requirements (MUST)

1. `Determinism`: `V` must produce identical class, reason code set, and canonical report hash for identical inputs.
2. `Evidence sufficiency`: if decision-critical evidence is missing, `V` must return `INDETERMINATE`.
3. `Contract immutability`: reused contract version identifiers with different bytes must be rejected.
4. `Epoch unambiguity`: ambiguous contract resolution for a receipt must return `INDETERMINATE`.
5. `Action closure`: evidenced actions not in `A(C_e)` must return `INVALID`.
6. `Boundary coherence`: if boundary evidence exists, recomputed `B` mismatch must return `INVALID`.
7. `Integrity verification`: signature/hash failures must return `INVALID`; missing verifier material must return `INDETERMINATE`.
8. `Compatibility determinism`: `Compat` must depend only on the two contract artifacts.
9. `Invalidation semantics`: valid in `C_e` but non-compliant in `C_e+1` must return `INVALIDATED`.
10. `Claim soundness`: `M(R, V)` must include contract id/hash, receipt hash, class, `primary_reason_code`, reason codes, and evidence pointers.
11. `Stable exits`: CLI must expose fixed exit codes for class and fatal processing failures.
12. `IP boundary`: public artifacts must exclude proprietary runtime logic, private policy internals, and operational secrets.

## 11. Conformance Suite (Minimum Fixtures)

Required golden fixtures:

- `T1 VALID`: all checks pass
- `T2 INVALID_TAMPER`: signature or content hash fails
- `T3 INVALID_CLOSURE`: action not in `A(C_e)` or boundary mismatch
- `T4 INVALIDATED_EPOCH`: valid in `C_e`, invalid under `C_e+1`
- `T5 INDETERMINATE_MISSING`: missing required evidence

Each fixture must assert deterministic class, deterministic reason codes, and deterministic canonical report hash.

Reference implementation fixtures for this draft live in:

- `conformance/fixtures/`

Additional deterministic fixture sets for next-phase lock-in:

- `conformance/fixtures_receipt/` (`R1-R4`) for receipt schema and evidence sufficiency checks
- `conformance/fixtures_temporal/` (`T6`) for explicit `INVALIDATED` epoch bridge behavior
- `conformance/fixtures_compat/` (`C1-C7`) for `Compat(C_e, C_e+1)` classification checks

## 12. IP-Safe Publishability Contract

Public-safe:

- Schemas
- Validator and compatibility classifier
- Reason-code taxonomy
- Synthetic fixtures and conformance harness
- Documentation and threat model

Private/non-publishable:

- Runtime policy logic
- Internal governance canon internals
- Production key material
- Operational evidence stores containing sensitive business context

## 13. v1 Delivery Shape

CLI-first commands:

- `eal verify <receipt>`
- `eal diff <contract_a> <contract_b>`
- `eal audit-log <log>`
- `eal replay <receipt>`
- `eal claim <receipt>`

No UI and no cloud runtime are required for v1.

## 14. Open Questions for v0.3

1. Which contract deltas map to `BACKWARD_COMPATIBLE` vs `CONDITIONAL` deterministically?
2. Should reason codes be local to this suite or governed as a shared registry?
3. Is hash-chain sufficient for v1 logs, or should Merkle anchoring be required?
4. What revocation/supersession policy governs previously issued MRCC claims?
