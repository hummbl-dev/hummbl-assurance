#!/usr/bin/env python3
"""Validate experimental-feature promotion gate artifact for release governance."""

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


EXPECTED_EXPERIMENTAL_FLAGS = (
    "multi_agent",
    "apps",
    "prevent_idle_sleep",
    "js_repl",
)
ALLOWED_DECISIONS = {"hold", "no-go", "promote"}


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


def _validate_payload(payload: dict[str, Any], max_age_days: int) -> list[str]:
    errors: list[str] = []

    required_top = {
        "schema_version",
        "evaluated_at",
        "audited_cli",
        "profile",
        "default_profile",
        "promotion_policy",
        "candidates",
    }
    missing = sorted(required_top - set(payload))
    if missing:
        _fail(errors, f"missing top-level keys: {', '.join(missing)}")
        return errors

    schema_version = payload.get("schema_version")
    if schema_version != "eal.experimental.feature.gate.v1":
        _fail(errors, f"schema_version must be eal.experimental.feature.gate.v1, got {schema_version!r}")

    try:
        evaluated_at = _parse_iso8601(str(payload["evaluated_at"]))
    except Exception as exc:  # noqa: BLE001
        _fail(errors, f"invalid evaluated_at timestamp: {exc}")
        evaluated_at = None

    if evaluated_at is not None and max_age_days > 0:
        age_seconds = (datetime.now(timezone.utc) - evaluated_at).total_seconds()
        max_age_seconds = max_age_days * 86400
        if age_seconds > max_age_seconds:
            _fail(
                errors,
                f"gate artifact stale: evaluated_at={evaluated_at.isoformat()} exceeds max_age_days={max_age_days}",
            )

    default_profile = payload.get("default_profile")
    if not isinstance(default_profile, dict):
        _fail(errors, "default_profile must be an object")
        return errors

    flags = default_profile.get("experimental_flags")
    if not isinstance(flags, dict):
        _fail(errors, "default_profile.experimental_flags must be an object")
        return errors

    for key in EXPECTED_EXPERIMENTAL_FLAGS:
        if key not in flags:
            _fail(errors, f"default_profile.experimental_flags missing key: {key}")
            continue
        if flags[key] is not False:
            _fail(errors, f"default_profile.experimental_flags.{key} must be false")

    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        _fail(errors, "candidates must be a non-empty array")
        return errors

    promote_count = 0
    for idx, candidate in enumerate(candidates):
        prefix = f"candidates[{idx}]"
        if not isinstance(candidate, dict):
            _fail(errors, f"{prefix} must be an object")
            continue

        for key in (
            "slug",
            "task_count_scored",
            "task_count_excluded_confounds",
            "confounded",
            "speedup_ratio",
            "gates",
            "decision",
        ):
            if key not in candidate:
                _fail(errors, f"{prefix} missing key: {key}")

        decision = candidate.get("decision")
        if decision not in ALLOWED_DECISIONS:
            _fail(errors, f"{prefix}.decision must be one of {sorted(ALLOWED_DECISIONS)}")
            continue

        if decision == "promote":
            promote_count += 1
            gates = candidate.get("gates")
            if not isinstance(gates, dict):
                _fail(errors, f"{prefix}.gates must be an object for promoted candidate")
                continue

            if candidate.get("confounded") is not False:
                _fail(errors, f"{prefix} promoted candidate must be confounded=false")

            required_true = ("reliability_gate", "value_gate", "signal_quality_gate")
            for gate in required_true:
                if gates.get(gate) is not True:
                    _fail(errors, f"{prefix}.gates.{gate} must be true for promoted candidate")

            if gates.get("security_gate") != "passed":
                _fail(errors, f"{prefix}.gates.security_gate must be 'passed' for promoted candidate")
            if gates.get("operability_gate") != "passed":
                _fail(errors, f"{prefix}.gates.operability_gate must be 'passed' for promoted candidate")

    if promote_count == 0:
        print("PASS feature_gate.promotions.none_default_on=true")

    return errors


def _parse_codex_feature_states(output: str) -> dict[str, str]:
    states: dict[str, str] = {}
    pattern = re.compile(r"^(\S+)\s+.+\s+(true|false)$")
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        match = pattern.match(line)
        if not match:
            continue
        states[match.group(1)] = match.group(2)
    return states


def _validate_live_flags(flags: dict[str, Any], require_codex: bool) -> list[str]:
    errors: list[str] = []
    codex_bin = shutil.which("codex")
    if codex_bin is None:
        if require_codex:
            _fail(errors, "codex binary not found in PATH")
        return errors

    run = subprocess.run(
        [codex_bin, "features", "list"],
        capture_output=True,
        text=True,
        check=False,
    )
    if run.returncode != 0:
        _fail(errors, f"codex features list failed with exit_code={run.returncode}")
        return errors

    observed = _parse_codex_feature_states(run.stdout)
    for key in EXPECTED_EXPERIMENTAL_FLAGS:
        expected = "true" if bool(flags.get(key)) else "false"
        actual = observed.get(key)
        if actual is None:
            _fail(errors, f"live feature state missing for {key}")
            continue
        if actual != expected:
            _fail(errors, f"live feature state mismatch for {key}: expected={expected} actual={actual}")
        else:
            print(f"PASS feature_gate.live.{key}={actual}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify experimental feature gate artifact")
    parser.add_argument(
        "--gate",
        type=Path,
        default=Path("conformance/experimental_feature_gate.json"),
        help="Path to experimental feature gate JSON artifact",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=45,
        help="Fail if evaluated_at is older than this many days (0 disables freshness check)",
    )
    parser.add_argument(
        "--live-check",
        action="store_true",
        help="Also compare expected default experimental flags with `codex features list`",
    )
    parser.add_argument(
        "--require-codex",
        action="store_true",
        help="Fail if --live-check is requested and codex is unavailable",
    )
    args = parser.parse_args()

    if not args.gate.exists():
        print(f"FAIL feature_gate.file.missing path={args.gate}", file=sys.stderr)
        return 1

    try:
        payload = json.loads(args.gate.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL feature_gate.file.invalid_json error={exc}", file=sys.stderr)
        return 1

    if not isinstance(payload, dict):
        print("FAIL feature_gate.file.invalid_payload_type expected=object", file=sys.stderr)
        return 1

    errors = _validate_payload(payload, max_age_days=args.max_age_days)

    default_flags = payload.get("default_profile", {}).get("experimental_flags", {})
    if args.live_check:
        errors.extend(_validate_live_flags(default_flags, require_codex=args.require_codex))

    if errors:
        for error in errors:
            print(f"FAIL feature_gate.{error}", file=sys.stderr)
        return 1

    print(f"PASS feature_gate.file.present path={args.gate}")
    print("PASS feature_gate.schema_version=eal.experimental.feature.gate.v1")
    print("PASS feature_gate.default_profile.experimental_flags=all_false")
    print(f"PASS feature_gate.max_age_days<={args.max_age_days}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
