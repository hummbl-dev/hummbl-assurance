"""CLI for deterministic EAL validation and compatibility reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from aaa_eal.core import (
    COMPAT_EXIT_CODES,
    VALIDATION_EXIT_CODES,
    evaluate_compat,
    evaluate_validation,
    render_json,
    sha256_hex,
)


def _load_json_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError("top-level JSON must be an object")
    return payload


def _write_output(serialized: str, out: Path | None) -> None:
    sys.stdout.write(serialized)
    if out is not None:
        out.write_text(serialized, encoding="utf-8")


def _maybe_schema_validate(
    instance: dict[str, Any],
    *,
    schema_path: Path,
) -> None:
    try:
        from jsonschema import validate
    except ModuleNotFoundError as exc:
        raise RuntimeError("jsonschema is required when --schema-check is enabled") from exc

    with schema_path.open("r", encoding="utf-8") as fh:
        schema = json.load(fh)
    validate(instance=instance, schema=schema)


def cmd_verify_receipt(args: argparse.Namespace) -> int:
    contract: dict[str, Any]
    receipt: dict[str, Any]

    parse_errors: list[str] = []

    try:
        contract = _load_json_object(Path(args.contract))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        contract = {}
        parse_errors.append(f"contract read error: {exc}")

    try:
        receipt = _load_json_object(Path(args.receipt))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        receipt = {}
        parse_errors.append(f"receipt read error: {exc}")

    report = evaluate_validation(contract, receipt)

    if args.schema_check:
        try:
            _maybe_schema_validate(
                report,
                schema_path=Path(__file__).resolve().parent.parent
                / "conformance"
                / "validation_report.schema.json",
            )
        except Exception as exc:  # noqa: BLE001 - deterministic CLI error contract
            print(f"schema validation error: {exc}", file=sys.stderr)
            return 65

    if parse_errors:
        for error in parse_errors:
            print(error, file=sys.stderr)

    serialized = render_json(report, canonical=not args.pretty)
    _write_output(serialized, Path(args.out) if args.out else None)

    if args.print_hash:
        print(sha256_hex(report), file=sys.stderr)

    return VALIDATION_EXIT_CODES[report["classification"]]


def cmd_compat(args: argparse.Namespace) -> int:
    try:
        contract_a = _load_json_object(Path(args.contract_a))
        contract_b = _load_json_object(Path(args.contract_b))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"input read error: {exc}", file=sys.stderr)
        return 64

    try:
        report = evaluate_compat(contract_a, contract_b)
    except ValueError as exc:
        print(f"contract normalization error: {exc}", file=sys.stderr)
        return 64

    if args.schema_check:
        try:
            _maybe_schema_validate(
                report,
                schema_path=Path(__file__).resolve().parent.parent
                / "conformance"
                / "compat_report.schema.json",
            )
        except Exception as exc:  # noqa: BLE001 - deterministic CLI error contract
            print(f"schema validation error: {exc}", file=sys.stderr)
            return 65

    serialized = render_json(report, canonical=not args.pretty)
    _write_output(serialized, Path(args.out) if args.out else None)

    if args.print_hash:
        print(sha256_hex(report), file=sys.stderr)

    return COMPAT_EXIT_CODES[report["classification"]]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eal",
        description="Deterministic EAL validation-only CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_parser = subparsers.add_parser(
        "verify-receipt",
        help="Validate a receipt against one contract and emit a validation report",
    )
    verify_parser.add_argument("--receipt", required=True, help="Path to receipt JSON")
    verify_parser.add_argument("--contract", required=True, help="Path to contract JSON")
    verify_parser.add_argument("--out", help="Optional path for report output")
    verify_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print output JSON instead of canonical compact JSON",
    )
    verify_parser.add_argument(
        "--print-hash",
        action="store_true",
        help="Print report SHA-256 to stderr",
    )
    verify_parser.add_argument(
        "--schema-check",
        action="store_true",
        help="Validate output JSON against conformance schema",
    )
    verify_parser.set_defaults(func=cmd_verify_receipt)

    compat_parser = subparsers.add_parser(
        "compat",
        help="Compare two contracts and emit a compatibility report",
    )
    compat_parser.add_argument("--contract-a", required=True, help="Path to baseline contract")
    compat_parser.add_argument("--contract-b", required=True, help="Path to candidate contract")
    compat_parser.add_argument("--out", help="Optional path for report output")
    compat_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print output JSON instead of canonical compact JSON",
    )
    compat_parser.add_argument(
        "--print-hash",
        action="store_true",
        help="Print report SHA-256 to stderr",
    )
    compat_parser.add_argument(
        "--schema-check",
        action="store_true",
        help="Validate output JSON against conformance schema",
    )
    compat_parser.set_defaults(func=cmd_compat)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
