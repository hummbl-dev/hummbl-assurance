# Changelog

All notable changes to this repository are documented here.

## 2026-02-28

### Added

- Deterministic CLI implementation:
  - `./eal verify-receipt --contract ... --receipt ...`
  - `./eal revalidate --contract-origin ... --contract-target ... --receipt ...`
  - `./eal compat --contract-a ... --contract-b ...`
- Shared core evaluator module:
  - `aaa_eal/core.py`
  - `aaa_eal/cli.py`
  - `aaa_eal/__main__.py`

### Changed

- `conformance/verify_conformance.py` now validates CLI parity against fixture
  expected reports and expected exit codes, including temporal `revalidate`.
- Added temporal validation fixture coverage:
  - `T7_VALID_BY_EPOCH` (valid cross-epoch carry-forward)
- Added multi-reason precedence fixtures for validation and compatibility:
  - `R5_RECEIPT_MULTI_REASON_INVALID`
  - `C8_MULTI_REASON_INCOMPATIBLE`
  - `C9_MULTI_REASON_CONDITIONAL`
- Added tag-triggered release artifact workflow:
  - `.github/workflows/release-artifacts.yml`
  - reruns conformance on `v*` tags and uploads verifier artifacts to GitHub Releases
- Fixed release artifact upload edge case for empty diff files by writing `NO_DIFF`
  sentinel content before upload.
- Added governance operating model:
  - `OPERATING_MODEL.md` (tag authority, rollback protocol, release receipt checklist)
- Added release receipt gate tooling:
  - `scripts/verify_release_receipt.sh`
  - `make release-receipt TAG=vX.Y.Z`
  - `cut-release` now enforces successful tag workflows and required assets
- Fixed release-receipt gate race by waiting for release object creation after
  tag push before evaluating workflows/assets.
- Added deterministic release receipt manifest publication:
  - `conformance/release_receipt.schema.json`
  - `release_receipt.json` emitted by tag workflow and uploaded to release assets
- Fixed release manifest workflow parsing bug in conformance-run metadata step.

## 2026-02-27

### Added

- Initial repository bootstrap with:
  - normative assurance spec (`SPEC.md`)
  - deterministic validation report schema
  - failure-code taxonomy and precedence
  - canonicalization rules
  - conformance fixtures `T1-T5`
  - verifier harness
  - CI workflow for conformance checks

- Receipt evidence contract hardening:
  - `receipt.schema.json`
  - receipt fixtures `R1-R4`

- Compatibility calculus hardening:
  - `compatibility_rules.md`
  - `compat_report.schema.json`
  - compat fixtures `C1-C7`

- Temporal invalidation bridge proof:
  - fixture `T6_INVALIDATED_BY_EPOCH`

- IP publication boundary:
  - `conformance/ip_boundary.md`

### Changed

- Verifier upgraded from static fixture hash checks to deterministic derived-evaluation checks for validation, receipt, temporal, and compat fixture suites.
- CI upgraded to include two-pass determinism check with artifact upload (`verify_run1`, `verify_run2`, `verify_diff`).

### Governance

- `main` branch protection enabled:
  - required status check: `verify`
  - 1 approving review required
  - conversation resolution required
  - admin enforcement enabled
  - force-push and branch deletion blocked

### Added

- Governance operator artifacts:
  - `CONTRIBUTING.md`
  - `RELEASE_POLICY.md`
  - `scripts/audit_branch_protection.sh`
- Make target `protection-audit` for policy drift checks.
- Release/ops automation:
  - `scripts/cut_release.sh`
  - make targets: `release-check`, `cut-release`
  - scheduled GitHub workflow: `.github/workflows/protection-audit.yml`
