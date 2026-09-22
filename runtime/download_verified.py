"""Resumable downloads of fixed official model revisions, validated against LFS SHA256."""
import os, json, subprocess, time, hashlib, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from filelock import FileLock
from huggingface_hub import HfApi, hf_hub_url, hf_hub_download
from huggingface_hub._local_folder import get_local_download_paths
ROOT=Path(os.environ['STORYMEM_RUN_ROOT']).resolve()
MODELS=Path(os.environ['STORYMEM_REPO']).resolve()/'models'
CACHE=Path(os.environ.get('HF_HOME', ROOT.parent/'.hf_home'))/'hub'
INV=json.loads((ROOT/'model_revisions.json').read_text())
loglock=threading.Lock()
def event(kind,**kw):
 row={'time':time.time(),'event':kind,**kw}
 with loglock:
  print(json.dumps(row),flush=True)
  with (ROOT/'verified-download-events.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
def sha256(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def resumable_transfer(command, output, repo, filename):
 # CDN connections can disappear without aria2 replenishing the full split count.
 # Refresh long-lived transfers, preserving the control file and verified pieces.
 for attempt in range(1,21):
  process=subprocess.Popen(command,stdout=output,stderr=subprocess.STDOUT)
  try:
   code=process.wait(timeout=600)
  except subprocess.TimeoutExpired:
   process.terminate()
   try: code=process.wait(timeout=30)
   except subprocess.TimeoutExpired:
    process.kill();code=process.wait()
   event('transfer_refresh',repo=repo,file=filename,attempt=attempt)
  if code==0:return
  event('transfer_retry',repo=repo,file=filename,attempt=attempt,returncode=code)
  time.sleep(5)
 raise RuntimeError(f'Transfer exhausted retries: {repo}/{filename}')
def download(t):
 repo,rev,f=t; filename=f.rfilename
 assert '..' not in Path(filename).parts and not Path(filename).is_absolute()
 local_mode=repo.startswith(('Wan-AI/','Kevin-thu/'))
 local=MODELS/repo.split('/')[-1]
 storage=CACHE/('models--'+repo.replace('/','--'))
 if not f.lfs:
  for attempt in range(5):
   try:
    p=hf_hub_download(repo,filename,revision=rev,local_dir=local if local_mode else None)
    event('small_file_complete',repo=repo,file=filename)
    return
   except Exception:
    if attempt==4:raise
    time.sleep(5*(attempt+1))
 sha=f.lfs.sha256
 if local_mode:
  paths=get_local_download_paths(local,filename); dest=paths.file_path; lock=paths.lock_path
  temp=local/'.range-downloads'/Path(filename).parent
 else:
  dest=storage/'blobs'/sha; lock=CACHE/'.locks'/storage.name/(sha+'.lock')
  temp=storage/'.range-downloads'/Path(filename).parent
 lock.parent.mkdir(parents=True,exist_ok=True);dest.parent.mkdir(parents=True,exist_ok=True);temp.mkdir(parents=True,exist_ok=True)
 with FileLock(lock):
  valid=dest.exists() and dest.stat().st_size==f.size and sha256(dest)==sha
  if not valid:
   event('large_file_start',repo=repo,file=filename,bytes=f.size)
   log=ROOT/('range-'+repo.split('/')[-1]+'-'+filename.replace('/','_')+'.log')
   with log.open('a') as output:
    resumable_transfer(['aria2c','--continue=true','--max-connection-per-server=16','--split=16','--min-split-size=1M','--lowest-speed-limit=32K','--max-tries=20','--retry-wait=5','--timeout=60','--summary-interval=60','--console-log-level=warn','--auto-file-renaming=false','--allow-overwrite=true','--file-allocation=none','--auto-save-interval=15',f'--checksum=sha-256={sha}',f'--dir={temp}',f'--out={Path(filename).name}',hf_hub_url(repo,filename,revision=rev)],output,repo,filename)
   staged=temp/Path(filename).name
   assert staged.stat().st_size==f.size
   staged.replace(dest)
  if local_mode:
   paths.metadata_path.write_text(f'{rev}\n{sha}\n{time.time()}\n')
  else:
   ptr=storage/'snapshots'/rev/filename;ptr.parent.mkdir(parents=True,exist_ok=True)
   if not ptr.exists():ptr.symlink_to(os.path.relpath(dest,ptr.parent))
  event('large_file_verified',repo=repo,file=filename,bytes=f.size,sha256=sha,reused=valid)

# Prioritize the main base models while auxiliary weights use the same pool.
tasks=[]
for repo in ['Kevin-thu/StoryMem','MizzenAI/HPSv3','Qwen/Qwen2-VL-7B-Instruct','Wan-AI/Wan2.2-T2V-A14B','Wan-AI/Wan2.2-I2V-A14B']:
 rev=next(r['revision'] for r in INV if r['repo']==repo)
 info=HfApi().model_info(repo,revision=rev,files_metadata=True)
 files=info.siblings
 if repo=='MizzenAI/HPSv3':files=[f for f in files if f.rfilename=='HPSv3.safetensors']
 if repo=='Qwen/Qwen2-VL-7B-Instruct':files=[f for f in files if not f.rfilename.endswith(('.bin','.pt'))]
 tasks += [(repo,rev,f) for f in files]
(ROOT/'verified-download-manifest.json').write_text(json.dumps([{'repo':r,'revision':rev,'file':f.rfilename,'size':f.size,'sha256':f.lfs.sha256 if f.lfs else None} for r,rev,f in tasks],indent=2))
with ThreadPoolExecutor(max_workers=24) as pool:
 futures=[pool.submit(download,t) for t in tasks]
 for future in as_completed(futures):future.result()
for r in INV:
 storage=CACHE/('models--'+r['repo'].replace('/','--'))
 if r['repo'] in ['MizzenAI/HPSv3','Qwen/Qwen2-VL-7B-Instruct']:
  (storage/'refs').mkdir(parents=True,exist_ok=True)
  (storage/'refs'/'main').write_text(r['revision'])
(ROOT/'model_revisions.json').write_text(json.dumps({r['repo']:r['revision'] for r in INV},indent=2))
(ROOT/'MODELS_READY').write_text(time.ctime()+'\n')
event('all_models_verified',files=len(tasks))
