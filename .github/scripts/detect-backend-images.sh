#!/usr/bin/env bash

set -euo pipefail

base_sha=$1
head_sha=$2

all_images='[{"image":"svitlo-power-back-end","dockerfile":"back-end/Dockerfile"},{"image":"svitlo-power-sse-back-end","dockerfile":"sse-back-end/Dockerfile"},{"image":"svitlo-power-grid-reporter","dockerfile":"grid-reporter/Dockerfile"}]'

if [[ "$base_sha" =~ ^0+$ ]] || ! git cat-file -e "${base_sha}^{commit}" 2>/dev/null; then
  echo "matrix={\"include\":${all_images}}"
  exit 0
fi

changed_paths=$(git diff --name-only "$base_sha" "$head_sha")

if grep -Eq '^(shared/|docker-compose|\.github/workflows/backend-build\.yml$|\.github/scripts/detect-backend-images\.sh$|\.github/actions/(compute-image-version|cleanup-old-images)/)' <<<"$changed_paths"; then
  echo "matrix={\"include\":${all_images}}"
  exit 0
fi

images=()
grep -q '^back-end/' <<<"$changed_paths" && images+=('{"image":"svitlo-power-back-end","dockerfile":"back-end/Dockerfile"}')
grep -q '^sse-back-end/' <<<"$changed_paths" && images+=('{"image":"svitlo-power-sse-back-end","dockerfile":"sse-back-end/Dockerfile"}')
grep -q '^grid-reporter/' <<<"$changed_paths" && images+=('{"image":"svitlo-power-grid-reporter","dockerfile":"grid-reporter/Dockerfile"}')

matrix=$(IFS=,; echo "${images[*]}")
echo "matrix={\"include\":[${matrix}]}"