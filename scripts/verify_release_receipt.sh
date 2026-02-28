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

CONFORMANCE_RUN_ID=""
CONFORMANCE_RUN_URL=""
RELEASE_ARTIFACTS_RUN_ID=""
RELEASE_ARTIFACTS_RUN_URL=""

require_workflow_success() {
  local workflow="$1"
  local prefix="$2"
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

    case "$prefix" in
      conformance)
        CONFORMANCE_RUN_ID="$run_id"
        CONFORMANCE_RUN_URL="$url"
        ;;
      release_artifacts)
        RELEASE_ARTIFACTS_RUN_ID="$run_id"
        RELEASE_ARTIFACTS_RUN_URL="$url"
        ;;
    esac

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

require_workflow_success "conformance" "conformance"
require_workflow_success "release-artifacts" "release_artifacts"

release_json="$(gh release view "$TAG" --repo "$REPO" --json tagName,url,assets)"

required_assets=(
  "verify_run1.txt"
  "verify_run2.txt"
  "verify_diff.txt"
  "vendor_surface_evidence.json"
  "SHA256SUMS.txt"
  "release_receipt.json"
)

for asset in "${required_assets[@]}"; do
  if jq -e --arg name "$asset" '.assets[] | select(.name == $name)' <<<"$release_json" >/dev/null; then
    echo "PASS release.asset.${asset}.present=true"
  else
    echo "FAIL release.asset.${asset}.present=false" >&2
    exit 1
  fi
done

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
gh release download "$TAG" --repo "$REPO" --pattern "release_receipt.json" --dir "$tmp_dir" --clobber >/dev/null
receipt_path="$tmp_dir/release_receipt.json"

if ! jq -e '.schema_version == "eal.release.receipt.v1"' "$receipt_path" >/dev/null; then
  echo "FAIL release_receipt.schema_version.invalid" >&2
  exit 1
fi
if ! jq -e --arg tag "$TAG" --arg repo "$REPO" '.tag == $tag and .repository == $repo' "$receipt_path" >/dev/null; then
  echo "FAIL release_receipt.identity.mismatch" >&2
  exit 1
fi
if ! jq -e '.conformance_run.conclusion == "success" and .release_artifacts_run.conclusion == "success"' "$receipt_path" >/dev/null; then
  echo "FAIL release_receipt.run_conclusions.invalid" >&2
  exit 1
fi
if ! jq -e --arg run_id "$CONFORMANCE_RUN_ID" '.conformance_run.run_id == ($run_id | tonumber)' "$receipt_path" >/dev/null; then
  echo "FAIL release_receipt.conformance_run_id.mismatch" >&2
  exit 1
fi
if ! jq -e --arg run_id "$RELEASE_ARTIFACTS_RUN_ID" '.release_artifacts_run.run_id == ($run_id | tonumber)' "$receipt_path" >/dev/null; then
  echo "FAIL release_receipt.release_artifacts_run_id.mismatch" >&2
  exit 1
fi

declared_hash="$(jq -r '.manifest_c14n_sha256' "$receipt_path")"
computed_hash="$(
  jq 'del(.manifest_c14n_sha256)' "$receipt_path" \
    | jq -cS . \
    | tr -d '\n' \
    | {
        if command -v sha256sum >/dev/null 2>&1; then
          sha256sum | awk '{print $1}'
        else
          shasum -a 256 | awk '{print $1}'
        fi
      }
)"
if [[ "$declared_hash" != "$computed_hash" ]]; then
  echo "FAIL release_receipt.hash.mismatch declared=${declared_hash} computed=${computed_hash}" >&2
  exit 1
fi
echo "PASS release_receipt.hash.match=true"

echo "RELEASE RECEIPT: PASS tag=${TAG} repo=${REPO}"
