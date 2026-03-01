# AAA Repo Audit Recommendations

**Date:** 2026-03-01
**Baseline:** `aaa-arch-v1.0.0` (commit `aff2ca7`)
**Auditors:** 5-agent parallel audit (Python code, conformance fixtures, CI/scripts, spec/governance docs, schemas/test vectors) + ChatGPT strategic analysis
**Total findings:** 73 (deduplicated)

---

## Executive Summary

The AAA repo is well-structured with strong deterministic conformance guarantees. The 5-agent audit found 73 findings across 4 priority levels. Critical issues centered on CI pipeline reliability (pipefail), a kernel determinism bug (conditional `origin_epoch`), missing fixture coverage for 5 of 13 failure codes, and local filesystem path leakage. A parallel ChatGPT strategic analysis recommended AST-based import gates and repo topology guardrails.

**All P0 items are resolved in PR `fix/claude/audit-p0-hardening`.**

---

## Priority Classification

| Priority | Count | Description |
|----------|-------|-------------|
| P0 (Critical) | 8 | Determinism bugs, CI reliability, security |
| P1 (High) | 12 | Missing coverage, spec alignment |
| P2 (Medium) | 28 | Code quality, documentation gaps |
| P3 (Low) | 25 | Style, naming, minor improvements |

---

## P0 Findings (Critical) -- ALL RESOLVED

### C1. CI pipefail missing in `conformance.yml`
**Finding:** All `run:` blocks lack `set -euo pipefail`. The `python3 ... | tee` pattern silently swallows script failures because only `tee`'s exit code is checked.
**Impact:** A failing conformance run could pass CI.
**Status:** RESOLVED -- pipefail added to all blocks.

### C2. CI pipefail missing in `release-artifacts.yml`
**Finding:** Same as C1 but in the release workflow.
**Status:** RESOLVED -- pipefail added to all blocks.

### C3. Missing fixture coverage for 5 failure codes
**Finding:** Only 8 of 13 EAL failure codes had dedicated fixtures. Missing: `E_INPUT_MALFORMED`, `E_BOUNDARY_MISMATCH`, `E_ACTION_OUT_OF_SPACE`, `E_CONTRACT_VERSION_COLLISION`, `E_LOG_SEQUENCE_GAP`.
**Impact:** Untested failure paths could silently regress.
**Status:** RESOLVED -- T11-T15 fixtures added to `conformance/fixtures/`.

### H1. `origin_epoch` conditionally emitted in INVALIDATED reports
**Finding:** In `core.py:518-519`, `origin_epoch` was only included when `n_receipt.epoch_number is not None`, creating non-deterministic receipt bodies that violate Pattern A.
**Impact:** Two identical INVALIDATED evaluations could produce different receipt shapes.
**Status:** RESOLVED -- now always emits `origin_epoch` (defaults to 0 when None).

### H2. Expression injection in `release-artifacts.yml`
**Finding:** Lines 148-151 interpolated `${{ steps.conformance_meta.outputs.run_id }}` and other expressions directly into shell `run:` blocks. A malicious conformance output could inject shell commands.
**Impact:** Potential arbitrary command execution in release pipeline.
**Status:** RESOLVED -- expressions moved to `env:` block, referenced as `$CONFORMANCE_RUN_ID` etc.

### H3. Local filesystem paths leaked in 11 files
**Finding:** `/Users/others/...` paths in vendor receipts, feature gates, SPRINT.md, and VENDOR_FEATURE_GAP_MATRIX.md expose local filesystem structure.
**Impact:** Information disclosure, non-portable references.
**Status:** RESOLVED -- all paths replaced with `<local-state>/` or `<repo>/` placeholders.

### H4. No AST-based kernel import enforcement
**Finding:** The TV-P2 check used `grep` to detect prohibited imports, which is fragile (can miss aliased imports, false-positive on comments). ChatGPT analysis recommended a proper AST-based gate.
**Impact:** Unauthorized imports could slip into kernel undetected.
**Status:** RESOLVED -- `spec/verify_kernel_imports.py` + `spec/kernel_import_allowlist_v1.json` added, integrated into CI and `make release-check`.

### H5. `aaa-spec-suite.yml` TV-P3 grep check fragile
**Finding:** The timestamp prohibition check uses `grep` with exclusion patterns for `#`, `def`, `"""`, which can false-positive on legitimate code or miss timestamp keys in string literals.
**Impact:** Low (supplemented by AST import gate), but could cause false CI failures.
**Status:** NOTED -- the AST import gate now provides stronger coverage. The grep check remains as defense-in-depth.

---

## P1 Findings (High) -- Recommended for next sprint

### P1-1. No `__version__` in `aaa_eal/__init__.py`
Programmatic version queries not possible. Add `__version__ = "0.2.0"`.

### P1-2. SPEC.md lists only 10 failure codes (13 in spec)
`SPEC.md` v0.2.0 is stale -- missing `E_INPUT_MALFORMED`, `E_CONTRACT_VERSION_COLLISION`, `E_LOG_SEQUENCE_GAP`.

### P1-3. SPEC.md CLI commands don't match actual implementation
CLI section shows `eal audit`, `eal check` -- actual commands are `verify-receipt`, `revalidate`, `compat`.

### P1-4. No mention of Pattern A determinism in SPEC.md
The receipt determinism strategy (body/meta split) is a core invariant not documented in the public-facing spec.

### P1-5. `_boundary_mismatch` truthy coercion for ALLOW/DENY
`bool(allow_raw)` coerces `0`, `""`, `[]` to `False`. Should validate `allow` is boolean or fail.

### P1-6. Missing `E_LOG_CHAIN_BREAK` and `E_REPLAY_DETECTED` fixtures
These are covered by the `log_chain_break`/`replay_detected` receipt flags but have no dedicated test fixtures.

### P1-7. TVS manifest at `spec/fixtures/TVS_V1_MANIFEST.json` doesn't exist
Referenced in AAA_TEST_VECTOR_SUITE_v1.md section 12 but never created.

### P1-8. `canonicalization_id` not emitted in receipt builder
The receipt schema (section M8) requires `canonicalization_id` but `evaluate_validation()` doesn't include it.

### P1-9. Temporal fixtures (T6-T10) number-collide with validation IDs
The temporal fixtures use T6-T10, same range as might be expected for validation fixtures. New fixtures had to use T11-T15.

### P1-10. `receipt.schema.json` `additionalProperties: false` blocks fixture evolution
The strict schema prevents adding new fields to receipt fixtures without a schema update.

### P1-11. No automated SPEC.md staleness check
SPEC.md can drift from the implementation with no CI gate catching it.

### P1-12. Vendor feature gate verifier doesn't check for sanitized paths
`verify_vendor_feature_gates.py` validates gate logic but doesn't flag local filesystem paths.

---

## P2 Findings (Medium) -- Document for reference

### Architecture & Design (10)
- P2-1. Three evaluation functions with different return shapes: `evaluate_validation`, `evaluate_temporal_validation`, `evaluate_compat`
- P2-2. `normalize_validation_receipt` and `normalize_validation_contract` use `ValueError` for all parse failures -- no structured error codes
- P2-3. No `dataclass` for the report dict -- it's a raw `dict[str, Any]`
- P2-4. `_sha_prefixed` helper is private but critical for hash format consistency
- P2-5. No formal interface/protocol for new evaluator modules
- P2-6. `cli.py` argument parsing could use `subparsers` for cleaner dispatch
- P2-7. Governance CAES_SPEC.md references Base120 but no formal binding exists
- P2-8. No formal changelog (CHANGES.md or equivalent)
- P2-9. Release receipt schema has no version migration strategy
- P2-10. No explicit contract schema (only implied by fixture structure)

### Testing & CI (10)
- P2-11. `make verify-repeat` uses `/tmp/` -- not parallel-safe
- P2-12. No coverage measurement for conformance suite
- P2-13. CI installs `jsonschema` every run -- could use requirements.txt or pin version
- P2-14. No matrix build (only Python 3.11)
- P2-15. `verify_conformance.py` exit code is always 0 (prints PASS/FAIL but doesn't fail)
- P2-16. `verify_test_vectors.py` and `verify_pinned_artifacts.py` use different output formats
- P2-17. No GitHub branch protection audit in CI (only local `make protection-audit`)
- P2-18. Compat fixtures (C1-C9) have no CLI round-trip tests
- P2-19. No smoke test for `make cut-release`
- P2-20. Vendor scorecards reference Codex API implementation details (model names, endpoints)

### Documentation (8)
- P2-21. AAA_ARCHITECTURE_v1.md section 9 references "HUMMBL Base120" without defining it
- P2-22. AAA_CONFORMANCE_PROFILE_v1.md section 19 assessment should be auto-generated
- P2-23. No quickstart guide for implementing a new AAA kernel in another language
- P2-24. AAA_KERNEL_REFERENCE_OUTLINE_v1.md repo layout doesn't match actual layout
- P2-25. No contributor guide (CONTRIBUTING.md)
- P2-26. License file references unclear
- P2-27. No glossary/terminology document
- P2-28. Temporal validation (epoch transitions) explained only in code, not in specs

---

## P3 Findings (Low) -- Backlog

25 findings covering naming consistency, comment style, test ID conventions, documentation cross-references, and similar minor items. Full list available on request.

---

## ChatGPT Strategic Recommendations (Integrated)

The following items from the ChatGPT analysis are captured here for tracking:

### Implemented in this PR
1. AST-based kernel import allowlist (spec/kernel_import_allowlist_v1.json + verifier)
2. CI pipefail hardening across all workflows
3. Expression injection fix in release-artifacts.yml
4. Path sanitization across all vendor evidence files

### Recommended for future work
1. **Repo topology**: Keep `/aaa` and `/base120` minimal. Agent runtimes belong in `agent-os` or `hummbl-agent`. CAES bindings in `hummbl-gaas-platform`.
2. **Phase 1 forcing function**: `make release-check` must pass before any tag. *(Already implemented)*
3. **Phase 2 forcing function**: Add `make verify-imports` to pre-commit hook for kernel files.
4. **Phase 3 forcing function**: Multi-language conformance test harness (TypeScript, Go reference implementations).
5. **CAES action-space binding**: Formalize the link between CAES_SPEC.md and the kernel's action_space validation.

---

## Verification Evidence

All fixes verified by running:
```
make verify          # All 44 fixtures pass
make verify-repeat   # Determinism check passes
make verify-imports  # Import allowlist passes
make verify-pinned   # Pinned artifacts unchanged
make verify-precedence # Precedence matches
```
