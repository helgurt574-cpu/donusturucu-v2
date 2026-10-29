import json,subprocess,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from donusturucu import core
root=Path('source-preserve-tests-final');root.mkdir(exist_ok=True)
sources=list(Path('verified-matrix-linux/sources/audio').glob('*'))+list(Path('verified-matrix-linux/sources/video').glob('*'))
def check(job):
 source,target=job;row={'source':str(source),'target':target}
 try:
  info=core.detect(source);out=core.Runner().convert(info,target,root/source.parent.name/source.suffix[1:]);detected=core.detect(out)
  subprocess.run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'],check=True,capture_output=True,timeout=60)
  if target in core.VIDEO:assert (detected.width,detected.height)==(info.width,info.height)
  row.update(status='pass',output=str(out))
 except Exception as e:row.update(status='fail',error=str(e))
 print(source.suffix,target,row['status'],row.get('error',''),flush=True);return row
jobs=[(s,t) for s in sources for t in core.targets(core.detect(s))]
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(check,jobs))
(root/'report.json').write_text(json.dumps(rows,indent=2));print('TOTAL',len(rows),'FAILED',sum(x['status']=='fail' for x in rows))
def hashes(p):
 x=subprocess.run(['ffprobe','-v','error','-show_packets','-show_data_hash','sha256','-of','json',str(p)],capture_output=True,text=True,check=True)
 return [(p['codec_type'],p['data_hash']) for p in json.loads(x.stdout)['packets']]
s=Path('verified-matrix-linux/seeds/Video.mp4');o=core.Runner().convert(core.detect(s),'mkv',root/'copy')
a=hashes(s);b=hashes(o)
for k in ['video','audio']:assert [h for t,h in a if t==k]==[h for t,h in b if t==k]
print('PASS: MP4 to MKV video and audio packets unchanged',flush=True)
assert all(x['status']=='pass' for x in rows)
