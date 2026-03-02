# EAL Failure Code Taxonomy (v1)

This taxonomy defines deterministic reason codes for
`eal.validation.report.v1`.

## Code Set

| Code | Class | Meaning |
|---|---|---|
| `E_OK_VALID` | `VALID` | All required checks pass. |
| `E_INPUT_MALFORMED` | `INDETERMINATE` | Input JSON structure cannot be parsed or required top-level keys are missing. |
| `E_EVIDENCE_MISSING` | `INDETERMINATE` | Required evidence for a deterministic decision is missing. |
| `E_EPOCH_AMBIGUOUS` | `INDETERMINATE` | Receipt cannot be mapped to a unique authoritative contract/epoch. |
| `E_SIG_INVALID` | `INVALID` | Signature verification failed. |
| `E_HASH_MISMATCH` | `INVALID` | Receipt/evidence hash mismatch. |
| `E_CONTRACT_VERSION_COLLISION` | `INVALID` | Same contract version identifier resolves to different bytes. |
| `E_ACTION_OUT_OF_SPACE` | `INVALID` | Receipt includes action not present in `A(C_e)`. |
| `E_BOUNDARY_MISMATCH` | `INVALID` | Recomputed `B(C_e, action, params)` differs from receipt boundary outcome. |
| `E_LOG_CHAIN_BREAK` | `INVALID` | Supplied log hash-chain integrity fails. |
| `E_LOG_SEQUENCE_GAP` | `INVALID` | Supplied log sequence monotonicity/continuity fails. |
| `E_REPLAY_DETECTED` | `INVALID` | Duplicate receipt identifier detected in provided ledger context. |
| `E_EPOCH_INVALIDATED` | `INVALIDATED` | Execution valid under origin epoch is incompatible under target epoch. |

## Deterministic Mapping Rules

Evaluation order is fixed. The first matching condition determines the primary
reason code and class:

1. `E_INPUT_MALFORMED`
2. `E_CONTRACT_VERSION_COLLISION`
3. `E_SIG_INVALID`
4. `E_HASH_MISMATCH`
5. `E_EVIDENCE_MISSING`
6. `E_EPOCH_AMBIGUOUS`
7. `E_ACTION_OUT_OF_SPACE`
8. `E_BOUNDARY_MISMATCH`
9. `E_LOG_CHAIN_BREAK`
10. `E_LOG_SEQUENCE_GAP`
11. `E_REPLAY_DETECTED`
12. `E_EPOCH_INVALIDATED`
13. `E_OK_VALID`

If multiple conditions are true, `reason_codes` MUST be emitted in this exact
precedence order, with no duplicates.

Validation reports MUST include:

- `primary_reason_code`: the highest-priority matched code
- `reason_codes[0]`: MUST equal `primary_reason_code`

Class constraints:

- `VALID` MAY only use `E_OK_VALID`.
- `INDETERMINATE` MAY only use:
  `E_INPUT_MALFORMED`, `E_EVIDENCE_MISSING`, `E_EPOCH_AMBIGUOUS`.
- `INVALID` MAY only use:
  `E_SIG_INVALID`, `E_HASH_MISMATCH`, `E_CONTRACT_VERSION_COLLISION`,
  `E_ACTION_OUT_OF_SPACE`, `E_BOUNDARY_MISMATCH`, `E_LOG_CHAIN_BREAK`,
  `E_LOG_SEQUENCE_GAP`, `E_REPLAY_DETECTED`.
- `INVALIDATED` MAY only use `E_EPOCH_INVALIDATED`.

## Fixture Mapping

Fixture ID namespaces: validation (T1-T5, T11+), temporal (T6-T10), receipt (R1+), compat (C1+).

### Validation Fixtures (T1-T5, T11-T18)

| Fixture | Expected Class | Expected Code |
|---|---|---|
| `T1_VALID` | `VALID` | `E_OK_VALID` |
| `T2_INVALID_TAMPER` | `INVALID` | `E_SIG_INVALID` |
| `T3_INVALID_CLOSURE` | `INVALID` | `E_ACTION_OUT_OF_SPACE` |
| `T4_INVALIDATED_EPOCH` | `INVALIDATED` | `E_EPOCH_INVALIDATED` |
| `T5_INDETERMINATE_MISSING` | `INDETERMINATE` | `E_EVIDENCE_MISSING` |
| `T11_INVALID_MALFORMED` | `INDETERMINATE` | `E_INPUT_MALFORMED` |
| `T12_INVALID_BOUNDARY_MISMATCH` | `INVALID` | `E_BOUNDARY_MISMATCH` |
| `T13_INVALID_ACTION_SPACE` | `INVALID` | `E_ACTION_OUT_OF_SPACE` |
| `T14_INVALID_CONTRACT_VERSION_COLLISION` | `INVALID` | `E_CONTRACT_VERSION_COLLISION` |
| `T15_INVALID_LOG_SEQUENCE_GAP` | `INVALID` | `E_LOG_SEQUENCE_GAP` |
| `T16_INVALID_LOG_CHAIN_BREAK` | `INVALID` | `E_LOG_CHAIN_BREAK` |
| `T17_INVALID_REPLAY_DETECTED` | `INVALID` | `E_REPLAY_DETECTED` |
| `T18_INVALID_BOUNDARY_ALLOW_TYPE` | `INDETERMINATE` | `E_INPUT_MALFORMED` |
