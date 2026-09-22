import os, torch, torch.distributed as dist
rank=int(os.environ['LOCAL_RANK']);torch.cuda.set_device(rank)
print('PyTorch compile-time NCCL:',torch.cuda.nccl.version(),flush=True)
dist.init_process_group('nccl');n=dist.get_world_size()
# Each destination receives one labeled chunk from every source rank.
x=torch.cat([torch.full((4096,), rank*n+d,device='cuda',dtype=torch.bfloat16) for d in range(n)])
y=torch.empty_like(x);dist.all_to_all_single(y,x)
expected=torch.cat([torch.full((4096,), s*n+rank,device='cuda',dtype=torch.bfloat16) for s in range(n)])
assert torch.equal(y,expected)
a=torch.full((4096,),rank,device='cuda',dtype=torch.float32);b=torch.empty(n*4096,device='cuda')
dist.all_gather_into_tensor(b,a)
assert torch.equal(b,torch.cat([torch.full_like(a,s) for s in range(n)]))
if rank==0:print('PASS: 8-GPU BF16 all_to_all_single and FP32 all_gather_into_tensor',flush=True)
dist.barrier();dist.destroy_process_group()
