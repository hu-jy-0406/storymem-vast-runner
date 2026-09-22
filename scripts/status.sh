#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CONFIG=${1:?Usage: status.sh /absolute/path/to/config.env}
source "$CONFIG"
exec "${STORYMEM_VENV:-/workspace/envs/storymem}/bin/python" "$ROOT/runtime/status.py"
