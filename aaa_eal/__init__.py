"""AAA EAL deterministic validation and compatibility tooling."""

__version__ = "1.0.1"

from aaa_eal.core import (
    COMPAT_PRECEDENCE,
    EAL_PRECEDENCE,
    EAL_PROFILE,
    canonical_json_bytes,
    evaluate_compat,
    evaluate_temporal_validation,
    evaluate_validation,
    sha256_hex,
)

__all__ = [
    "COMPAT_PRECEDENCE",
    "EAL_PRECEDENCE",
    "EAL_PROFILE",
    "canonical_json_bytes",
    "evaluate_compat",
    "evaluate_temporal_validation",
    "evaluate_validation",
    "sha256_hex",
]
