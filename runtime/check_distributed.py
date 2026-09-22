import os, torch, torch.distributed as dist
from flash_attn import flash_attn_func, flash_attn_varlen_func
rank=int(os.environ['LOCAL_RANK']); torch.cuda.set_device(rank)
print(f'Rank {rank}: CUDA ready; initializing process group',flush=True)
dist.init_process_group('nccl')
print(f'Rank {rank}: process group ready; checking all_reduce',flush=True)
x=torch.tensor([rank+1.],device='cuda'); dist.all_reduce(x)
world=dist.get_world_size()
assert x.item()==world*(world+1)/2,x
print(f'Rank {rank}: all_reduce OK; checking FlashAttention',flush=True)
q=torch.randn(1,256,40,128,device='cuda',dtype=torch.bfloat16)
y=flash_attn_func(q,q,q)
assert torch.isfinite(y).all()
cu=torch.tensor([0,256],device='cuda',dtype=torch.int32)
z=flash_attn_varlen_func(q.flatten(0,1),q.flatten(0,1),q.flatten(0,1),cu,cu,256,256)
assert torch.isfinite(z).all() and torch.allclose(y.flatten(0,1),z,atol=0.03,rtol=0.03)
if rank==0:
 print(f'PASS: {world}-GPU NCCL all_reduce; flash-attn dense and varlen BF16 head_dim128 on all GPUs',flush=True)
 print('PyTorch compile-time NCCL:',torch.cuda.nccl.version(),flush=True)
 print('Torch:',torch.__version__,'CUDA:',torch.version.cuda,'ABI:',torch._C._GLIBCXX_USE_CXX11_ABI,flush=True)
dist.barrier(); dist.destroy_process_group()
