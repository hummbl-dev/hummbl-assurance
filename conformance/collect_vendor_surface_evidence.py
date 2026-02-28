#!/usr/bin/env python3
"""Collect vendor surface evidence for experimental feature governance."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class SurfaceSpec:
    vendor_id: str
    surface_id: str
    binary: str | None
    version_cmd: tuple[str, ...] | None
    feature_cmd: tuple[str, ...] | None


SURFACES: tuple[SurfaceSpec, ...] = (
    SurfaceSpec(
        vendor_id="openai",
        surface_id="codex_cli",
        binary="codex",
        version_cmd=("codex", "--version"),
        feature_cmd=("codex", "features", "list"),
    ),
    SurfaceSpec(
        vendor_id="anthropic",
        surface_id="claude_code_cli",
        binary="claude",
        version_cmd=("claude", "--version"),
        feature_cmd=("claude", "--help"),
    ),
    SurfaceSpec(
        vendor_id="google",
        surface_id="gemini_cli",
        binary="gemini",
        version_cmd=("gemini", "--version"),
        feature_cmd=("gemini", "--help"),
    ),
    SurfaceSpec(
        vendor_id="openrouter",
        surface_id="openrouter_api",
        binary=None,
        version_cmd=None,
        feature_cmd=None,
    ),
    SurfaceSpec(
        vendor_id="ollama",
        surface_id="ollama_local",
        binary="ollama",
        version_cmd=("ollama", "--version"),
        feature_cmd=("ollama", "--help"),
    ),
)

FEATURE_KEYWORDS = ("experimental", "beta", "preview")
OPTION_PATTERN = re.compile(r"--[a-zA-Z0-9][a-zA-Z0-9_-]*")
CODEX_FEATURE_PATTERN = re.compile(r"^([a-zA-Z0-9][a-zA-Z0-9_-]*)\s+.+\s+(true|false)$")
OLLAMA_CLIENT_VERSION_PATTERN = re.compile(r"client version is ([0-9A-Za-z._-]+)", re.IGNORECASE)


def _run_command(command: tuple[str, ...]) -> tuple[int, str]:
    run = subprocess.run(command, capture_output=True, text=True, check=False)
    output = run.stdout.strip() if run.stdout.strip() else run.stderr.strip()
    return run.returncode, output


def _parse_codex_inventory(output: str) -> list[str]:
    features: list[str] = []
    for line in output.splitlines():
        match = CODEX_FEATURE_PATTERN.match(line.strip())
        if match:
            features.append(match.group(1))
    return sorted(set(features))


def _parse_help_inventory(output: str) -> list[str]:
    discovered: set[str] = set()
    for raw_line in output.splitlines():
        line = raw_line.strip()
        line_lower = line.lower()
        if not line:
            continue
        if not any(keyword in line_lower for keyword in FEATURE_KEYWORDS):
            continue
        for option in OPTION_PATTERN.findall(line):
            if option.startswith("--"):
                discovered.add(option[2:])
    return sorted(discovered)


def _extract_version(spec: SurfaceSpec, exit_code: int, output: str) -> tuple[str, str]:
    if exit_code != 0:
        return "", f"version probe failed for {spec.binary} exit_code={exit_code}"

    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return "", f"version probe returned empty output for {spec.binary}"

    if spec.vendor_id == "ollama" and spec.surface_id == "ollama_local":
        for line in lines:
            match = OLLAMA_CLIENT_VERSION_PATTERN.search(line)
            if match:
                suffix = " (daemon_unreachable)" if any("could not connect" in raw.lower() for raw in lines) else ""
                return f"ollama-cli {match.group(1)}{suffix}", ""
        return "", "unable to parse ollama client version from probe output"

    for line in lines:
        if line.lower().startswith(("warning:", "error:")):
            continue
        return line, ""

    return "", f"version probe output for {spec.binary} did not contain a usable version line"


def _collect_surface(spec: SurfaceSpec) -> dict[str, object]:
    key = f"{spec.vendor_id}/{spec.surface_id}"
    report: dict[str, object] = {
        "vendor_id": spec.vendor_id,
        "surface_id": spec.surface_id,
        "available": False,
        "audited_version": "",
        "feature_inventory": [],
        "notes": "",
    }

    if spec.vendor_id == "openrouter" and spec.surface_id == "openrouter_api":
        token_present = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
        report["available"] = token_present
        report["notes"] = (
            "OPENROUTER_API_KEY present; API surface requires out-of-band feature inventory curation."
            if token_present
            else "OPENROUTER_API_KEY not set; API surface probe unavailable."
        )
        return report

    if spec.binary is None:
        report["notes"] = f"{key} has no binary probe configured."
        return report

    binary_path = shutil.which(spec.binary)
    if binary_path is None:
        report["notes"] = f"binary {spec.binary!r} not found in PATH."
        return report

    report["available"] = True

    if spec.version_cmd is not None:
        code, output = _run_command(spec.version_cmd)
        version, note = _extract_version(spec, code, output)
        if version:
            report["audited_version"] = version
        if note:
            report["notes"] = note

    inventory: list[str] = []
    if spec.feature_cmd is not None:
        code, output = _run_command(spec.feature_cmd)
        if code == 0 and output:
            if spec.vendor_id == "openai" and spec.surface_id == "codex_cli":
                inventory = _parse_codex_inventory(output)
            else:
                inventory = _parse_help_inventory(output)
        elif not report["notes"]:
            report["notes"] = f"feature probe failed for {spec.binary} exit_code={code}"

    report["feature_inventory"] = inventory
    if not report["notes"]:
        report["notes"] = "probe completed"
    return report


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON root must be object")
    return payload


def _sync_gate(gate: dict[str, object], probe_reports: list[dict[str, object]]) -> tuple[dict[str, object], list[str]]:
    vendors = gate.get("vendors")
    if not isinstance(vendors, list):
        raise ValueError("gate.vendors must be array")

    by_key = {
        (str(item.get("vendor_id", "")), str(item.get("surface_id", ""))): item
        for item in vendors
        if isinstance(item, dict)
    }

    updates: list[str] = []
    for report in probe_reports:
        key = (str(report["vendor_id"]), str(report["surface_id"]))
        vendor = by_key.get(key)
        if vendor is None:
            continue

        audited_version = str(report.get("audited_version", "")).strip()
        current_audited_version = str(vendor.get("audited_version", "")).strip()
        if audited_version and (
            not current_audited_version
            or current_audited_version.lower().startswith("warning:")
        ):
            vendor["audited_version"] = audited_version
            updates.append(f"{key[0]}/{key[1]} audited_version")

        feature_inventory = report.get("feature_inventory")
        if isinstance(feature_inventory, list):
            cleaned = sorted({str(item).strip() for item in feature_inventory if str(item).strip()})
            current = vendor.get("feature_inventory")
            current_list = current if isinstance(current, list) else []
            current_clean = sorted({str(item).strip() for item in current_list if str(item).strip()})
            if cleaned and not current_clean:
                vendor["feature_inventory"] = cleaned
                updates.append(f"{key[0]}/{key[1]} feature_inventory")

    gate["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return gate, updates


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect vendor surface evidence")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("conformance/vendor_surface_evidence.latest.json"),
        help="Output path for probe evidence JSON",
    )
    parser.add_argument(
        "--update-gate",
        action="store_true",
        help="Update vendor gate artifact with discovered audited_version/feature_inventory values",
    )
    parser.add_argument(
        "--gate",
        type=Path,
        default=Path("conformance/vendor_experimental_feature_gates.json"),
        help="Vendor gate artifact path (used with --update-gate)",
    )
    args = parser.parse_args()

    reports = [_collect_surface(spec) for spec in SURFACES]
    evidence = {
        "schema_version": "eal.vendor.surface.evidence.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "surfaces": reports,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"PASS vendor_surface_evidence.written path={args.out}")

    for report in reports:
        key = f"{report['vendor_id']}/{report['surface_id']}"
        available = str(report["available"]).lower()
        inv_len = len(report.get("feature_inventory", []))
        print(f"PASS vendor_surface_evidence.{key}.available={available}")
        print(f"PASS vendor_surface_evidence.{key}.feature_inventory_count={inv_len}")

    if args.update_gate:
        gate_payload = _load_json(args.gate)
        gate_payload, updates = _sync_gate(gate_payload, reports)
        args.gate.write_text(json.dumps(gate_payload, indent=2) + "\n", encoding="utf-8")
        if updates:
            print(f"PASS vendor_surface_evidence.gate_updates={len(updates)}")
            for item in updates:
                print(f"PASS vendor_surface_evidence.gate_update.{item}=applied")
        else:
            print("PASS vendor_surface_evidence.gate_updates=0")

    return 0


if __name__ == "__main__":
    sys.exit(main())
