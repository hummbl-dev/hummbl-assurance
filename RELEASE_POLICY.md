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

## Determinism Contract Changes

Any change to canonical expected outputs (hashes) is a release-significant event and must include:

- explicit changelog entry
- compatibility classification (`breaking` or `non-breaking`)
- regenerated hashes under canonicalization rules

## Merge Policy

All releases are cut from `main` after required checks pass.
