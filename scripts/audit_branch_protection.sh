#!/usr/bin/env bash
set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI required" >&2
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq required" >&2
  exit 1
fi

BRANCH="${1:-main}"
REPO="${2:-}"

if [[ -z "$REPO" ]]; then
  origin_url="$(git config --get remote.origin.url || true)"
  if [[ "$origin_url" =~ github.com[:/]([^/]+/[^/.]+)(\.git)?$ ]]; then
    REPO="${BASH_REMATCH[1]}"
  else
    echo "ERROR: could not infer repo from origin URL" >&2
    echo "Pass explicitly: scripts/audit_branch_protection.sh <branch> <owner/repo>" >&2
    exit 1
  fi
fi

json="$(gh api "repos/$REPO/branches/$BRANCH/protection")"

strict="$(jq -r '.required_status_checks.strict' <<<"$json")"
verify_present="$(jq -r '.required_status_checks.contexts | index("verify") != null' <<<"$json")"
reviews_required="$(jq -r '.required_pull_request_reviews != null' <<<"$json")"
conversation_resolution="$(jq -r '.required_conversation_resolution.enabled' <<<"$json")"
enforce_admins="$(jq -r '.enforce_admins.enabled' <<<"$json")"
linear_history="$(jq -r '.required_linear_history.enabled' <<<"$json")"
allow_force_pushes="$(jq -r '.allow_force_pushes.enabled' <<<"$json")"
allow_deletions="$(jq -r '.allow_deletions.enabled' <<<"$json")"

fail=0

check_eq() {
  local name="$1"
  local actual="$2"
  local expected="$3"
  if [[ "$actual" == "$expected" ]]; then
    echo "PASS $name=$actual"
  else
    echo "FAIL $name expected=$expected actual=$actual"
    fail=1
  fi
}

check_eq "required_status_checks.strict" "$strict" "true"
check_eq "required_status_checks.contexts includes verify" "$verify_present" "true"
check_eq "required_pull_request_reviews configured" "$reviews_required" "false"
check_eq "required_conversation_resolution.enabled" "$conversation_resolution" "true"
check_eq "enforce_admins.enabled" "$enforce_admins" "true"
check_eq "required_linear_history.enabled" "$linear_history" "true"
check_eq "allow_force_pushes.enabled" "$allow_force_pushes" "false"
check_eq "allow_deletions.enabled" "$allow_deletions" "false"

if [[ "$fail" -ne 0 ]]; then
  echo "BRANCH PROTECTION AUDIT: FAIL"
  exit 2
fi

echo "BRANCH PROTECTION AUDIT: PASS"
