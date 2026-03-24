# IP Boundary Matrix (Public HUMMBL Assurance Repo)

This matrix defines what can be published in `hummbl-dev/hummbl-assurance`.

| Artifact Type | Allowed | Redaction / Synthesis Rule | Rationale |
|---|---|---|---|
| Normative specs (`SPEC.md`) | Yes | Keep generic contract semantics; no internal policy content | Share assurance method without exposing proprietary controls |
| JSON schemas (`validation_report`, `receipt`, `compat_report`) | Yes | Use synthetic ids/examples only | Required for interoperability and conformance |
| Reason code taxonomy | Yes | No production incident references | Needed for deterministic classifier behavior |
| Conformance fixtures (`T*`, `R*`, `C*`) | Yes | Synthetic action ids, synthetic hashes, no real traces | Demonstrate behavior without leaking runtime activity |
| Verifier scripts | Yes | No network calls, no secret paths | Reproducible local verification |
| Runtime orchestration logic | No | Do not publish | Out of scope; proprietary execution substrate |
| Real action taxonomy | No | Replace with synthetic action ids | Protect HUMMBL governance semantics |
| Real contract semantics | No | Keep simplified contract surfaces | Prevent governance-model leakage |
| Production evidence bundles | No | Never publish | May contain sensitive execution/business context |
| Keys, key metadata, signatures from prod | No | Never publish | Security and compliance boundary |
| Internal org authority policy docs | No | Never publish | Operational governance is private |

## Non-Negotiables

- No real policy internals.
- No production receipts or logs.
- No secrets, tokens, or key material.
- Validation-only surface; runtime remains out of repo scope.
