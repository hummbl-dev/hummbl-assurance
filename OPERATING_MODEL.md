# Operating Model

## Scope

This repository is assurance-only. Release governance applies to deterministic
validation artifacts, schemas, fixtures, and CI receipts.

## Roles and Authority

- Release Operator:
  - A maintainer operating in `hummbl-dev` with admin rights on `main`
  - Responsible for running release gates, creating tags, and reviewing receipts
- Automation Actor:
  - GitHub Actions workflows (`conformance`, `release-artifacts`)
  - Responsible for deterministic verification and artifact publication

Only a Release Operator may cut official tags.

## Tag Policy

- Stable release tags:
  - `vMAJOR.MINOR.PATCH`
  - Cut from clean `main` only
  - Command: `make cut-release VERSION=vX.Y.Z`
- Pre-release tags:
  - `vMAJOR.MINOR.PATCH-rcN`
  - Used for governance drills and release-candidate validation
  - Manual flow:
    - `git tag -a vX.Y.Z-rcN -m "release vX.Y.Z-rcN"`
    - `git push origin vX.Y.Z-rcN`
    - `gh release edit vX.Y.Z-rcN --prerelease`

## Rollback Protocol

### Tag or Release Metadata Error

1. Disable consumption of the tag (announce freeze).
2. Delete release object:
   - `gh release delete <tag> --yes`
3. Delete remote and local tag:
   - `git push origin :refs/tags/<tag>`
   - `git tag -d <tag>`
4. Record incident and corrective action in PR/changelog.

### Workflow/Artifact Failure on Tag

1. Do not reuse failed artifact receipts as release evidence.
2. Patch workflow on `main` via PR.
3. Either:
   - cut next patch tag, or
   - regenerate and upload canonical receipts for impacted tag explicitly.
4. Attach failure run link + remediation run link to release notes.

### Code Regression After Release

1. Open hotfix branch from `main`.
2. Merge fix via PR with `verify` green.
3. Cut next patch release and publish fresh receipts.

## Release Receipt Checklist

A release is valid only when all checks below pass.

1. Local gate:
   - `make release-check` passes (`verify`, `verify-repeat`, `feature-gate`, `protection-audit`)
2. Tag created from clean `main` with annotated message.
3. Tag push triggers:
   - `conformance` workflow success
   - `release-artifacts` workflow success
4. Receipt gate command passes:
   - `make release-receipt TAG=<tag>`
5. Release assets present:
   - `verify_run1.txt`
   - `verify_run2.txt`
   - `verify_diff.txt` (expected `NO_DIFF` when clean)
   - `SHA256SUMS.txt`
   - `release_receipt.json`
6. Determinism evidence:
   - `verify_run1.txt` and `verify_run2.txt` hashes match
   - `verify_diff.txt` indicates no drift
7. Governance record updated:
   - changelog entry present
   - milestone/issues updated as appropriate
