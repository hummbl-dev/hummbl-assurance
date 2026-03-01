# Sprint Status - 2026-02-28

**Project:** EAL-AAA v0.2.0 (Spec Draft)
**Sprint focus:** Multi-vendor feature evaluation, governance hardening
**Updated by:** codex (coordinator)

## Shipped Today

| PR | Description | Status |
|----|-------------|--------|
| #29 | feat: evaluate anthropic claude code experimental feature gates (phase 1) | MERGED |
| #28 | feat: add anthropic feature inventory snapshot | MERGED |
| #27 | ci: publish vendor evidence artifacts in release pipeline | MERGED |
| #26 | feat: add vendor surface evidence collection workflow | MERGED |
| #25 | feat: harden multi-vendor feature gate validation | MERGED |

### Phase 1 Feature Evaluation -- COMPLETE
Evaluated 4 Anthropic Claude Code CLI features against promotion policy (min 20% speedup + manual gates):

| Feature | Decision | Speedup | Rationale |
|---------|----------|---------|-----------|
| `task_list_id` | HOLD | 0.15 (15%) | Below 0.2 threshold, manual gates required |
| `precompact_hooks` | HOLD | 0.0 | Safety feature, no speed delta |
| `terminal_progress_bar` | HOLD | 0.0 | UI-only, security/operability gates passed |
| `always_thinking` | NO-GO | -0.35 | Confounded with adaptive thinking |

**Result:** Zero features promoted to default-on. Stable profile remains authoritative. 8 evidence receipts generated.

### Governance Tooling -- COMPLETE
- Vendor surface evidence collection workflow
- Release receipt gate automation (tag-triggered)
- Deterministic CLI: `eal verify-receipt`, `eal revalidate`, `eal compat`
- Multi-vendor feature gate hardening + coherence checks

## In Progress

### MVS-2026-03-01A -- Multi-vendor evidence closure

Control packet: `/Users/others/_state/coordination/MULTI_VENDOR_SPRINT_2026-03-01A.md`

Current execution lanes:

1. Anthropic probe-vs-curated normalization
2. Gemini evidence lane (`experimental-acp`) from scanned baseline to evaluated classification
3. OpenRouter capability inventory curation
4. Matrix/sprint synchronization with repo-local evidence links

## Next Up

### P0 -- Immediate

1. **Vendor evidence closure (Gemini/OpenRouter/Ollama)**
   - Google Gemini CLI (v0.29.7): scan + inventory receipt captured; pilot scorecard still pending
   - OpenRouter API: scan + inventory receipt captured; curated capability inventory still empty
   - Ollama Local (v0.15.4): empty inventory, daemon_unreachable on this machine
   - Action: convert inventory receipts into scorecard-ready evaluation artifacts and matrix decisions
   - Note: Ollama blocked until Mac Mini (HUM-9) is provisioned

### P1 -- This Week

2. **Phase 2 Claude Code feature evaluation**
   - 7 features queued: enable_telemetry, enable_prompt_suggestion, fast_mode_per_session_opt_in, etc.
   - `always_thinking` may be re-evaluated with cleaner isolation
   - Requires: phase 1 data clean-up first

3. **Manual security review + operability drills**
   - All phase 1 candidates flagged `manual-review-required` (security_gate)
   - All flagged `manual-rollback-drill-required` (operability_gate)
   - Exception: `terminal_progress_bar` has both gates passed
   - Action: schedule review session with Reuben

4. **Codex confounded data reconciliation**
   - `prevent_idle_sleep`: 1 valid scorecard (3 excluded confounds), inconclusive
   - `multi_agent-prevent_idle_sleep`: -0.21 speedup, no-go
   - Action: re-run with cleaner isolation between sleep cycles

### P2 -- v0.3 Spec Cycle

5. **SPEC.md v0.3 open questions**
   - Which contract deltas map to BACKWARD_COMPATIBLE vs CONDITIONAL?
   - Reason codes: local to AAA or shared registry?
   - Hash-chain sufficient for v1 logs, or require Merkle anchoring?
   - Revocation/supersession policy for previously issued MRCC claims?

6. **Release governance hardening**
   - Artifact immutability guarantees for long-term audits
   - Cross-vendor receipt correlation
   - Temporal invalidation proof automation

7. **Adversarial conformance fixtures**
   - Multi-vendor contract collision scenarios
   - Cross-epoch vendor compatibility edge cases
   - Current fixtures: T1-T10, R1-R5, C1-C9 (24 total including temporal and receipt suites, all deterministic)

## Blockers

| Blocker | Blocks | Owner |
|---------|--------|-------|
| Mac Mini not provisioned | Ollama vendor evidence | Reuben (HUM-9) |
| Manual review not scheduled | Security/operability gate promotion | Reuben |

## Vendor Coverage

| Vendor | Surface | Status | Features | Evidence |
|--------|---------|--------|----------|----------|
| Anthropic | claude_code_cli | EVALUATED | 4 assessed | 8 receipts |
| OpenAI | codex_cli | EVALUATED | 6 assessed | mixed (2 confounded) |
| Google | gemini_cli | PENDING_EVIDENCE | 1 in inventory | `google_gemini_cli_inventory_2026-03-01.json` |
| OpenRouter | openrouter_api | PENDING_EVIDENCE | 0 | `openrouter_openrouter_api_inventory_2026-03-01.json` |
| Ollama | ollama_local | PENDING_EVIDENCE | 0 | daemon unreachable |

**Vendors evaluated:** 2/5
**Features promoted to default-on:** 0 (conservative governance posture)
**Conformance fixtures:** 24 (T1-T10, R1-R5, C1-C9)
**Open GitHub issues:** 0
