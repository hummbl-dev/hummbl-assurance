#!/usr/bin/env python3
"""Verify AAA-TVS-V1 test vectors against aaa_eal.core canonicalization.

Validates:
- TV-A1: Basic deterministic canonicalization
- TV-A2: Whitespace stability (implicit via TV-A1 canonical match)
- TV-A3: Nested object ordering
- TV-A4: Replay determinism (run TV-A1 twice, compare)
- TV-A5: Missing required field (schema-level failure)
- TV-F2: Governance version mismatch

Usage:
    python3 spec/verify_test_vectors.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add repo root to path for aaa_eal import
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from aaa_eal.core import canonical_json_bytes, sha256_hex  # noqa: E402

FIXTURES = repo_root / "spec" / "fixtures"
PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    status = "PASS" if condition else "FAIL"
    if not condition:
        FAIL += 1
    else:
        PASS += 1
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{status}] {name}{suffix}")


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def load_canonical(path: Path) -> bytes:
    """Load canonical form (no trailing newline)."""
    return path.read_bytes().rstrip(b"\n").rstrip(b"\r")


def test_tv_a1() -> None:
    """TV-A1: Basic Deterministic Canonicalization."""
    print("\nTV-A1: Basic Deterministic Canonicalization")
    intent = load_json(FIXTURES / "tv-a1.intent.json")
    expected_canonical = load_canonical(FIXTURES / "tv-a1.canonical.json")
    expected_sha256 = load_text(FIXTURES / "tv-a1.sha256.txt")

    actual_canonical = canonical_json_bytes(intent)
    actual_sha256 = sha256_hex(intent)

    check("Canonical output matches", actual_canonical == expected_canonical,
          f"got {len(actual_canonical)} bytes")
    check("SHA-256 matches", actual_sha256 == expected_sha256,
          f"{actual_sha256[:16]}...")


def test_tv_a2() -> None:
    """TV-A2: Whitespace Stability (same data with extra whitespace)."""
    print("\nTV-A2: Whitespace Stability")
    # Parse TV-A1 input with whitespace variations -- JSON parse normalizes this
    raw = '  { "action" :  "deploy" , "authority":"human","parameters" : { "env" : "prod" },"intent_id":"abc-123","version":"1.0","governance_version":"v1.0" }  '
    intent = json.loads(raw)
    expected_canonical = load_canonical(FIXTURES / "tv-a1.canonical.json")
    expected_sha256 = load_text(FIXTURES / "tv-a1.sha256.txt")

    actual_canonical = canonical_json_bytes(intent)
    actual_sha256 = sha256_hex(intent)

    check("Canonical output matches despite whitespace", actual_canonical == expected_canonical)
    check("SHA-256 matches despite whitespace", actual_sha256 == expected_sha256)


def test_tv_a3() -> None:
    """TV-A3: Nested Object Ordering."""
    print("\nTV-A3: Nested Object Ordering")
    intent = load_json(FIXTURES / "tv-a3.intent.json")
    expected_canonical = load_canonical(FIXTURES / "tv-a3.canonical.json")
    expected_sha256 = load_text(FIXTURES / "tv-a3.sha256.txt")

    actual_canonical = canonical_json_bytes(intent)
    actual_sha256 = sha256_hex(intent)

    check("Canonical output matches (nested sort)", actual_canonical == expected_canonical,
          f"got {len(actual_canonical)} bytes")
    check("SHA-256 matches", actual_sha256 == expected_sha256)


def test_tv_a4() -> None:
    """TV-A4: Replay Determinism (same input twice -> same output)."""
    print("\nTV-A4: Replay Determinism")
    intent = load_json(FIXTURES / "tv-a1.intent.json")

    run1_canonical = canonical_json_bytes(intent)
    run1_sha256 = sha256_hex(intent)

    run2_canonical = canonical_json_bytes(intent)
    run2_sha256 = sha256_hex(intent)

    check("Canonical output identical across runs", run1_canonical == run2_canonical)
    check("SHA-256 identical across runs", run1_sha256 == run2_sha256)


def test_tv_a5() -> None:
    """TV-A5: Missing required field (authority) -- structural check."""
    print("\nTV-A5: Failure Precedence (missing field)")
    intent = load_json(FIXTURES / "tv-a5.intent.json")

    check("'authority' field is absent", "authority" not in intent)

    # Canonicalization still works (it operates on whatever dict is given)
    # but a schema validator would reject this
    canonical1 = canonical_json_bytes(intent)
    canonical2 = canonical_json_bytes(intent)
    check("Canonical output deterministic even for invalid input",
          canonical1 == canonical2)


def test_tv_f2() -> None:
    """TV-F2: Governance Version Mismatch."""
    print("\nTV-F2: Governance Version Mismatch")
    intent = load_json(FIXTURES / "tv-f2.intent.json")

    check("governance_version is v2.0", intent.get("governance_version") == "v2.0",
          "mismatch against v1.x pin expected")

    # Canonicalization is still deterministic
    canonical1 = canonical_json_bytes(intent)
    canonical2 = canonical_json_bytes(intent)
    check("Canonical output deterministic for mismatched governance version",
          canonical1 == canonical2)


def main() -> None:
    print("=" * 60)
    print("AAA-TVS-V1 Test Vector Verification")
    print("=" * 60)

    test_tv_a1()
    test_tv_a2()
    test_tv_a3()
    test_tv_a4()
    test_tv_a5()
    test_tv_f2()

    print()
    print("=" * 60)
    print(f"Results: {PASS} passed, {FAIL} failed")
    print("=" * 60)

    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
