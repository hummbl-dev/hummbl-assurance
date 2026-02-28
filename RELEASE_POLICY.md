# Release Policy

## Versioning

Use semantic version tags: `vMAJOR.MINOR.PATCH`.

- `MAJOR`: breaking schema, fixture, or determinism contract change
- `MINOR`: backward-compatible feature additions (new fixture families, new non-breaking schema fields)
- `PATCH`: documentation, CI, or non-behavioral fixes

## Release Checklist

1. `make verify`
2. `make verify-repeat`
3. `make feature-gate`
4. `make vendor-scan` (recommended evidence refresh)
5. `make protection-audit`
6. Confirm `CHANGELOG.md` includes release notes
7. Create annotated tag

```bash
make cut-release VERSION=vX.Y.Z
```

`cut-release` now blocks until release governance receipts pass for the tag:

- `conformance` workflow succeeded on the tag push
- `release-artifacts` workflow succeeded on the tag push
- required release assets are present

Manual receipt check:

```bash
make release-receipt TAG=vX.Y.Z
```

## Tag Artifact Automation

Pushing a `v*` tag triggers `.github/workflows/release-artifacts.yml` which:

1. reruns `conformance/verify_conformance.py` twice
2. fails closed if output drift is detected
3. uploads verifier artifacts (`verify_run1.txt`, `verify_run2.txt`, `verify_diff.txt`, `SHA256SUMS.txt`) to the matching GitHub Release
4. publishes `release_receipt.json` validated against `conformance/release_receipt.schema.json`

## Determinism Contract Changes

Any change to canonical expected outputs (hashes) is a release-significant event and must include:

- explicit changelog entry
- compatibility classification (`breaking` or `non-breaking`)
- regenerated hashes under canonicalization rules

## Experimental Feature Gate

Releases are blocked if the pinned multi-vendor experimental feature gate artifact fails validation.

```bash
make feature-gate
```

Optional operator-only live environment parity check:

```bash
make feature-gate-live
```

Optional operator sync to hydrate gate metadata from local vendor probes:

```bash
make vendor-scan-sync
```

`feature-gate` validates:

- required vendor/surface registry coverage is complete
- each evaluated vendor surface has deterministic gate evidence
- no candidate is promoted unless all non-manual gates pass and confounds are absent
- gate artifact freshness is within policy bounds
- default experimental flags and candidate slugs are inventory-consistent

## Merge Policy

All releases are cut from `main` after required checks pass.
