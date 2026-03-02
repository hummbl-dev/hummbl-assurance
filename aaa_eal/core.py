"""Deterministic EAL core evaluators used by conformance and CLI."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

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

EAL_CODE_CLASS = {
    "E_OK_VALID": "VALID",
    "E_INPUT_MALFORMED": "INDETERMINATE",
    "E_EVIDENCE_MISSING": "INDETERMINATE",
    "E_EPOCH_AMBIGUOUS": "INDETERMINATE",
    "E_SIG_INVALID": "INVALID",
    "E_HASH_MISMATCH": "INVALID",
    "E_CONTRACT_VERSION_COLLISION": "INVALID",
    "E_ACTION_OUT_OF_SPACE": "INVALID",
    "E_BOUNDARY_MISMATCH": "INVALID",
    "E_LOG_CHAIN_BREAK": "INVALID",
    "E_LOG_SEQUENCE_GAP": "INVALID",
    "E_REPLAY_DETECTED": "INVALID",
    "E_EPOCH_INVALIDATED": "INVALIDATED",
}

COMPAT_PRECEDENCE = [
    "COMPAT_ACTION_REMOVED",
    "COMPAT_SEMANTICS_CHANGED",
    "COMPAT_CONSTRAINT_ADDED",
    "COMPAT_CONSTRAINT_TIGHTENED",
    "COMPAT_RISK_INCREASED",
    "COMPAT_BACKWARD_ONLY_RELAX_OR_ADD",
]
COMPAT_PRECEDENCE_INDEX = {code: idx for idx, code in enumerate(COMPAT_PRECEDENCE)}

VALIDATION_EXIT_CODES = {
    "VALID": 0,
    "INVALID": 10,
    "INVALIDATED": 11,
    "INDETERMINATE": 12,
}

COMPAT_EXIT_CODES = {
    "BACKWARD_COMPATIBLE": 0,
    "CONDITIONAL": 20,
    "INCOMPATIBLE": 21,
}


@dataclass(frozen=True)
class NormalizedValidationContract:
    contract_id: str
    contract_hash: str
    epoch_number: int | None
    action_space: list[str]
    boundary_rules: dict[str, Any]


@dataclass(frozen=True)
class NormalizedValidationAction:
    action_id: str
    params: dict[str, Any]
    boundary_decision: str | None


@dataclass(frozen=True)
class NormalizedValidationReceipt:
    receipt_id: str
    contract_id: str
    contract_hash: str
    epoch_number: int | None
    epoch_explicit: bool
    signature_valid: bool
    actions: list[NormalizedValidationAction]
    evidence_count: int
    receipt_hash: str
    hash_mismatch: bool
    log_chain_break: bool
    log_sequence_gap: bool
    replay_detected: bool


@dataclass(frozen=True)
class NormalizedCompatContract:
    contract_id: str
    contract_hash: str
    action_space: list[str]
    constraints: dict[str, Any]
    risk_policy: dict[str, Any]
    semantics_changed: bool


def canonical_json_bytes(obj: dict[str, Any]) -> bytes:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return payload.encode("utf-8")


def sha256_hex(obj: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


def ordered_reason_codes(codes: list[str], precedence_index: dict[str, int]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for code in codes:
        if code not in seen:
            seen.add(code)
            unique.append(code)
    return sorted(unique, key=lambda code: precedence_index[code])


def render_json(report: dict[str, Any], canonical: bool = True) -> str:
    if canonical:
        return canonical_json_bytes(report).decode("utf-8")
    return json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _read_non_empty_str(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing or invalid {key}")
    return value


def _sha_prefixed(value: str) -> str:
    if value.startswith("sha256:"):
        return value
    return f"sha256:{value}"


def _normalize_contract_hash(contract: dict[str, Any]) -> str:
    raw = contract.get("contract_hash")
    if raw is None:
        raw = contract.get("contract_sha256")
    if not isinstance(raw, str) or not raw:
        raise ValueError("missing contract hash")
    return _sha_prefixed(raw)


def normalize_validation_contract(contract: dict[str, Any]) -> NormalizedValidationContract:
    if not isinstance(contract, dict):
        raise ValueError("contract must be object")

    contract_id = _read_non_empty_str(contract, "contract_id")
    contract_hash = _normalize_contract_hash(contract)

    epoch_raw = contract.get("epoch")
    if epoch_raw is None:
        epoch_raw = contract.get("epoch_number")
    if epoch_raw is not None and (not isinstance(epoch_raw, int) or epoch_raw < 0):
        raise ValueError("invalid epoch")

    action_space = contract.get("action_space", [])
    if not isinstance(action_space, list) or any(
        not isinstance(action_id, str) or not action_id for action_id in action_space
    ):
        raise ValueError("invalid action_space")

    boundary_rules = contract.get("boundary_rules", {})
    if boundary_rules is None:
        boundary_rules = {}
    if not isinstance(boundary_rules, dict):
        raise ValueError("invalid boundary_rules")

    for _action_id, _rule in boundary_rules.items():
        if isinstance(_rule, dict):
            _allow = _rule.get("allow")
            if _allow is not None and not isinstance(_allow, bool):
                raise ValueError("boundary_rules allow must be boolean")

    return NormalizedValidationContract(
        contract_id=contract_id,
        contract_hash=contract_hash,
        epoch_number=epoch_raw,
        action_space=action_space,
        boundary_rules=boundary_rules,
    )


def _normalize_validation_action_schema(action: dict[str, Any]) -> NormalizedValidationAction:
    action_id = _read_non_empty_str(action, "action_id")

    params: dict[str, Any]
    if "params_inline" in action:
        params_inline = action.get("params_inline")
        if not isinstance(params_inline, dict):
            raise ValueError("invalid params_inline")
        params = params_inline
    elif "params" in action:
        params_value = action.get("params")
        if not isinstance(params_value, dict):
            raise ValueError("invalid params")
        params = params_value
    else:
        params = {}

    boundary_decision: str | None = None
    if "boundary_assertion" in action:
        boundary = action.get("boundary_assertion")
        if not isinstance(boundary, dict):
            raise ValueError("invalid boundary_assertion")
        boundary_decision = boundary.get("decision")
    elif "boundary_decision" in action:
        boundary_decision = action.get("boundary_decision")

    if boundary_decision is not None and boundary_decision not in ("ALLOW", "DENY"):
        raise ValueError("invalid boundary decision")

    return NormalizedValidationAction(
        action_id=action_id,
        params=params,
        boundary_decision=boundary_decision,
    )


def normalize_validation_receipt(receipt: dict[str, Any]) -> NormalizedValidationReceipt:
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be object")

    schema_style = "execution_id" in receipt

    if schema_style:
        receipt_id = _read_non_empty_str(receipt, "execution_id")

        contract_ref = receipt.get("contract_ref")
        if not isinstance(contract_ref, dict):
            raise ValueError("missing contract_ref")
        contract_id = _read_non_empty_str(contract_ref, "contract_id")

        contract_hash_raw = contract_ref.get("contract_sha256")
        if contract_hash_raw is None:
            contract_hash_raw = contract_ref.get("contract_hash")
        if not isinstance(contract_hash_raw, str) or not contract_hash_raw:
            raise ValueError("missing contract hash in receipt")
        contract_hash = _sha_prefixed(contract_hash_raw)

        epoch_ref = receipt.get("epoch_ref")
        if not isinstance(epoch_ref, dict):
            raise ValueError("missing epoch_ref")
        epoch_raw = epoch_ref.get("epoch_number")
        if epoch_raw is not None and (not isinstance(epoch_raw, int) or epoch_raw < 0):
            raise ValueError("invalid epoch_number")
        epoch_explicit = True

        signature = receipt.get("signature")
        if not isinstance(signature, dict):
            raise ValueError("missing signature")
        sig_raw = signature.get("sig")
        if not isinstance(sig_raw, str) or not sig_raw:
            raise ValueError("invalid signature")
        signature_valid = sig_raw != "INVALID"

        evidence = receipt.get("evidence")
        if not isinstance(evidence, list):
            raise ValueError("invalid evidence")

        integrity = receipt.get("integrity")
        if not isinstance(integrity, dict):
            raise ValueError("missing integrity")
        receipt_hash_raw = integrity.get("receipt_c14n_sha256")
        if not isinstance(receipt_hash_raw, str) or not receipt_hash_raw:
            raise ValueError("missing receipt hash")
        receipt_hash = _sha_prefixed(receipt_hash_raw)

        hash_mismatch = integrity.get("status") == "mismatch"

        log_integrity = receipt.get("log_integrity")
        if not isinstance(log_integrity, dict):
            log_integrity = {}
        log_chain_break = log_integrity.get("chain") == "broken"
        log_sequence_gap = log_integrity.get("sequence") == "gap"

        replay_detected = bool(receipt.get("replay_detected", False))

        actions_raw = receipt.get("actions")
        if not isinstance(actions_raw, list):
            raise ValueError("invalid actions")
        actions = [_normalize_validation_action_schema(action) for action in actions_raw]
    else:
        receipt_id = _read_non_empty_str(receipt, "receipt_id")
        contract_id = _read_non_empty_str(receipt, "contract_id")

        contract_hash = _sha_prefixed(_read_non_empty_str(receipt, "contract_hash"))

        signature = receipt.get("signature")
        if not isinstance(signature, dict):
            raise ValueError("missing signature")
        signature_status = signature.get("status")
        if not isinstance(signature_status, str):
            raise ValueError("missing signature.status")
        signature_valid = signature_status == "valid"

        evidence = receipt.get("evidence")
        if not isinstance(evidence, list):
            raise ValueError("invalid evidence")

        receipt_hash = _sha_prefixed(_read_non_empty_str(receipt, "receipt_hash"))

        epoch_raw = receipt.get("epoch")
        if epoch_raw is not None and (not isinstance(epoch_raw, int) or epoch_raw < 0):
            raise ValueError("invalid epoch")
        epoch_explicit = "epoch" in receipt

        hash_mismatch = bool(receipt.get("hash_mismatch", False))
        log_chain_break = bool(receipt.get("log_chain_break", False))
        log_sequence_gap = bool(receipt.get("log_sequence_gap", False))
        replay_detected = bool(receipt.get("replay_detected", False))

        actions_raw = receipt.get("actions")
        if not isinstance(actions_raw, list):
            raise ValueError("invalid actions")
        actions = [_normalize_validation_action_schema(action) for action in actions_raw]

    return NormalizedValidationReceipt(
        receipt_id=receipt_id,
        contract_id=contract_id,
        contract_hash=contract_hash,
        epoch_number=epoch_raw,
        epoch_explicit=epoch_explicit,
        signature_valid=signature_valid,
        actions=actions,
        evidence_count=len(evidence),
        receipt_hash=receipt_hash,
        hash_mismatch=hash_mismatch,
        log_chain_break=log_chain_break,
        log_sequence_gap=log_sequence_gap,
        replay_detected=replay_detected,
    )


def _boundary_mismatch(
    actions: list[NormalizedValidationAction],
    boundary_rules: dict[str, Any],
) -> bool:
    for action in actions:
        rule = boundary_rules.get(action.action_id)
        if not isinstance(rule, dict):
            continue

        allow_raw = rule.get("allow")
        expected_decision = "ALLOW" if bool(allow_raw) else "DENY"
        if action.boundary_decision is not None and action.boundary_decision != expected_decision:
            return True

        required_params = rule.get("required_params", [])
        if bool(allow_raw) and isinstance(required_params, list):
            for required in required_params:
                if isinstance(required, str) and required not in action.params:
                    return True
    return False


def _validation_malformed_report(profile: str) -> dict[str, Any]:
    return {
        "schema_version": "eal.validation.report.v1",
        "classification": "INDETERMINATE",
        "primary_reason_code": "E_INPUT_MALFORMED",
        "reason_codes": ["E_INPUT_MALFORMED"],
        "contract_ref": {
            "contract_id": "unknown",
            "contract_hash": "sha256:unknown",
        },
        "receipt_ref": {
            "receipt_id": "unknown",
            "receipt_hash": "sha256:unknown",
        },
        "evaluated_epoch": 0,
        "validator_profile": profile,
    }


def evaluate_validation(
    contract: dict[str, Any],
    receipt: dict[str, Any],
    *,
    validator_profile: str = EAL_PROFILE,
) -> dict[str, Any]:
    try:
        n_contract = normalize_validation_contract(contract)
        n_receipt = normalize_validation_receipt(receipt)
    except ValueError:
        return _validation_malformed_report(validator_profile)

    reason_codes: list[str] = []

    if n_contract.contract_hash != n_receipt.contract_hash:
        reason_codes.append("E_CONTRACT_VERSION_COLLISION")

    if not n_receipt.signature_valid:
        reason_codes.append("E_SIG_INVALID")

    if n_receipt.hash_mismatch:
        reason_codes.append("E_HASH_MISMATCH")

    evidence_missing = n_receipt.evidence_count == 0
    if evidence_missing:
        reason_codes.append("E_EVIDENCE_MISSING")

    if n_receipt.epoch_explicit and n_receipt.epoch_number is None:
        reason_codes.append("E_EPOCH_AMBIGUOUS")
    elif (
        n_receipt.epoch_explicit
        and n_contract.epoch_number is not None
        and n_contract.epoch_number != n_receipt.epoch_number
    ):
        reason_codes.append("E_EPOCH_AMBIGUOUS")

    if not evidence_missing:
        action_space = set(n_contract.action_space)
        if any(action.action_id not in action_space for action in n_receipt.actions):
            reason_codes.append("E_ACTION_OUT_OF_SPACE")

        if _boundary_mismatch(n_receipt.actions, n_contract.boundary_rules):
            reason_codes.append("E_BOUNDARY_MISMATCH")

        if n_receipt.log_chain_break:
            reason_codes.append("E_LOG_CHAIN_BREAK")

        if n_receipt.log_sequence_gap:
            reason_codes.append("E_LOG_SEQUENCE_GAP")

        if n_receipt.replay_detected:
            reason_codes.append("E_REPLAY_DETECTED")

    if not reason_codes:
        reason_codes = ["E_OK_VALID"]

    reason_codes = ordered_reason_codes(reason_codes, EAL_PRECEDENCE_INDEX)
    primary_reason_code = reason_codes[0]
    classification = EAL_CODE_CLASS[primary_reason_code]

    evaluated_epoch = n_receipt.epoch_number
    if evaluated_epoch is None:
        evaluated_epoch = n_contract.epoch_number
    if evaluated_epoch is None:
        evaluated_epoch = 0

    return {
        "schema_version": "eal.validation.report.v1",
        "classification": classification,
        "primary_reason_code": primary_reason_code,
        "reason_codes": reason_codes,
        "contract_ref": {
            "contract_id": n_receipt.contract_id,
            "contract_hash": n_receipt.contract_hash,
        },
        "receipt_ref": {
            "receipt_id": n_receipt.receipt_id,
            "receipt_hash": n_receipt.receipt_hash,
        },
        "evaluated_epoch": evaluated_epoch,
        "validator_profile": validator_profile,
    }


def evaluate_temporal_validation(
    contract_origin: dict[str, Any],
    contract_target: dict[str, Any],
    receipt: dict[str, Any],
    *,
    validator_profile: str = EAL_PROFILE,
) -> dict[str, Any]:
    """Evaluate a receipt across governance epochs.

    The receipt must first be valid under the origin contract. If origin
    validation fails, that origin result is returned. If origin validation
    passes but target action-space closure fails, classification is
    INVALIDATED with E_EPOCH_INVALIDATED.
    """

    origin_report = evaluate_validation(
        contract_origin,
        receipt,
        validator_profile=validator_profile,
    )
    if origin_report["classification"] != "VALID":
        return origin_report

    try:
        n_target = normalize_validation_contract(contract_target)
        n_receipt = normalize_validation_receipt(receipt)
    except ValueError:
        return _validation_malformed_report(validator_profile)

    target_actions = set(n_target.action_space)
    action_ids = [action.action_id for action in n_receipt.actions]

    if any(action_id not in target_actions for action_id in action_ids):
        report: dict[str, Any] = {
            "schema_version": "eal.validation.report.v1",
            "classification": "INVALIDATED",
            "primary_reason_code": "E_EPOCH_INVALIDATED",
            "reason_codes": ["E_EPOCH_INVALIDATED"],
            "contract_ref": {
                "contract_id": n_target.contract_id,
                "contract_hash": n_target.contract_hash,
            },
            "receipt_ref": {
                "receipt_id": n_receipt.receipt_id,
                "receipt_hash": n_receipt.receipt_hash,
            },
            "evaluated_epoch": n_target.epoch_number if n_target.epoch_number is not None else 0,
            "validator_profile": validator_profile,
        }
        report["origin_epoch"] = n_receipt.epoch_number if n_receipt.epoch_number is not None else 0
        return report

    return {
        "schema_version": "eal.validation.report.v1",
        "classification": "VALID",
        "primary_reason_code": "E_OK_VALID",
        "reason_codes": ["E_OK_VALID"],
        "contract_ref": {
            "contract_id": n_target.contract_id,
            "contract_hash": n_target.contract_hash,
        },
        "receipt_ref": {
            "receipt_id": n_receipt.receipt_id,
            "receipt_hash": n_receipt.receipt_hash,
        },
        "evaluated_epoch": n_target.epoch_number if n_target.epoch_number is not None else 0,
        "validator_profile": validator_profile,
    }


def normalize_compat_contract(contract: dict[str, Any]) -> NormalizedCompatContract:
    if not isinstance(contract, dict):
        raise ValueError("contract must be object")

    contract_id = _read_non_empty_str(contract, "contract_id")
    contract_hash = _normalize_contract_hash(contract)

    action_space = contract.get("action_space")
    if not isinstance(action_space, list) or any(
        not isinstance(action_id, str) or not action_id for action_id in action_space
    ):
        raise ValueError("invalid action_space")

    constraints = contract.get("constraints", {})
    if not isinstance(constraints, dict):
        raise ValueError("invalid constraints")

    risk_policy = contract.get("risk_policy", {})
    if not isinstance(risk_policy, dict):
        raise ValueError("invalid risk_policy")

    semantics_changed = bool(contract.get("semantics_changed", False))

    return NormalizedCompatContract(
        contract_id=contract_id,
        contract_hash=contract_hash,
        action_space=action_space,
        constraints=constraints,
        risk_policy=risk_policy,
        semantics_changed=semantics_changed,
    )


def evaluate_compat(
    contract_a: dict[str, Any],
    contract_b: dict[str, Any],
    *,
    evaluator_profile: str = EAL_PROFILE,
) -> dict[str, Any]:
    a = normalize_compat_contract(contract_a)
    b = normalize_compat_contract(contract_b)

    a_actions = set(a.action_space)
    b_actions = set(b.action_space)

    actions_added = sorted(b_actions - a_actions)
    actions_removed = sorted(a_actions - b_actions)

    a_keys = set(a.constraints)
    b_keys = set(b.constraints)
    constraints_added = sorted(b_keys - a_keys)
    constraints_removed = sorted(a_keys - b_keys)

    constraints_tightened: list[str] = []
    constraints_loosened: list[str] = []
    for key in sorted(a_keys & b_keys):
        a_value = a.constraints[key]
        b_value = b.constraints[key]
        if isinstance(a_value, (int, float)) and isinstance(b_value, (int, float)):
            if b_value < a_value:
                constraints_tightened.append(key)
            elif b_value > a_value:
                constraints_loosened.append(key)

    risk_increased: list[str] = []
    risk_decreased: list[str] = []
    for key in sorted(set(a.risk_policy) & set(b.risk_policy)):
        a_value = a.risk_policy[key]
        b_value = b.risk_policy[key]
        if isinstance(a_value, (int, float)) and isinstance(b_value, (int, float)):
            if b_value > a_value:
                risk_increased.append(key)
            elif b_value < a_value:
                risk_decreased.append(key)

    reasons: list[str] = []
    if actions_removed:
        reasons.append("COMPAT_ACTION_REMOVED")
    if b.semantics_changed:
        reasons.append("COMPAT_SEMANTICS_CHANGED")
    if constraints_added:
        reasons.append("COMPAT_CONSTRAINT_ADDED")
    if constraints_tightened:
        reasons.append("COMPAT_CONSTRAINT_TIGHTENED")
    if risk_increased:
        reasons.append("COMPAT_RISK_INCREASED")

    if actions_removed or b.semantics_changed:
        classification = "INCOMPATIBLE"
        reasons = [
            reason
            for reason in reasons
            if reason in {"COMPAT_ACTION_REMOVED", "COMPAT_SEMANTICS_CHANGED"}
        ]
    elif constraints_added or constraints_tightened or risk_increased:
        classification = "CONDITIONAL"
        reasons = [
            reason
            for reason in reasons
            if reason
            in {
                "COMPAT_CONSTRAINT_ADDED",
                "COMPAT_CONSTRAINT_TIGHTENED",
                "COMPAT_RISK_INCREASED",
            }
        ]
    else:
        classification = "BACKWARD_COMPATIBLE"
        reasons = ["COMPAT_BACKWARD_ONLY_RELAX_OR_ADD"]

    reasons = ordered_reason_codes(reasons, COMPAT_PRECEDENCE_INDEX)

    return {
        "schema_version": "eal.compat.report.v1",
        "classification": classification,
        "primary_reason_code": reasons[0],
        "reason_codes": reasons,
        "contract_a_ref": {
            "contract_id": a.contract_id,
            "contract_hash": a.contract_hash,
        },
        "contract_b_ref": {
            "contract_id": b.contract_id,
            "contract_hash": b.contract_hash,
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
            "semantics_changed": b.semantics_changed,
        },
        "evaluator_profile": evaluator_profile,
    }
