"""AAA EAL deterministic validation and compatibility tooling."""

from aaa_eal.core import (
    COMPAT_PRECEDENCE,
    EAL_PRECEDENCE,
    EAL_PROFILE,
    canonical_json_bytes,
    evaluate_compat,
    evaluate_validation,
    sha256_hex,
)

__all__ = [
    "COMPAT_PRECEDENCE",
    "EAL_PRECEDENCE",
    "EAL_PROFILE",
    "canonical_json_bytes",
    "evaluate_compat",
    "evaluate_validation",
    "sha256_hex",
]
