# Contributing

## Workflow

All changes to `main` must go through a pull request.

1. Create a branch using `type/agent/short-desc` (example: `chore/codex/governance-ops`).
2. Run local verification before push:
   - `make verify`
   - `make verify-repeat`
   - `make protection-audit` (requires repo admin token)
3. Push branch and open PR to `main`.
4. Wait for required check `verify` to pass.
5. Merge PR (squash merge preferred).

## Protection Policy (Main)

`main` policy is expected to be:

- required status check: `verify`
- required pull-request review: disabled
- conversation resolution: enabled
- enforce admins: enabled
- required linear history: enabled
- force push: disabled
- deletions: disabled

Use `make protection-audit` to verify drift.

## Commit Format

Use Conventional Commits:

- `feat:` new behavior or artifacts
- `fix:` bug fix
- `docs:` documentation changes
- `test:` test-only changes
- `ci:` CI/workflow changes
- `chore:` maintenance

## Scope Constraints

This repo is assurance-only. Do not add runtime orchestration or model routing.

## Release Hygiene

Update:

- `CHANGELOG.md`
- relevant schemas/fixtures
- deterministic hashes for changed expected outputs

See `RELEASE_POLICY.md` for tagging rules.
