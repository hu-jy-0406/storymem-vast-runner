from pathlib import Path
import os
import json,re
root=Path(os.environ['STORYMEM_RUN_ROOT']).resolve()
manifest=json.loads((root/'verified-download-manifest.json').read_text())
large=[f for f in manifest if f['sha256']]
events=[json.loads(x) for x in (root/'verified-download-events.jsonl').read_text().splitlines()]
done={(x['repo'],x['file']) for x in events if x['event']=='large_file_verified'}
started={(x['repo'],x['file']) for x in events if x['event']=='large_file_start'}
completed=sum(f['size'] for f in large if (f['repo'],f['file']) in done)
total=sum(f['size'] for f in large)
print(f'Verified model weights: {len(done)}/{len(large)} files, {completed/1e9:.2f}/{total/1e9:.2f} GB')
rate=0.; estimated=completed
for f in large:
 k=(f['repo'],f['file'])
 if k in done or k not in started:continue
 p=root/('range-'+f['repo'].split('/')[-1]+'-'+f['file'].replace('/','_')+'.log')
 if not p.exists():continue
 lines=p.read_text(errors='replace').splitlines()
 matches=[x for x in lines if re.search(r'\((\d+)%\)',x)]
 if matches:
  line=matches[-1]; pct=int(re.search(r'\((\d+)%\)',line)[1]);estimated+=f['size']*pct/100
  m=re.search(r'DL:([\d.]+)([KMG])iB',line)
  if m:rate+=float(m[1])*{'K':1024,'M':1024**2,'G':1024**3}[m[2]]
  print(f'{f["repo"].split("/")[-1]}/{f["file"]}: {line}')
print(f'Approx. downloaded including unverified partial files: {estimated/1e9:.1f} GB; current aggregate speed: {rate/1e6:.1f} MB/s')
if rate:print(f'Approx. remaining download time at this instantaneous speed: {(total-estimated)/rate/60:.0f} minutes (variable; excludes install and generation)')
