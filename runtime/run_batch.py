"""Dispatch the official StoryMem runner one episode at a time."""
from pathlib import Path
import json, subprocess, time, shutil, os
ROOT=Path(os.environ['STORYMEM_RUN_ROOT']).resolve()
REPO=Path(os.environ['STORYMEM_REPO']).resolve()
BUNDLE=Path(os.environ['STORYMEM_BUNDLE']).resolve()
OUTPUT=ROOT/'outputs'; OUTPUT.mkdir(exist_ok=True)
DELIVERY=ROOT/'videos'; DELIVERY.mkdir(exist_ok=True)
QUEUE=[json.loads(x) for x in (BUNDLE/'generation_queue.jsonl').read_text().splitlines()]
assert QUEUE, 'generation_queue.jsonl is empty'
assert all(e['shot_count']==len(e['shots']) for e in QUEUE)
assert len({e['generation_priority'] for e in QUEUE})==len(QUEUE)

def event(kind, **kw):
    row={'time':time.time(),'event':kind,**kw}
    print(json.dumps(row),flush=True)
    with (ROOT/'events.jsonl').open('a') as f: f.write(json.dumps(row)+'\n')

def probe(p):
    r=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_entries','stream=width,height,nb_read_frames,r_frame_rate','-of','json',str(p)],capture_output=True,text=True,check=True)
    return json.loads(r.stdout)['streams'][0]

for entry in QUEUE:
    eid=entry['episode_id']; out=OUTPUT/eid
    if (out/'complete.json').exists():
        continue
    # Restart an incomplete episode from clean memory, preserving the failed attempt.
    if out.exists():
        out.rename(out.with_name(eid+'.interrupted.'+str(int(time.time()))))
    out.mkdir()
    start=time.time(); event('episode_start',episode_id=eid,priority=entry['generation_priority'],shots=entry['shot_count'])
    script=(REPO/'run_example.sh').read_text()
    script=script.replace('OUTPUT_PATH=results/daiyu',f'OUTPUT_PATH={out}')
    script=script.replace('./story/daiyu.json',str(BUNDLE/entry['story_script_path']))
    script=script.replace('pipeline.py \\',f'pipeline.py --log_file {out}/pipeline.log \\')
    script='#!/bin/bash\nset -euo pipefail\n'+script+'\n'
    runner=out/'official_run.sh'; runner.write_text(script)
    (out/'assignment.json').write_text(json.dumps(entry,indent=2))
    shutil.copy2(BUNDLE/entry['story_script_path'],out/'story_script.json')
    with (out/'console.log').open('w') as log:
        ret=subprocess.run(['bash',str(runner)],cwd=REPO,stdout=log,stderr=subprocess.STDOUT)
    if ret.returncode:
        event('episode_failed',episode_id=eid,returncode=ret.returncode)
        raise SystemExit(ret.returncode)
    checks={}
    for shot in entry['shots']:
        p=out/shot['storymem_output_name']; checks[p.name]=probe(p)
        assert int(checks[p.name]['nb_read_frames'])==81,checks
        assert checks[p.name]['width']==832 and checks[p.name]['height']==480,checks
    # Deliver only mapped narrative shots. Official pipeline also concatenates motion_frames.mp4.
    concat=out/'evaluation_concat.txt'
    concat.write_text(''.join(f"file '{out/s['storymem_output_name']}'\n" for s in entry['shots']))
    dest=DELIVERY/f'{entry["generation_priority"]:03d}_{eid}.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','concat','-safe','0','-i',str(concat),'-c','copy','-y',str(dest)],check=True)
    result={'episode_id':eid,'priority':entry['generation_priority'],'elapsed_seconds':time.time()-start,'shots':checks,'video':str(dest),'finished':time.time()}
    (out/'complete.json.tmp').write_text(json.dumps(result,indent=2))
    (out/'complete.json.tmp').replace(out/'complete.json')
    event('episode_complete',**result)
event('batch_complete',episodes=len(QUEUE))
(ROOT/'COMPLETE').write_text(time.ctime()+'\n')
