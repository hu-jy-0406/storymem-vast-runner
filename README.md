# StoryMem Vast 8x RTX 5090 runner

This repository makes the tested StoryMem deployment reproducible on a Vast
PyTorch instance with 8 x RTX 5090 (32 GB each). It does not include model
weights, prompts, videos, Hugging Face credentials, logs, or the upstream
StoryMem source. It clones the official repository at a pinned commit and
applies a documented RTX 5090 memory patch.

The base inference contract remains the official `run_example.sh` contract:
8 ranks, 832x480, 81 frames, 40 UniPC steps, seed 0, FSDP, Ulysses size 8,
model offload, rank-128 MI2V LoRA, and `max_memory_size=10`.

## Why this wrapper exists

The official A14B pipeline exhausted 32 GB cards in three places even across
eight GPUs: full-sequence time projection, HPSv3 keyframe scoring, and rank-0
VAE decoding. The patch in [patches/rtx5090-32gb.patch](patches/rtx5090-32gb.patch)
shards the time projection before calculating it and temporarily moves inactive
FSDP shard references to CPU while an auxiliary model or VAE runs. Model weights,
sampling settings, prompts, cut flags, and official pipeline calls are unchanged.
Read [docs/TESTED.md](docs/TESTED.md) before using it on a different GPU class.

## Requirements

- Vast PyTorch image, 8 x RTX 5090 / 32 GB or equivalent
- At least 400 GB free filesystem capacity for the roughly 295 GB model set plus outputs
- Python 3.11 and `uv`, `git`, `aria2c`, `ffmpeg`, `unzip`, and Supervisor available
- Hugging Face access to the five model repositories and the dataset

This setup is specific to RTX 5090 / `sm_120`. Do not use an older CUDA wheel or
an NCCL build without native `sm_120` support.

## New-server quick start

Run all commands as root on the new Vast instance.

```bash
cd /workspace
git clone https://github.com/hu-jy-0406/storymem-vast-runner.git
cd storymem-vast-runner

# Authenticate once. Tokens are stored outside this repository.
hf auth login

# Installs the pinned runtime, applies the patch to the official checkout,
# configures native-sm_120 NCCL, and warms the CLIP keyframe cache.
./scripts/setup.sh
```

The setup script defaults to the exact FlashAttention release wheel validated
here. Set `FLASH_ATTN_WHEEL_URL` only when a replacement wheel matches Python
3.11, CUDA 12, torch 2.7, C++11 ABI, and has native `sm_120` kernels.

Download a non-overlapping prompt batch. For example, this rents another server
for ranks 151--200:

```bash
./scripts/download-eec-bench.sh 0150_0200
```

Create a job directory and configuration. Keep each batch in its own job
directory so that retries and output files remain isolated.

```bash
JOB=/workspace/storymem-jobs/0150_0200
mkdir -p "$JOB"
cp .env.example "$JOB/config.env"

# Edit just these paths in $JOB/config.env:
# STORYMEM_RUN_ROOT=$JOB
# STORYMEM_BUNDLE=/workspace/datasets/eec-bench-storymem-400/batches/storymem_inputs_0150_0200
# LD_PRELOAD=/workspace/storymem-runtime/nccl/lib/libnccl.so.2
nano "$JOB/config.env"

source "$JOB/config.env"
./scripts/download-models.sh
```

`download-models.sh` pins every Hugging Face revision, resumes through aria2,
checks each LFS SHA256, and writes `MODELS_READY` only after all files validate.
The first server can download models into `/workspace/StoryMem/models`; servers
do not share that directory unless they use the same mounted volume.

Install and start a managed batch service:

```bash
./scripts/install-supervisor.sh "$JOB/config.env" storymem-0150-0200
supervisorctl start storymem-0150-0200

# Progress and logs
./scripts/status.sh "$JOB/config.env"
tail -f /var/log/portal/storymem-0150-0200.log
```

To run without Supervisor for an ad-hoc foreground test:

```bash
./scripts/run-job.sh "$JOB/config.env"
```

## Batch semantics

The EEC dataset ranges are zero-based and end-exclusive. `0150_0200` means
priority ranks 151--200. Download exactly one `storymem_inputs_<batch>.zip` per
server; do not dispatch the dataset's cumulative `priority_*` lists as a batch.
The native `generation_queue.jsonl` is authoritative. The runner preserves each
story script and cut flag and verifies every completed shot has 81 frames at
832x480 before producing the evaluation concatenation.

Outputs are written under `$STORYMEM_RUN_ROOT/outputs` and evaluation videos
under `$STORYMEM_RUN_ROOT/videos`. On failure, an incomplete episode directory
is renamed with `.interrupted.<timestamp>` before retrying, so old memory frames
cannot contaminate a new run.

## Runtime controls

The environment settings in `config.env` are required for the tested hardware:

- `LD_PRELOAD` selects the native-sm_120 NCCL 2.28.9 copy.
- `NCCL_CUMEM_HOST_ENABLE=0` avoids a shared-memory issue in this container.
- `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` lowers allocator pressure.
- `CUBLAS_WORKSPACE_CONFIG=:16:8` keeps the cuBLAS workspace small.

The runner intentionally sets Hugging Face and Transformers offline during
generation. Ensure `MODELS_READY` exists before starting a batch.

## Reproducibility record

- Official source: `Kevin-thu/StoryMem` commit `052c68d2627a22a95f79dbb4d3376cc30c96f1a3`
- Model revisions: [runtime/model_revisions.json](runtime/model_revisions.json)
- Dataset used for validation: `BlueSourceJY/eec-bench-storymem-400`, revision `b2a1c86842f3e5b7f7aed53ab0091c0689945efd`
- Validated source patch: [patches/rtx5090-32gb.patch](patches/rtx5090-32gb.patch)

The upstream StoryMem source is released under the S-Lab License 1.0, including
non-commercial restrictions. This repository contains only an integration patch
and operational scripts; comply with the upstream license and model licenses.
