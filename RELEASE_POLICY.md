# Release Policy

## Versioning

Use semantic version tags: `vMAJOR.MINOR.PATCH`.

- `MAJOR`: breaking schema, fixture, or determinism contract change
- `MINOR`: backward-compatible feature additions (new fixture families, new non-breaking schema fields)
- `PATCH`: documentation, CI, or non-behavioral fixes

## Release Checklist

1. `make verify`
2. `make verify-repeat`
3. `make protection-audit`
4. Confirm `CHANGELOG.md` includes release notes
5. Create annotated tag

```bash
make cut-release VERSION=vX.Y.Z
```

## Tag Artifact Automation

Pushing a `v*` tag triggers `.github/workflows/release-artifacts.yml` which:

1. reruns `conformance/verify_conformance.py` twice
2. fails closed if output drift is detected
3. uploads verifier artifacts (`verify_run1.txt`, `verify_run2.txt`, `verify_diff.txt`, `SHA256SUMS.txt`) to the matching GitHub Release

## Determinism Contract Changes

Any change to canonical expected outputs (hashes) is a release-significant event and must include:

- explicit changelog entry
- compatibility classification (`breaking` or `non-breaking`)
- regenerated hashes under canonicalization rules

## Merge Policy

All releases are cut from `main` after required checks pass.
