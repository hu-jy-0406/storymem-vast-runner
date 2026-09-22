#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
: "${STORYMEM_RUN_ROOT:?Set STORYMEM_RUN_ROOT in config.env}"
: "${STORYMEM_REPO:?Set STORYMEM_REPO in config.env}"
: "${HF_HOME:?Set HF_HOME in config.env}"
mkdir -p "$STORYMEM_RUN_ROOT"
cp -n "$ROOT/runtime/model_revisions.json" "$STORYMEM_RUN_ROOT/model_revisions.json"
"${STORYMEM_VENV:-/workspace/envs/storymem}/bin/python" "$ROOT/runtime/download_verified.py"
