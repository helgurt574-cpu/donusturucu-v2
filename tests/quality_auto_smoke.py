import json,subprocess,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from donusturucu import core
root=Path('quality-auto-results');root.mkdir(exist_ok=True)
source=Path('verified-matrix-linux/seeds/Video.mp4')
def run(job):
 target,quality,res=job;row={'target':target,'quality':quality,'resolution':res}
 try:
  output=core.Runner().convert(core.detect(source),target,root,core.Options(quality=quality,resolution=res))
  subprocess.run(['ffmpeg','-v','error','-i',str(output),'-f','null','-'],capture_output=True,check=True)
  info=core.detect(output);assert (info.width,info.height)==(160,120)
  if target!='gif':assert info.has_audio
  row.update(status='pass',output=str(output))
 except Exception as e:row.update(status='fail',error=str(e))
 print(target,quality,res,row['status'],row.get('error',''),flush=True);return row
jobs=[(t,q,r) for t in sorted(core.VIDEO) for q in ['original','small','balanced','high'] for r in ['original','480','720','1080']]
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,jobs))
# Verify actual downscaling, since the main sample is smaller than all limits.
big=root/'Big.mp4';subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=800x600:r=12:d=0.3','-c:v','libx264','-y',str(big)],check=True)
out=core.Runner().convert(core.detect(big),'mp4',root,core.Options(quality='high',resolution='480'));info=core.detect(out);assert info.height==480
(root/'report.json').write_text(json.dumps(rows,indent=2));print('TOTAL',len(rows),'FAILED',sum(r['status']=='fail' for r in rows),'DOWNSCALE PASS')
assert all(r['status']=='pass' for r in rows)
