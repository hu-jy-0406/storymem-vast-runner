#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CONFIG=${1:?Usage: run-job.sh /absolute/path/to/config.env}
source "$CONFIG"
: "${STORYMEM_REPO:?}"
: "${STORYMEM_RUN_ROOT:?}"
: "${STORYMEM_BUNDLE:?}"
VENV=${STORYMEM_VENV:-/workspace/envs/storymem}

test -f "$STORYMEM_REPO/run_example.sh"
test -f "$STORYMEM_BUNDLE/generation_queue.jsonl"
test -f "$STORYMEM_RUN_ROOT/MODELS_READY" || {
  echo "Models are not ready. Run scripts/download-models.sh first." >&2; exit 2; }

export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
cd "$STORYMEM_REPO"
exec "$VENV/bin/python" -u "$ROOT/runtime/run_batch.py"
