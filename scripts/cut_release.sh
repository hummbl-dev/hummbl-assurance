#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 vMAJOR.MINOR.PATCH" >&2
  exit 1
fi

TAG="$1"

if [[ ! "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "ERROR: tag must match vMAJOR.MINOR.PATCH" >&2
  exit 2
fi

current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$current_branch" != "main" ]]; then
  echo "ERROR: releases must be cut from main (current: $current_branch)" >&2
  exit 3
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: working tree is not clean" >&2
  exit 4
fi

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "ERROR: tag already exists locally: $TAG" >&2
  exit 5
fi
if git ls-remote --tags origin "$TAG" | grep -q "$TAG"; then
  echo "ERROR: tag already exists on origin: $TAG" >&2
  exit 6
fi

echo "Running required checks..."
make verify
make verify-repeat
make protection-audit

echo "Creating annotated tag: $TAG"
git tag -a "$TAG" -m "release $TAG"

echo "Pushing tag to origin"
git push origin "$TAG"

echo "Release tag pushed: $TAG"
