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
- CLI parity: `eal verify-receipt` and `eal compat` match fixture outputs/exit codes
"""

from __future__ import annotations

import glob
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import validate


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aaa_eal.core import (  # noqa: E402
    COMPAT_EXIT_CODES,
    COMPAT_PRECEDENCE,
    EAL_PRECEDENCE,
    VALIDATION_EXIT_CODES,
    canonical_json_bytes,
    evaluate_compat,
    evaluate_validation,
    sha256_hex,
)


EAL_PRECEDENCE_INDEX = {code: idx for idx, code in enumerate(EAL_PRECEDENCE)}
COMPAT_PRECEDENCE_INDEX = {code: idx for idx, code in enumerate(COMPAT_PRECEDENCE)}


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
        "validator_profile": "eal-fixture-profile-v1",
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

        inputs = fixture["inputs"]
        if "contract" in inputs and "receipt" in inputs:
            derived_report = evaluate_validation(inputs["contract"], inputs["receipt"])
            expected_report = fixture["expected_report"]
            if derived_report != expected_report:
                raise ValueError(
                    f"{fixture_path.name}: derived validation report does not match expected_report"
                )

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

        derived_report = evaluate_validation(fixture["inputs"]["contract"], fixture["inputs"]["receipt"])
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
            fixture["inputs"]["contract_a"],
            fixture["inputs"]["contract_b"],
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
        derived_report = evaluate_compat(
            fixture["inputs"]["contract_a"],
            fixture["inputs"]["contract_b"],
        )
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


def _run_cli(command: list[str], expected_exit_code: int, fixture_name: str) -> bytes:
    run = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if run.returncode != expected_exit_code:
        stderr = run.stderr.decode("utf-8", errors="replace")
        stdout = run.stdout.decode("utf-8", errors="replace")
        raise ValueError(
            f"{fixture_name}: CLI exit mismatch {run.returncode} != {expected_exit_code}\n"
            f"STDERR:\n{stderr}\nSTDOUT:\n{stdout}"
        )
    return run.stdout


def verify_cli_receipt_fixtures(base: Path) -> None:
    fixture_paths = sorted(Path(p) for p in glob.glob(str(base / "fixtures_receipt" / "*.json")))
    if not fixture_paths:
        raise ValueError("no receipt fixtures found for CLI parity")

    for fixture_path in fixture_paths:
        with fixture_path.open("r", encoding="utf-8") as fh:
            fixture = json.load(fh)

        expected = fixture["expected_report"]
        expected_exit_code = VALIDATION_EXIT_CODES[expected["classification"]]
        expected_serialized = canonical_json_bytes(expected)

        with tempfile.TemporaryDirectory(prefix="eal-cli-") as tmpdir:
            tmp = Path(tmpdir)
            contract_path = tmp / "contract.json"
            receipt_path = tmp / "receipt.json"
            out_path = tmp / "report.json"

            contract_path.write_text(json.dumps(fixture["inputs"]["contract"]), encoding="utf-8")
            receipt_path.write_text(json.dumps(fixture["inputs"]["receipt"]), encoding="utf-8")

            stdout_bytes = _run_cli(
                [
                    str(ROOT / "eal"),
                    "verify-receipt",
                    "--contract",
                    str(contract_path),
                    "--receipt",
                    str(receipt_path),
                    "--schema-check",
                    "--out",
                    str(out_path),
                ],
                expected_exit_code,
                fixture_path.name,
            )

            if stdout_bytes != expected_serialized:
                raise ValueError(f"{fixture_path.name}: CLI stdout canonical JSON mismatch")

            parsed_stdout = json.loads(stdout_bytes.decode("utf-8"))
            if parsed_stdout != expected:
                raise ValueError(f"{fixture_path.name}: CLI stdout parsed report mismatch")

            out_bytes = out_path.read_bytes()
            if out_bytes != expected_serialized:
                raise ValueError(f"{fixture_path.name}: CLI --out payload mismatch")

        print(f"PASS {fixture_path.name} (cli)")


def verify_cli_compat_fixtures(base: Path) -> None:
    fixture_paths = sorted(Path(p) for p in glob.glob(str(base / "fixtures_compat" / "*.json")))
    if not fixture_paths:
        raise ValueError("no compat fixtures found for CLI parity")

    for fixture_path in fixture_paths:
        with fixture_path.open("r", encoding="utf-8") as fh:
            fixture = json.load(fh)

        expected = fixture["expected_compat_report"]
        expected_exit_code = COMPAT_EXIT_CODES[expected["classification"]]
        expected_serialized = canonical_json_bytes(expected)

        with tempfile.TemporaryDirectory(prefix="eal-cli-") as tmpdir:
            tmp = Path(tmpdir)
            contract_a_path = tmp / "contract_a.json"
            contract_b_path = tmp / "contract_b.json"
            out_path = tmp / "report.json"

            contract_a_path.write_text(
                json.dumps(fixture["inputs"]["contract_a"]),
                encoding="utf-8",
            )
            contract_b_path.write_text(
                json.dumps(fixture["inputs"]["contract_b"]),
                encoding="utf-8",
            )

            stdout_bytes = _run_cli(
                [
                    str(ROOT / "eal"),
                    "compat",
                    "--contract-a",
                    str(contract_a_path),
                    "--contract-b",
                    str(contract_b_path),
                    "--schema-check",
                    "--out",
                    str(out_path),
                ],
                expected_exit_code,
                fixture_path.name,
            )

            if stdout_bytes != expected_serialized:
                raise ValueError(f"{fixture_path.name}: CLI stdout canonical JSON mismatch")

            parsed_stdout = json.loads(stdout_bytes.decode("utf-8"))
            if parsed_stdout != expected:
                raise ValueError(f"{fixture_path.name}: CLI stdout parsed report mismatch")

            out_bytes = out_path.read_bytes()
            if out_bytes != expected_serialized:
                raise ValueError(f"{fixture_path.name}: CLI --out payload mismatch")

        print(f"PASS {fixture_path.name} (cli)")


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
    verify_cli_receipt_fixtures(base)
    verify_cli_compat_fixtures(base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
