from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json,subprocess,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from donusturucu import core
from donusturucu.operations import Editor,Request,actions
root=Path('operations-format-results');root.mkdir(exist_ok=True)
sources=list(Path('verified-matrix-linux/sources/audio').glob('*'))+list(Path('verified-matrix-linux/sources/video').glob('*'))
def check(job):
 path,action=job;row={'source':str(path),'action':action}
 try:
  folder=root/path.parent.name/path.suffix[1:]/action
  kwargs=dict(start='.1',end='.4',part='.15',factor='90' if action=='rotate' else '1.5',audio='verified-matrix-linux/seeds/Ses.wav',audio_start='.1',audio_end='.4')
  if action=='merge':kwargs.update(segments=[('.1','.3'),('.2','.4')])
  request=Request(action,[path,path] if action=='merge' else [path],folder,**kwargs)
  products=Editor().execute(request)
  for out in products:
   subprocess.run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'],capture_output=True,check=True,timeout=60)
  row.update(status='pass',outputs=list(map(str,products)))
 except Exception as e:row.update(status='fail',error=str(e))
 print(path.suffix,action,row['status'],row.get('error',''),flush=True);return row
jobs=[(p,a) for p in sources for a in actions(core.detect(p))]
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(check,jobs))
(root/'report.json').write_text(json.dumps(rows,indent=2));print('TOTAL',len(rows),'FAILED',sum(r['status']=='fail' for r in rows));assert all(r['status']=='pass' for r in rows)
