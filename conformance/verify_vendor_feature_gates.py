#!/usr/bin/env python3
"""Verify multi-vendor experimental feature gate artifact for release governance."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_VENDOR_STATUS = {"evaluated", "pending_evidence", "not_applicable"}
ALLOWED_DECISIONS = {"hold", "no-go", "promote"}

# Codex is currently the only vendor with a local live parity adapter.
CODEX_VENDOR_KEY = ("openai", "codex_cli")
CODEX_FLAGS = ("multi_agent", "apps", "prevent_idle_sleep", "js_repl")


def _parse_iso8601(value: str) -> datetime:
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fail(errors: list[str], message: str) -> None:
    errors.append(message)


def _parse_required_vendor_surfaces(
    payload: dict[str, Any],
    errors: list[str],
) -> set[tuple[str, str]]:
    surfaces = payload.get("required_vendor_surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        _fail(errors, "required_vendor_surfaces must be non-empty array")
        return set()

    required: set[tuple[str, str]] = set()
    for idx, entry in enumerate(surfaces):
        prefix = f"required_vendor_surfaces[{idx}]"
        if not isinstance(entry, dict):
            _fail(errors, f"{prefix} must be object")
            continue

        vendor_id = str(entry.get("vendor_id", "")).strip()
        surface_id = str(entry.get("surface_id", "")).strip()
        if not vendor_id:
            _fail(errors, f"{prefix}.vendor_id must be non-empty string")
        if not surface_id:
            _fail(errors, f"{prefix}.surface_id must be non-empty string")

        if vendor_id and surface_id:
            key = (vendor_id, surface_id)
            if key in required:
                _fail(errors, f"{prefix} duplicates vendor/surface key: {vendor_id}/{surface_id}")
            required.add(key)

    return required


def _normalize_feature_inventory(value: Any, key: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list):
        _fail(errors, f"vendor[{key}].feature_inventory must be array")
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for idx, raw in enumerate(value):
        if not isinstance(raw, str) or not raw.strip():
            _fail(errors, f"vendor[{key}].feature_inventory[{idx}] must be non-empty string")
            continue
        slug = raw.strip()
        if slug in seen:
            _fail(errors, f"vendor[{key}].feature_inventory duplicate entry: {slug}")
            continue
        seen.add(slug)
        normalized.append(slug)

    return normalized


def _validate_candidate_slug(
    candidate_slug: str,
    inventory: set[str],
    prefix: str,
    errors: list[str],
) -> None:
    if not candidate_slug:
        _fail(errors, f"{prefix}.slug must be non-empty string")
        return

    if candidate_slug in inventory:
        return

    parts = [part for part in candidate_slug.split("-") if part]
    if not parts:
        _fail(errors, f"{prefix}.slug invalid composite tokenization: {candidate_slug!r}")
        return

    unknown = [part for part in parts if part not in inventory]
    if unknown:
        _fail(
            errors,
            f"{prefix}.slug references unknown features: {', '.join(unknown)}",
        )


def _validate_promoted_candidate(
    candidate: dict[str, Any],
    prefix: str,
    errors: list[str],
) -> None:
    gates = candidate.get("gates")
    if not isinstance(gates, dict):
        _fail(errors, f"{prefix}.gates must be object for promoted candidate")
        return

    if candidate.get("confounded") is not False:
        _fail(errors, f"{prefix} promoted candidate must be confounded=false")

    for gate in ("reliability_gate", "value_gate", "signal_quality_gate"):
        if gates.get(gate) is not True:
            _fail(errors, f"{prefix}.gates.{gate} must be true for promoted candidate")

    if gates.get("security_gate") != "passed":
        _fail(errors, f"{prefix}.gates.security_gate must be 'passed' for promoted candidate")
    if gates.get("operability_gate") != "passed":
        _fail(errors, f"{prefix}.gates.operability_gate must be 'passed' for promoted candidate")


def _validate_vendor(vendor: dict[str, Any], max_age_days: int, errors: list[str]) -> None:
    required = {
        "vendor_id",
        "surface_id",
        "status",
        "evaluated_at",
        "audited_version",
        "profile",
        "feature_inventory",
        "default_policy",
        "candidates",
        "source_receipts",
        "decision_summary",
    }
    missing = sorted(required - set(vendor))
    key = f"{vendor.get('vendor_id', '<missing_vendor>')}/{vendor.get('surface_id', '<missing_surface>')}"
    if missing:
        _fail(errors, f"vendor[{key}] missing keys: {', '.join(missing)}")
        return

    status = vendor.get("status")
    if status not in ALLOWED_VENDOR_STATUS:
        _fail(errors, f"vendor[{key}].status invalid: {status!r}")
        return

    try:
        evaluated_at = _parse_iso8601(str(vendor.get("evaluated_at")))
    except Exception as exc:  # noqa: BLE001
        _fail(errors, f"vendor[{key}].evaluated_at invalid: {exc}")
        evaluated_at = None

    if status == "evaluated" and evaluated_at is not None and max_age_days > 0:
        age_seconds = (datetime.now(timezone.utc) - evaluated_at).total_seconds()
        if age_seconds > (max_age_days * 86400):
            _fail(
                errors,
                f"vendor[{key}] stale evidence: evaluated_at={evaluated_at.isoformat()} exceeds max_age_days={max_age_days}",
            )

    feature_inventory = _normalize_feature_inventory(vendor.get("feature_inventory"), key, errors)
    feature_inventory_set = set(feature_inventory)

    if status == "evaluated":
        audited_version = str(vendor.get("audited_version", "")).strip()
        if not audited_version:
            _fail(errors, f"vendor[{key}] evaluated status requires non-empty audited_version")
        if not feature_inventory_set:
            _fail(errors, f"vendor[{key}] evaluated status requires non-empty feature_inventory")

    default_policy = vendor.get("default_policy")
    if not isinstance(default_policy, dict):
        _fail(errors, f"vendor[{key}].default_policy must be object")
        return

    experimental_flags = default_policy.get("experimental_flags")
    if not isinstance(experimental_flags, dict):
        _fail(errors, f"vendor[{key}].default_policy.experimental_flags must be object")
        return

    for flag, value in experimental_flags.items():
        if not isinstance(value, bool):
            _fail(errors, f"vendor[{key}].default_policy.experimental_flags.{flag} must be boolean")
        if flag not in feature_inventory_set:
            _fail(errors, f"vendor[{key}].default_policy.experimental_flags.{flag} not in feature_inventory")

    candidates = vendor.get("candidates")
    if not isinstance(candidates, list):
        _fail(errors, f"vendor[{key}].candidates must be array")
        return

    if status == "evaluated" and not candidates:
        _fail(errors, f"vendor[{key}] evaluated status requires non-empty candidates")
    if status in {"pending_evidence", "not_applicable"} and candidates:
        _fail(errors, f"vendor[{key}] status={status} must not include candidate evaluations")

    promote_count = 0
    for idx, candidate in enumerate(candidates):
        prefix = f"vendor[{key}].candidates[{idx}]"
        if not isinstance(candidate, dict):
            _fail(errors, f"{prefix} must be object")
            continue

        for ck in (
            "slug",
            "task_count_scored",
            "task_count_excluded_confounds",
            "confounded",
            "speedup_ratio",
            "gates",
            "decision",
        ):
            if ck not in candidate:
                _fail(errors, f"{prefix} missing key: {ck}")

        slug_value = candidate.get("slug")
        if not isinstance(slug_value, str):
            _fail(errors, f"{prefix}.slug must be string")
            continue
        _validate_candidate_slug(slug_value, feature_inventory_set, prefix, errors)

        decision = candidate.get("decision")
        if decision not in ALLOWED_DECISIONS:
            _fail(errors, f"{prefix}.decision must be one of {sorted(ALLOWED_DECISIONS)}")
            continue

        if decision == "promote":
            promote_count += 1
            _validate_promoted_candidate(candidate, prefix, errors)

    if promote_count == 0 and status == "evaluated":
        print(f"PASS vendor_gate.{key}.promotions.none_default_on=true")


def _parse_codex_feature_states(output: str) -> dict[str, str]:
    states: dict[str, str] = {}
    pattern = re.compile(r"^(\S+)\s+.+\s+(true|false)$")
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = pattern.match(line)
        if match:
            states[match.group(1)] = match.group(2)
    return states


def _live_check_codex(vendor: dict[str, Any], require_codex: bool, errors: list[str]) -> None:
    codex_bin = shutil.which("codex")
    key = f"{vendor['vendor_id']}/{vendor['surface_id']}"
    if codex_bin is None:
        if require_codex:
            _fail(errors, f"vendor[{key}] codex binary not found in PATH")
        return

    run = subprocess.run([codex_bin, "features", "list"], capture_output=True, text=True, check=False)
    if run.returncode != 0:
        _fail(errors, f"vendor[{key}] codex features list failed exit_code={run.returncode}")
        return

    observed = _parse_codex_feature_states(run.stdout)
    expected_flags = vendor["default_policy"]["experimental_flags"]
    for flag in CODEX_FLAGS:
        expected = "true" if bool(expected_flags.get(flag)) else "false"
        actual = observed.get(flag)
        if actual is None:
            _fail(errors, f"vendor[{key}] live state missing for {flag}")
            continue
        if actual != expected:
            _fail(errors, f"vendor[{key}] live mismatch {flag}: expected={expected} actual={actual}")
        else:
            print(f"PASS vendor_gate.live.{key}.{flag}={actual}")


def _validate_payload(payload: dict[str, Any], max_age_days: int) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []

    required_top = {"schema_version", "generated_at", "required_vendor_surfaces", "policy", "vendors"}
    missing = sorted(required_top - set(payload))
    if missing:
        _fail(errors, f"missing top-level keys: {', '.join(missing)}")
        return [], errors

    if payload.get("schema_version") != "eal.vendor.experimental.feature.gates.v1":
        _fail(errors, "schema_version must be eal.vendor.experimental.feature.gates.v1")

    try:
        _parse_iso8601(str(payload.get("generated_at")))
    except Exception as exc:  # noqa: BLE001
        _fail(errors, f"generated_at invalid: {exc}")

    policy = payload.get("policy")
    if not isinstance(policy, dict):
        _fail(errors, "policy must be object")
    else:
        if not isinstance(policy.get("value_gate_min_speedup_ratio"), (int, float)):
            _fail(errors, "policy.value_gate_min_speedup_ratio must be numeric")
        reqs = policy.get("manual_gate_requirements")
        if not isinstance(reqs, dict):
            _fail(errors, "policy.manual_gate_requirements must be object")

    vendors = payload.get("vendors")
    if not isinstance(vendors, list) or not vendors:
        _fail(errors, "vendors must be non-empty array")
        return [], errors

    required_surfaces = _parse_required_vendor_surfaces(payload, errors)

    seen: set[tuple[str, str]] = set()
    parsed_vendors: list[dict[str, Any]] = []
    for vendor in vendors:
        if not isinstance(vendor, dict):
            _fail(errors, "each vendors entry must be object")
            continue

        vendor_id = str(vendor.get("vendor_id", ""))
        surface_id = str(vendor.get("surface_id", ""))
        if vendor_id and surface_id:
            key = (vendor_id, surface_id)
            if key in seen:
                _fail(errors, f"duplicate vendor/surface key: {vendor_id}/{surface_id}")
            seen.add(key)

        _validate_vendor(vendor, max_age_days=max_age_days, errors=errors)
        parsed_vendors.append(vendor)

    missing_surfaces = sorted(required_surfaces - seen)
    for vendor_id, surface_id in missing_surfaces:
        _fail(errors, f"required vendor/surface missing from vendors: {vendor_id}/{surface_id}")

    return parsed_vendors, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify vendor experimental feature gates")
    parser.add_argument(
        "--gate",
        type=Path,
        default=Path("conformance/vendor_experimental_feature_gates.json"),
        help="Path to vendor gate artifact",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=45,
        help="Fail evaluated vendor evidence older than this many days (0 disables freshness)",
    )
    parser.add_argument(
        "--live-check",
        action="store_true",
        help="Run supported live parity checks for evaluated vendor surfaces",
    )
    parser.add_argument(
        "--require-codex",
        action="store_true",
        help="With --live-check, fail when codex binary is unavailable",
    )
    args = parser.parse_args()

    if not args.gate.exists():
        print(f"FAIL vendor_gate.file.missing path={args.gate}", file=sys.stderr)
        return 1

    try:
        payload = json.loads(args.gate.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL vendor_gate.file.invalid_json error={exc}", file=sys.stderr)
        return 1

    if not isinstance(payload, dict):
        print("FAIL vendor_gate.file.invalid_payload_type expected=object", file=sys.stderr)
        return 1

    vendors, errors = _validate_payload(payload, max_age_days=args.max_age_days)

    if args.live_check:
        for vendor in vendors:
            key = (vendor.get("vendor_id"), vendor.get("surface_id"))
            if key == CODEX_VENDOR_KEY and vendor.get("status") == "evaluated":
                _live_check_codex(vendor, require_codex=args.require_codex, errors=errors)

    if errors:
        for err in errors:
            print(f"FAIL vendor_gate.{err}", file=sys.stderr)
        return 1

    print(f"PASS vendor_gate.file.present path={args.gate}")
    print("PASS vendor_gate.schema_version=eal.vendor.experimental.feature.gates.v1")
    print(f"PASS vendor_gate.max_age_days<={args.max_age_days}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
