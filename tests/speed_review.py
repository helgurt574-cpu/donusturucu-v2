from pathlib import Path
import sys,subprocess,time,json,statistics,hashlib,re,os
b=Path(__file__).resolve().parents[1];sys.path.insert(0,str(b/'build/installed-1.6.2/usr/share/donusturucu'))
from donusturucu import core
from donusturucu.runtime import isolation_status
out=b/'speed-review-20261025';src=out/'source-720p.mp4'
subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=s=1280x720:r=30:d=10','-f','lavfi','-i','sine=frequency=440:duration=10','-c:v','libx264','-crf','16','-preset','fast','-c:a','aac',str(src)],check=True)
h=hashlib.sha256(src.read_bytes()).hexdigest();info=core.detect(src);rows=[]
class ProbeRunner(core.Runner):
 def __init__(self,preset):super().__init__();self.preset=preset;self.command=None
 def run(self,args,**kw):
  args=list(args)
  if args[0]=='ffmpeg':
   if '-preset' in args:args[args.index('-preset')+1]=self.preset
   self.command=args
  return super().run(args,**kw)
for repeat in range(1,4):
 for preset in ['copy','medium','fast','veryfast']:
  runner=ProbeRunner(preset);start=time.perf_counter();p=runner.convert(info,'mkv',out/f'{preset}-{repeat}',core.Options(quality='original' if preset=='copy' else 'balanced'));seconds=time.perf_counter()-start
  probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]));duration=float(probe['format']['duration']);assert abs(duration-10)<.15
  subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','null','-'],check=True,capture_output=True)
  psnr=None
  if preset!='copy':
   check=subprocess.run(['ffmpeg','-hide_banner','-i',str(src),'-i',str(p),'-lavfi','[0:v]setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[z];[a][z]psnr','-an','-f','null','-'],capture_output=True,text=True,check=True);m=re.findall(r'average:([0-9.]+)',check.stderr);assert m;psnr=float(m[-1])
  else:
   def digest(path):return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-'])
   assert digest(src)==digest(p)
  assert hashlib.sha256(src.read_bytes()).hexdigest()==h
  rows.append(dict(repeat=repeat,preset=preset,seconds=round(seconds,3),bytes=p.stat().st_size,psnr=psnr,duration=duration,command=runner.command));print(preset,round(seconds,3),flush=True)
summary={k:{'median_seconds':round(statistics.median(r['seconds'] for r in rows if r['preset']==k),3),'bytes':next(r['bytes'] for r in rows if r['preset']==k),'psnr_db':next(r['psnr'] for r in rows if r['preset']==k)} for k in ['copy','medium','fast','veryfast']}
report={'source':'synthetic moving test pattern10s 1280x72030fps H264/AAC','source_sha256':h,'app_root':str(Path(core.__file__).resolve().parents[1]),'isolation':isolation_status(),'repeats':3,'rows':rows,'summary':summary,'limitations':['Single synthetic source; not a prediction for all videos or other platforms','Same CRF is not identical quality across presets; PSNR is only one numerical metric','No GPU encoding benchmark; no product defaults changed']};(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,indent=2))
