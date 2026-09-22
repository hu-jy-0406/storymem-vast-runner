#!/usr/bin/env bash
set -euo pipefail
BATCH_ID=${1:?Usage: download-eec-bench.sh 0150_0200 [dataset-root]}
DATASET_ROOT=${2:-/workspace/datasets/eec-bench-storymem-400}
ARCHIVE=batches/storymem_inputs_${BATCH_ID}.zip
mkdir -p "$DATASET_ROOT/batches"
hf download BlueSourceJY/eec-bench-storymem-400 \
  "$ARCHIVE" "$ARCHIVE.sha256" --repo-type dataset --local-dir "$DATASET_ROOT"
cd "$DATASET_ROOT/batches"
sha256sum -c "storymem_inputs_${BATCH_ID}.zip.sha256"
unzip -n "storymem_inputs_${BATCH_ID}.zip"
python "storymem_inputs_${BATCH_ID}/verify_bundle.py"
echo "Dataset batch ready: $DATASET_ROOT/batches/storymem_inputs_${BATCH_ID}"
