#!/usr/bin/env python3
"""Verify EAL conformance fixtures deterministically.

Checks:
- report schema validity
- primary_reason_code equals reason_codes[0]
- reason_codes order follows declared precedence
- expected report hash matches canonical bytes
- receipt fixtures: receipt schema validity + deterministic evaluator parity
- temporal fixture: INVALIDATED-by-epoch bridge proof
- compat fixtures: deterministic classifier parity
"""

from __future__ import annotations

import glob
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import validate


EAL_PROFILE = "eal-fixture-profile-v1"

EAL_PRECEDENCE = [
    "E_INPUT_MALFORMED",
    "E_CONTRACT_VERSION_COLLISION",
    "E_SIG_INVALID",
    "E_HASH_MISMATCH",
    "E_EVIDENCE_MISSING",
    "E_EPOCH_AMBIGUOUS",
    "E_ACTION_OUT_OF_SPACE",
    "E_BOUNDARY_MISMATCH",
    "E_LOG_CHAIN_BREAK",
    "E_LOG_SEQUENCE_GAP",
    "E_REPLAY_DETECTED",
    "E_EPOCH_INVALIDATED",
    "E_OK_VALID",
]
EAL_PRECEDENCE_INDEX = {code: idx for idx, code in enumerate(EAL_PRECEDENCE)}

COMPAT_PRECEDENCE = [
    "COMPAT_ACTION_REMOVED",
    "COMPAT_SEMANTICS_CHANGED",
    "COMPAT_CONSTRAINT_ADDED",
    "COMPAT_CONSTRAINT_TIGHTENED",
    "COMPAT_RISK_INCREASED",
    "COMPAT_BACKWARD_ONLY_RELAX_OR_ADD",
]
COMPAT_PRECEDENCE_INDEX = {code: idx for idx, code in enumerate(COMPAT_PRECEDENCE)}


def canonical_json_bytes(obj: dict[str, Any]) -> bytes:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return payload.encode("utf-8")


def sha256_hex(obj: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


def verify_reason_order(report: dict[str, Any], precedence_index: dict[str, int], name: str) -> None:
    reason_codes = report["reason_codes"]
    primary = report["primary_reason_code"]

    if not reason_codes:
        raise ValueError(f"{name}: reason_codes must not be empty")

    if reason_codes[0] != primary:
        raise ValueError(
            f"{name}: primary_reason_code ({primary}) does not match reason_codes[0] ({reason_codes[0]})"
        )

    try:
        expected_order = sorted(reason_codes, key=lambda code: precedence_index[code])
    except KeyError as exc:
        raise ValueError(f"{name}: unknown reason code {exc.args[0]}") from exc

    if expected_order != reason_codes:
        raise ValueError(f"{name}: reason_codes are not in precedence order")


def verify_report(
    report: dict[str, Any],
    declared_hash: str,
    schema: dict[str, Any],
    precedence_index: dict[str, int],
    name: str,
) -> None:
    validate(instance=report, schema=schema)
    verify_reason_order(report, precedence_index, name)
    digest = sha256_hex(report)
    if digest != declared_hash:
        raise ValueError(f"{name}: hash mismatch {digest} != {declared_hash}")


def evaluate_receipt(inputs: dict[str, Any]) -> dict[str, Any]:
    contract = inputs["contract"]
    receipt = inputs["receipt"]

    contract_sha = contract["contract_sha256"]
    receipt_contract_sha = receipt["contract_ref"]["contract_sha256"]
    signature = receipt["signature"]["sig"]
    evidence = receipt["evidence"]

    if receipt_contract_sha != contract_sha:
        classification, code = "INVALID", "E_CONTRACT_VERSION_COLLISION"
    elif signature == "INVALID":
        classification, code = "INVALID", "E_SIG_INVALID"
    elif not evidence:
        classification, code = "INDETERMINATE", "E_EVIDENCE_MISSING"
    else:
        classification, code = "VALID", "E_OK_VALID"

    return {
        "schema_version": "eal.validation.report.v1",
        "classification": classification,
        "primary_reason_code": code,
        "reason_codes": [code],
        "contract_ref": {
            "contract_id": receipt["contract_ref"]["contract_id"],
            "contract_hash": f"sha256:{receipt_contract_sha}",
        },
        "receipt_ref": {
            "receipt_id": receipt["execution_id"],
            "receipt_hash": f"sha256:{receipt['integrity']['receipt_c14n_sha256']}",
        },
        "evaluated_epoch": receipt["epoch_ref"]["epoch_number"],
        "validator_profile": EAL_PROFILE,
    }


def evaluate_compat(inputs: dict[str, Any]) -> dict[str, Any]:
    contract_a = inputs["contract_a"]
    contract_b = inputs["contract_b"]

    a_actions = set(contract_a["action_space"])
    b_actions = set(contract_b["action_space"])
    actions_added = sorted(b_actions - a_actions)
    actions_removed = sorted(a_actions - b_actions)

    a_constraints = contract_a["constraints"]
    b_constraints = contract_b["constraints"]
    a_keys = set(a_constraints)
    b_keys = set(b_constraints)
    constraints_added = sorted(b_keys - a_keys)
    constraints_removed = sorted(a_keys - b_keys)

    constraints_tightened = []
    constraints_loosened = []
    for key in sorted(a_keys & b_keys):
        aval = a_constraints[key]
        bval = b_constraints[key]
        if isinstance(aval, (int, float)) and isinstance(bval, (int, float)):
            if bval < aval:
                constraints_tightened.append(key)
            elif bval > aval:
                constraints_loosened.append(key)

    a_risk = contract_a["risk_policy"]
    b_risk = contract_b["risk_policy"]
    risk_increased = []
    risk_decreased = []
    for key in sorted(set(a_risk) & set(b_risk)):
        if b_risk[key] > a_risk[key]:
            risk_increased.append(key)
        elif b_risk[key] < a_risk[key]:
            risk_decreased.append(key)

    semantics_changed = bool(contract_b.get("semantics_changed", False))

    reasons = []
    if actions_removed:
        reasons.append("COMPAT_ACTION_REMOVED")
    if semantics_changed:
        reasons.append("COMPAT_SEMANTICS_CHANGED")
    if constraints_added:
        reasons.append("COMPAT_CONSTRAINT_ADDED")
    if constraints_tightened:
        reasons.append("COMPAT_CONSTRAINT_TIGHTENED")
    if risk_increased:
        reasons.append("COMPAT_RISK_INCREASED")

    if actions_removed or semantics_changed:
        classification = "INCOMPATIBLE"
        reasons = [
            reason
            for reason in reasons
            if reason in ("COMPAT_ACTION_REMOVED", "COMPAT_SEMANTICS_CHANGED")
        ]
    elif constraints_added or constraints_tightened or risk_increased:
        classification = "CONDITIONAL"
        reasons = [
            reason
            for reason in reasons
            if reason
            in (
                "COMPAT_CONSTRAINT_ADDED",
                "COMPAT_CONSTRAINT_TIGHTENED",
                "COMPAT_RISK_INCREASED",
            )
        ]
    else:
        classification = "BACKWARD_COMPATIBLE"
        reasons = ["COMPAT_BACKWARD_ONLY_RELAX_OR_ADD"]

    return {
        "schema_version": "eal.compat.report.v1",
        "classification": classification,
        "primary_reason_code": reasons[0],
        "reason_codes": reasons,
        "contract_a_ref": {
            "contract_id": contract_a["contract_id"],
            "contract_hash": f"sha256:{contract_a['contract_sha256']}",
        },
        "contract_b_ref": {
            "contract_id": contract_b["contract_id"],
            "contract_hash": f"sha256:{contract_b['contract_sha256']}",
        },
        "diff_summary": {
            "actions_added": actions_added,
            "actions_removed": actions_removed,
            "constraints_added": constraints_added,
            "constraints_removed": constraints_removed,
            "constraints_tightened": constraints_tightened,
            "constraints_loosened": constraints_loosened,
            "risk_increased": risk_increased,
            "risk_decreased": risk_decreased,
            "semantics_changed": semantics_changed,
        },
        "evaluator_profile": EAL_PROFILE,
    }


def evaluate_temporal(inputs: dict[str, Any]) -> dict[str, Any]:
    contract_a = inputs["contract_a"]
    contract_b = inputs["contract_b"]
    receipt = inputs["receipt"]

    action_ids = [entry["action_id"] for entry in receipt["actions"]]
    a_actions = set(contract_a["action_space"])
    b_actions = set(contract_b["action_space"])

    if not all(action_id in a_actions for action_id in action_ids):
        classification, code = "INVALID", "E_ACTION_OUT_OF_SPACE"
    elif not all(action_id in b_actions for action_id in action_ids):
        classification, code = "INVALIDATED", "E_EPOCH_INVALIDATED"
    else:
        classification, code = "VALID", "E_OK_VALID"

    report = {
        "schema_version": "eal.validation.report.v1",
        "classification": classification,
        "primary_reason_code": code,
        "reason_codes": [code],
        "contract_ref": {
            "contract_id": contract_b["contract_id"],
            "contract_hash": f"sha256:{contract_b['contract_sha256']}",
        },
        "receipt_ref": {
            "receipt_id": receipt["execution_id"],
            "receipt_hash": f"sha256:{receipt['integrity']['receipt_c14n_sha256']}",
        },
        "evaluated_epoch": contract_b["epoch_number"],
        "validator_profile": EAL_PROFILE,
    }
    if classification == "INVALIDATED":
        report["origin_epoch"] = contract_a["epoch_number"]
    return report


def verify_validation_fixtures(base: Path, validation_schema: dict[str, Any]) -> None:
    fixture_paths = sorted(Path(p) for p in glob.glob(str(base / "fixtures" / "*.json")))
    if not fixture_paths:
        raise ValueError("no validation fixtures found")

    for fixture_path in fixture_paths:
        with fixture_path.open("r", encoding="utf-8") as fh:
            fixture = json.load(fh)

        verify_report(
            fixture["expected_report"],
            fixture["expected_report_sha256"],
            validation_schema,
            EAL_PRECEDENCE_INDEX,
            fixture_path.name,
        )
        print(f"PASS {fixture_path.name}")


def verify_receipt_fixtures(
    base: Path,
    validation_schema: dict[str, Any],
    receipt_schema: dict[str, Any],
) -> None:
    fixture_paths = sorted(Path(p) for p in glob.glob(str(base / "fixtures_receipt" / "*.json")))
    if not fixture_paths:
        raise ValueError("no receipt fixtures found")

    for fixture_path in fixture_paths:
        with fixture_path.open("r", encoding="utf-8") as fh:
            fixture = json.load(fh)

        validate(instance=fixture["inputs"]["receipt"], schema=receipt_schema)

        derived_report = evaluate_receipt(fixture["inputs"])
        expected_report = fixture["expected_report"]
        if derived_report != expected_report:
            raise ValueError(
                f"{fixture_path.name}: derived receipt report does not match expected_report"
            )

        verify_report(
            expected_report,
            fixture["expected_report_sha256"],
            validation_schema,
            EAL_PRECEDENCE_INDEX,
            fixture_path.name,
        )
        print(f"PASS {fixture_path.name}")


def verify_temporal_fixtures(
    base: Path,
    validation_schema: dict[str, Any],
    receipt_schema: dict[str, Any],
) -> None:
    fixture_paths = sorted(Path(p) for p in glob.glob(str(base / "fixtures_temporal" / "*.json")))
    if not fixture_paths:
        raise ValueError("no temporal fixtures found")

    for fixture_path in fixture_paths:
        with fixture_path.open("r", encoding="utf-8") as fh:
            fixture = json.load(fh)

        validate(instance=fixture["inputs"]["receipt"], schema=receipt_schema)

        compat_report = evaluate_compat(
            {
                "contract_a": fixture["inputs"]["contract_a"],
                "contract_b": fixture["inputs"]["contract_b"],
            }
        )
        if compat_report["classification"] == "BACKWARD_COMPATIBLE":
            raise ValueError(
                f"{fixture_path.name}: temporal invalidation fixture requires non-backward compatibility"
            )

        expected_report = fixture["expected_report"]
        derived_report = evaluate_temporal(fixture["inputs"])
        if derived_report != expected_report:
            raise ValueError(
                f"{fixture_path.name}: derived temporal report does not match expected_report"
            )

        verify_report(
            expected_report,
            fixture["expected_report_sha256"],
            validation_schema,
            EAL_PRECEDENCE_INDEX,
            fixture_path.name,
        )
        print(f"PASS {fixture_path.name}")


def verify_compat_fixtures(base: Path, compat_schema: dict[str, Any]) -> None:
    fixture_paths = sorted(Path(p) for p in glob.glob(str(base / "fixtures_compat" / "*.json")))
    if not fixture_paths:
        raise ValueError("no compat fixtures found")

    for fixture_path in fixture_paths:
        with fixture_path.open("r", encoding="utf-8") as fh:
            fixture = json.load(fh)

        expected_report = fixture["expected_compat_report"]
        derived_report = evaluate_compat(fixture["inputs"])
        if derived_report != expected_report:
            raise ValueError(
                f"{fixture_path.name}: derived compat report does not match expected_compat_report"
            )

        verify_report(
            expected_report,
            fixture["expected_compat_report_sha256"],
            compat_schema,
            COMPAT_PRECEDENCE_INDEX,
            fixture_path.name,
        )
        print(f"PASS {fixture_path.name}")


def main() -> int:
    base = Path(__file__).resolve().parent

    with (base / "validation_report.schema.json").open("r", encoding="utf-8") as fh:
        validation_schema = json.load(fh)
    with (base / "receipt.schema.json").open("r", encoding="utf-8") as fh:
        receipt_schema = json.load(fh)
    with (base / "compat_report.schema.json").open("r", encoding="utf-8") as fh:
        compat_schema = json.load(fh)

    verify_validation_fixtures(base, validation_schema)
    verify_receipt_fixtures(base, validation_schema, receipt_schema)
    verify_temporal_fixtures(base, validation_schema, receipt_schema)
    verify_compat_fixtures(base, compat_schema)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
