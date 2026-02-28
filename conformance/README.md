# EAL Conformance Fixtures (v1 Minimum)

This directory contains synthetic fixtures aligned with `SPEC.md` Section 11.

Supporting artifacts:

- `FAILURE_CODES.md`: deterministic reason-code taxonomy and precedence
- `validation_report.schema.json`: canonical report schema (`eal.validation.report.v1`)
- `receipt.schema.json`: minimal deterministic receipt schema (`eal.receipt.v1`)
- `compat_report.schema.json`: compatibility report schema (`eal.compat.report.v1`)
- `release_receipt.schema.json`: release governance manifest schema (`eal.release.receipt.v1`)
- `experimental_feature_gate.json`: pinned experimental feature promotion decisions
- `compatibility_rules.md`: deterministic Compat calculus and reason precedence
- `CANONICALIZATION.md`: canonical JSON and hashing rules
- `ip_boundary.md`: allowed vs non-publishable artifact matrix
- `verify_conformance.py`: executable verifier (schema + precedence + hash)
  plus CLI parity (`./eal verify-receipt`, `./eal revalidate`, `./eal compat`)
- `verify_feature_gate.py`: release gate verifier for experimental feature defaults and promotion constraints

Each fixture file includes:

- `inputs`: contract/receipt artifacts required for evaluation
- `expected_report`: deterministic machine-readable output
- `expected_report_sha256`: SHA-256 of canonicalized `expected_report`

Fixture sets:

- `fixtures/`: validation fixtures (`T1-T5`)
- `fixtures_receipt/`: receipt determinism fixtures (`R1-R5`)
- `fixtures_temporal/`: epoch bridge and adversarial fixtures (`T6-T10`)
- `fixtures_compat/`: compatibility calculus fixtures (`C1-C9`)

Canonicalization rule:

- `jq -cS '.expected_report' <fixture.json> | tr -d '\n'`

Hash rule:

- `shasum -a 256 | awk '{print $1}'`

Quick integrity check:

```bash
for f in conformance/fixtures/*.json; do
  computed=$(jq -cS '.expected_report' "$f" | tr -d '\n' | shasum -a 256 | awk '{print $1}')
  declared=$(jq -r '.expected_report_sha256' "$f")
  if [ "$computed" = "$declared" ]; then
    echo "PASS $f"
  else
    echo "FAIL $f"
  fi
done
```

Full conformance check:

```bash
python3 conformance/verify_conformance.py
```

Experimental feature gate check:

```bash
python3 conformance/verify_feature_gate.py
```

The fixtures are intentionally synthetic and contain no production secrets,
runtime internals, or private governance canon content.
