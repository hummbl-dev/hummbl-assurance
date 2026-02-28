# Compatibility Rules (Compat Calculus v1)

Deterministic classification for `Compat(C_e, C_e+1)` based only on contract
artifact bytes.

## Normalized Diff Surface

Given `contract_a` and `contract_b`:

- `actions_added`: action ids in `b` but not `a`
- `actions_removed`: action ids in `a` but not `b`
- `constraints_added`: constraint keys in `b` but not `a`
- `constraints_removed`: constraint keys in `a` but not `b`
- `constraints_tightened`: shared numeric constraints where `b < a`
- `constraints_loosened`: shared numeric constraints where `b > a`
- `risk_increased`: shared risk keys where `b > a`
- `risk_decreased`: shared risk keys where `b < a`
- `semantics_changed`: explicit boolean flag in contract metadata

All arrays MUST be sorted lexicographically.

## Classification Rules

1. `INCOMPATIBLE` iff:
- `actions_removed` is non-empty, OR
- `semantics_changed` is `true`

2. `CONDITIONAL` iff not incompatible and at least one is non-empty:
- `constraints_added`
- `constraints_tightened`
- `risk_increased`

3. `BACKWARD_COMPATIBLE` otherwise.

## Reason Code Precedence

Reason codes MUST be emitted in this order when applicable:

1. `COMPAT_ACTION_REMOVED`
2. `COMPAT_SEMANTICS_CHANGED`
3. `COMPAT_CONSTRAINT_ADDED`
4. `COMPAT_CONSTRAINT_TIGHTENED`
5. `COMPAT_RISK_INCREASED`
6. `COMPAT_BACKWARD_ONLY_RELAX_OR_ADD`

`primary_reason_code` MUST equal the first emitted reason code.

## Fixture Matrix

- `C1`: add action only -> `BACKWARD_COMPATIBLE`
- `C2`: remove action -> `INCOMPATIBLE`
- `C3`: add constraint -> `CONDITIONAL`
- `C4`: tighten constraint -> `CONDITIONAL`
- `C5`: semantics change flag -> `INCOMPATIBLE`
- `C6`: risk increase only -> `CONDITIONAL`
- `C7`: constraint removal only -> `BACKWARD_COMPATIBLE`
- `C8`: action removal + semantics change (+ other diffs) -> `INCOMPATIBLE`
- `C9`: multi-reason conditional (constraint add + tighten + risk increase) -> `CONDITIONAL`
