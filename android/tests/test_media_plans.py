from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,hashlib
BASE=Path(__file__).resolve().parents[2];ROOT=BASE/'android/host-test-results';ROOT.mkdir(exist_ok=True)
seed=BASE/'operations-stress-results/seeds';sources=[seed/'Türkçe û فارسی video.mp4',seed/'silent.mkv',seed/'odd.mkv',seed/'ses.wav',seed/'video.ts']
def probe(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]))
def metadata(p):
 r=probe(p);v=next((s for s in r['streams'] if s['codec_type']=='video'),None);a=any(s['codec_type']=='audio' for s in r['streams']);fps=15
 if v:
  x,y=v['avg_frame_rate'].split('/');fps=float(x)/float(y) if float(y) else 15
 return dict(video=bool(v),audio=a,duration=float(r['format']['duration']),width=v['width'] if v else 0,height=v['height'] if v else 0,fps=fps)
jobs=[]
for p in sources:
 m=metadata(p);actions=['trim','remove','split','merge','speed']
 if m['video']:
  actions+=['mute','frame','gif','rotate','add']
  if m['audio']:actions+=['extract','replace','mute_range']
 else:actions+=['mute_range','volume','fade_in','fade_out']
 for a in actions:
  for start,end in [(0,1.2),(1.125,3.375),(4.4,5.6)]:jobs.append((p,a,'',start,end))
 formats=['mp4','mkv','webm','mov','avi','mpeg','ts','gif'] if m['video'] else []
 if m['audio']:formats+=['mp3','wav','flac','ogg','opus','m4a','aac','aiff','wma']
 for fmt in formats:jobs.append((p,'convert',fmt,0,m['duration']))
digest={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
def run(pair):
 index,job=pair;p,action,fmt,start,end=job;folder=ROOT/str(index);folder.mkdir(exist_ok=True);row=dict(source=p.name,action=action,format=fmt,start=start,end=end)
 try:
  m=metadata(p);other=seed/'silent.mkv' if action=='merge' and m['video'] else seed/'ses.wav';om=metadata(other)
  props=dict(source=str(p),output=str(folder/'outputs'),action=action,format=fmt or 'mp4',start=start,end=end,other=str(other),**m)
  props.update({'other.'+k:v for k,v in om.items()})
  prop=folder/'job.properties';prop.write_text('\n'.join(k+'='+str(v).lower() if isinstance(v,bool) else k+'='+str(v) for k,v in props.items()),encoding='utf-8')
  process=subprocess.run(['java','-cp',str(BASE/'android/hostclasses'),'HostMediaHarness',str(prop)],capture_output=True,text=True,timeout=120)
  assert process.returncode==0,process.stderr
  outputs=[Path(s.split('\t',1)[1]) for s in process.stdout.splitlines() if s.startswith('OUTPUT\t')]
  assert outputs
  durations=[]
  for f in outputs:
   subprocess.run(['ffmpeg','-v','error','-i',str(f),'-f','null','-'],check=True,capture_output=True,timeout=60)
   if action not in ['frame','gif'] and fmt!='gif':durations.append(float(probe(f)['format']['duration']))
  expected=None
  if action in ['trim','split','extract','rotate']:expected=end-start
  elif action=='remove':expected=m['duration']-(end-start)
  elif action=='merge':expected=m['duration']+om['duration']
  elif action=='speed':expected=m['duration']-(end-start)+(end-start)/1.5
  elif action not in ['frame','gif'] and fmt!='gif':expected=m['duration']
  if expected is not None:assert abs(sum(durations)-expected)<.5,(durations,expected)
  row.update(status='pass',outputs=list(map(str,outputs)))
 except Exception as e:row.update(status='fail',error=str(e))
 print(index,p.name,action,fmt,row['status'],row.get('error','')[:200],flush=True);return row
with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(run,enumerate(jobs)))
assert all(hashlib.sha256(p.read_bytes()).hexdigest()==d for p,d in digest.items())
report=dict(platform='Linux host running Android Java command planner; not an Android device test',cases=len(rows),failures=sum(x['status']=='fail' for x in rows),originals_unchanged=True,rows=rows)
(ROOT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('SUMMARY',report['cases'],report['failures']);assert report['failures']==0
