#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <tag> [owner/repo]" >&2
  exit 1
fi

TAG="$1"
REPO="${2:-}"

if [[ -z "$REPO" ]]; then
  REPO="$(gh repo view --json nameWithOwner --jq '.nameWithOwner')"
fi

if [[ ! "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+([-.][A-Za-z0-9]+)?$ ]]; then
  echo "ERROR: tag must start with vMAJOR.MINOR.PATCH (optional prerelease suffix)" >&2
  exit 2
fi

TIMEOUT="${RELEASE_RECEIPT_TIMEOUT_SECONDS:-600}"
POLL="${RELEASE_RECEIPT_POLL_SECONDS:-5}"
DEADLINE=$((SECONDS + TIMEOUT))

require_workflow_success() {
  local workflow="$1"
  local run_json run_id status conclusion url

  while true; do
    run_json="$(gh run list \
      --repo "$REPO" \
      --workflow "$workflow" \
      --branch "$TAG" \
      --event push \
      --limit 1 \
      --json databaseId,status,conclusion,url 2>/dev/null || true)"

    run_id="$(jq -r '.[0].databaseId // empty' <<<"$run_json")"

    if [[ -z "$run_id" ]]; then
      if (( SECONDS >= DEADLINE )); then
        echo "FAIL workflow.${workflow}.run_present=false" >&2
        return 1
      fi
      sleep "$POLL"
      continue
    fi

    status="$(jq -r '.[0].status' <<<"$run_json")"
    conclusion="$(jq -r '.[0].conclusion // ""' <<<"$run_json")"
    url="$(jq -r '.[0].url // ""' <<<"$run_json")"

    if [[ "$status" != "completed" ]]; then
      if (( SECONDS >= DEADLINE )); then
        echo "FAIL workflow.${workflow}.status=${status} timeout=true run_id=${run_id} url=${url}" >&2
        return 1
      fi
      sleep "$POLL"
      continue
    fi

    if [[ "$conclusion" != "success" ]]; then
      echo "FAIL workflow.${workflow}.conclusion=${conclusion} run_id=${run_id} url=${url}" >&2
      return 1
    fi

    echo "PASS workflow.${workflow}.conclusion=success run_id=${run_id} url=${url}"
    return 0
  done
}

release_json="$(gh release view "$TAG" --repo "$REPO" --json tagName,url,assets 2>/dev/null || true)"
while [[ -z "$release_json" ]]; do
  if (( SECONDS >= DEADLINE )); then
    echo "FAIL release.present=false tag=${TAG} timeout=true" >&2
    exit 1
  fi
  sleep "$POLL"
  release_json="$(gh release view "$TAG" --repo "$REPO" --json tagName,url,assets 2>/dev/null || true)"
done

echo "PASS release.present=true tag=${TAG}"

require_workflow_success "conformance"
require_workflow_success "release-artifacts"

required_assets=(
  "verify_run1.txt"
  "verify_run2.txt"
  "verify_diff.txt"
  "SHA256SUMS.txt"
)

for asset in "${required_assets[@]}"; do
  if jq -e --arg name "$asset" '.assets[] | select(.name == $name)' <<<"$release_json" >/dev/null; then
    echo "PASS release.asset.${asset}.present=true"
  else
    echo "FAIL release.asset.${asset}.present=false" >&2
    exit 1
  fi
done

echo "RELEASE RECEIPT: PASS tag=${TAG} repo=${REPO}"
