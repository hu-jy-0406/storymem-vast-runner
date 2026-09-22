from pathlib import Path
import os
import json, time, statistics, subprocess, re
root=Path(os.environ['STORYMEM_RUN_ROOT']).resolve()
queue=[json.loads(x) for x in Path(os.environ['STORYMEM_BUNDLE']).joinpath('generation_queue.jsonl').read_text().splitlines()]
done=[json.loads(p.read_text()) for p in (root/'outputs').glob('*/complete.json')]
shots=sum(len(d['shots']) for d in done)
service=subprocess.run(['supervisorctl','status','storymem-batch'],capture_output=True,text=True)
print(service.stdout.strip() or service.stderr.strip())
print(f'Completed episodes: {len(done)}/{len(queue)}; completed episode shots: {shots}/{sum(e["shot_count"] for e in queue)}')
if done:
 sec=sum(d['elapsed_seconds'] for d in done); rate=sec/shots
 print(f'Measured complete-episode average: {rate:.1f} seconds/shot (includes model loads and keyframe selection)')
 print(f'Estimated time for remaining complete episodes: {(sum(e["shot_count"] for e in queue)-shots)*rate/3600:.2f} hours')
for e in queue:
 out=root/'outputs'/e['episode_id']
 if out.exists() and not (out/'complete.json').exists():
  print('Current:',e['generation_priority'],e['episode_id'])
  print('Written shot files:',sum((out/s['storymem_output_name']).exists() for s in e['shots']),'/',e['shot_count'])
  log=out/'console.log'
  if log.exists():
   with log.open('rb') as f:
    f.seek(max(0,log.stat().st_size-16384));tail=f.read().decode(errors='replace')
   progress=re.findall(r'(\d+)/40 \[[^\r\n]*',tail)
   if progress:print('Latest sampling progress:',progress[-1]+'/40')
   if 'OutOfMemoryError' in tail or 'ChildFailedError' in tail:print('Last attempt failed; inspect log before restarting.')
  print('Log:',log)
