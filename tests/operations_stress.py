"""Additional real media edit cases, including awkward dimensions and time bases."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib,json,subprocess,sys,time,os
sys.path.insert(0,os.environ.get('DONUSTURUCU_TEST_APP_ROOT',str(Path(__file__).resolve().parents[1])))
from donusturucu import core
from donusturucu.operations import Editor,Request,actions
root=Path(os.environ.get('DONUSTURUCU_OPERATIONS_RESULTS','operations-stress-results'));root.mkdir(exist_ok=True);seeds=root/'seeds';seeds.mkdir(exist_ok=True)
def ff(args):subprocess.run(['ffmpeg','-v','error',*args,'-y'],check=True,capture_output=True)
video=seeds/'Türkçe û فارسی video.mp4'
ff(['-f','lavfi','-i','testsrc2=s=176x144:r=15:d=6','-f','lavfi','-i','sine=frequency=440:sample_rate=44100:duration=6','-c:v','libx264','-c:a','aac',str(video)])
silent=seeds/'silent.mkv';ff(['-f','lavfi','-i','testsrc2=s=320x180:r=24000/1001:d=6','-an','-c:v','libx264',str(silent)])
odd=seeds/'odd.mkv';ff(['-f','lavfi','-i','testsrc=s=177x145:r=12:d=6','-f','lavfi','-i','sine=frequency=660:sample_rate=32000:duration=6','-c:v','libx264','-pix_fmt','yuv444p','-c:a','flac',str(odd)])
audio=seeds/'ses.wav';ff(['-f','lavfi','-i','sine=frequency=880:sample_rate=22050:duration=6','-ac','2',str(audio)])
sources=[video,silent,odd,audio]
for ext in ['ts','webm','mov']:
 p=seeds/('video.'+ext)
 if ext=='webm':ff(['-i',str(video),'-c:v','libvpx-vp9','-c:a','libopus',str(p)])
 elif ext=='ts':ff(['-i',str(video),'-c','copy','-f','mpegts',str(p)])
 else:ff(['-i',str(video),'-c','copy',str(p)])
 sources.append(p)
for ext in ['mp3','flac','ogg','m4a']:
 p=seeds/('ses.'+ext);ff(['-i',str(audio),str(p)]);sources.append(p)
digests={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
jobs=[]
for path in sources:
 for action in actions(core.detect(path)):
  if action=='transcribe':continue
  for start,end in [('0','1.2'),('1.125','3.375'),('4.4','5.6')]:jobs.append((path,action,start,end))
def check(job):
 path,action,start,end=job;row=dict(source=str(path),action=action,start=start,end=end)
 try:
  info=core.detect(path);duration=Editor().duration(path);a=float(start);b=float(end)
  options=dict(start=start,end=end,part='.55',audio=str(audio),audio_start='.25',audio_end='1.15',factor='270' if action=='rotate' else '1.5')
  files=[path]
  if action=='merge':files=[path,silent if info.kind=='video' else audio];options['segments']=[(start,end),('0.25','1.25')]
  outdir=root/'outputs'/str(jobs.index(job));products=Editor().execute(Request(action,files,outdir,**options))
  lengths=[]
  for p in products:
   subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','null','-'],check=True,capture_output=True,timeout=60)
   if action=='frame':
    assert p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n');continue
   detected=core.detect(p)
   if action not in {'frame','gif'}:lengths.append(Editor().duration(p))
   if action=='mute':assert not detected.has_audio
   if action=='rotate':assert (detected.width,detected.height)==((info.height+1)//2*2,(info.width+1)//2*2)
   if detected.kind=='video' and action!='gif':assert detected.width%2==0 and detected.height%2==0
  expected=None
  if action in {'trim','split','extract_audio','rotate'}:expected=b-a
  elif action=='remove_range':expected=duration-(b-a)
  elif action=='speed':expected=duration-(b-a)+(b-a)/1.5
  elif action=='merge':expected=b-a+1
  elif action not in {'frame','gif'}:expected=duration
  if expected is not None:assert abs(sum(lengths)-expected)<.4,(lengths,expected)
  if action=='split':assert len(products)==__import__('math').ceil((b-a)/.55-1e-9)
  row.update(status='pass',outputs=list(map(str,products)))
 except Exception as e:row.update(status='fail',error=str(e),detail=getattr(e,'detail',''))
 print(len(jobs),path.name,action,start,row['status'],row.get('error',''),flush=True);return row
with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(check,jobs))
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in digests.items())
report=dict(cases=len(rows),failures=sum(r['status']=='fail' for r in rows),source_hashes_preserved=True,rows=rows)
(root/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('SUMMARY',report['cases'],report['failures']);assert report['failures']==0
