#!/usr/bin/env bash
set -euo pipefail

# Bootstrap the code and Python runtime. Run from the cloned runner repository.
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
WORKSPACE=${WORKSPACE:-/workspace}
STORYMEM_REPO=${STORYMEM_REPO:-$WORKSPACE/StoryMem}
RUNTIME_ROOT=${RUNTIME_ROOT:-$WORKSPACE/storymem-runtime}
VENV=${STORYMEM_VENV:-$WORKSPACE/envs/storymem}
SOURCE_COMMIT=052c68d2627a22a95f79dbb4d3376cc30c96f1a3

command -v uv >/dev/null
command -v aria2c >/dev/null
command -v ffmpeg >/dev/null
command -v git >/dev/null

if [[ ! -d "$STORYMEM_REPO/.git" ]]; then
  git clone https://github.com/Kevin-thu/StoryMem.git "$STORYMEM_REPO"
fi
git -C "$STORYMEM_REPO" fetch --depth 1 origin "$SOURCE_COMMIT"
git -C "$STORYMEM_REPO" checkout --detach "$SOURCE_COMMIT"
git -C "$STORYMEM_REPO" apply --check "$ROOT/patches/rtx5090-32gb.patch"
git -C "$STORYMEM_REPO" apply "$ROOT/patches/rtx5090-32gb.patch"

uv venv --python 3.11 "$VENV"
uv pip install --python "$VENV/bin/python" \
  torch==2.7.1+cu128 torchvision==0.22.1+cu128 \
  --index-url https://download.pytorch.org/whl/cu128
uv pip install --python "$VENV/bin/python" \
  -r "$ROOT/runtime/requirements-runtime.txt" \
  -c "$ROOT/runtime/constraints.txt"

# A native sm_120 FlashAttention build is mandatory for RTX 5090. Prefer an
# explicit prebuilt wheel URL to avoid a lengthy compilation on the new host.
FLASH_ATTN_WHEEL_URL=${FLASH_ATTN_WHEEL_URL:-https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.3/flash_attn-2.8.3%2Bcu12torch2.7cxx11abiTRUE-cp311-cp311-linux_x86_64.whl}
uv pip install --python "$VENV/bin/python" "$FLASH_ATTN_WHEEL_URL" --no-deps

mkdir -p "$RUNTIME_ROOT/nccl/lib"
SOURCE_NCCL=$(find /venv/main -path '*/nvidia/nccl/lib/libnccl.so.2' -type f -print -quit 2>/dev/null || true)
if [[ -z "$SOURCE_NCCL" ]]; then
  echo "No compatible NCCL copy found under /venv/main; install a native-sm_120 NCCL 2.28.9+ library first." >&2
  exit 2
fi
cp -f "$SOURCE_NCCL" "$RUNTIME_ROOT/nccl/lib/libnccl.so.2"
sha256sum "$RUNTIME_ROOT/nccl/lib/libnccl.so.2" > "$RUNTIME_ROOT/nccl/SHA256SUMS"

export HF_HOME=${HF_HOME:-$WORKSPACE/.hf_home}
"$VENV/bin/python" - <<'PY'
import clip
clip.load('ViT-B/32', device='cpu')
print('CLIP cache ready')
PY
"$VENV/bin/python" -c 'import torch, flash_attn; print(torch.__version__, torch.version.cuda, flash_attn.__version__)'
echo "Setup complete. Source $ROOT/.env.example after copying it to your job config."
