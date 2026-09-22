# Tested runtime

This runner was validated on a Vast PyTorch image with 8 x RTX 5090 (32 GB),
host driver 570.181 (CUDA capability 12.8), Python 3.11, and 513 GB RAM.

The runtime uses PyTorch 2.7.1+cu128, torchvision 0.22.1+cu128,
FlashAttention 2.8.3 compiled for CUDA 12 / torch 2.7 / C++11 ABI / Python 3.11,
and a native-sm_120 NCCL 2.28.9 library copied from the base environment.

The source patch is intentionally small and is recorded in
`patches/rtx5090-32gb.patch`. It has three parts:

1. Compute time embeddings after Ulysses sequence sharding, instead of allocating
   the full sequence on every GPU.
2. Offload inactive FSDP local shard references while HPSv3 selects keyframes.
3. Use the same temporary offload while rank 0 decodes VAE frames.

The full 32,760-token time-embedding test reduced this isolated peak allocation
from 6,108,119,040 to 1,411,645,440 bytes. The patched job completed a four-shot
episode at 832x480, 81 frames, 16 fps, using the native StoryMem runner settings.
