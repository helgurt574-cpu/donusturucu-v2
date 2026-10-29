"""Bounded variable frame-rate timeline regression using the release tree."""
from pathlib import Path
import os,sys,subprocess,json,hashlib
base=Path(__file__).resolve().parents[1];sys.path.insert(0,os.environ.get('DONUSTURUCU_TEST_APP_ROOT',str(base/'build/installed-1.6.2/usr/share/donusturucu')))
from donusturucu import core
from donusturucu.operations import Editor,Request
out=Path(os.environ.get('DONUSTURUCU_VFR_OUT',str(base/'qa-vfr-20261025')));out.mkdir(exist_ok=True)
def run(args):return subprocess.run(args,check=True,capture_output=True).stdout
def ff(args):return run(['ffmpeg','-v','error','-y',*args])
# Four unequal-duration solid frames make actual packet presentation times variable.
colors=[(255,0,0),(0,0,255),(0,0,255),(0,255,0)]
for i,c in enumerate(colors):(out/f'f{i}.ppm').write_bytes(b'P6\n160 120\n255\n'+bytes(c)*160*120)
(out/'frames.txt').write_text("file 'f0.ppm'\nduration 1\nfile 'f1.ppm'\nduration 0.4\nfile 'f2.ppm'\nduration 1.6\nfile 'f3.ppm'\nduration 1\nfile 'f3.ppm'\n")
src=out/'VFR Türkçe û فارسی.mkv'
ff(['-f','concat','-safe','1','-i',str(out/'frames.txt'),'-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=4','-t','4','-fps_mode','vfr','-c:v','libx264','-pix_fmt','yuv420p','-c:a','flac',str(src)])
h=hashlib.sha256(src.read_bytes()).hexdigest();frames=json.loads(run(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(src)]))['frames'];ts=[float(f['best_effort_timestamp_time']) for f in frames];assert len(set(round(b-a,2) for a,b in zip(ts,ts[1:])))>1,ts
rows=[]
for repeat in range(1,4):
 for action,expected,checks in [('trim',1.5,[(.1,0),(1.4,2)]),('remove_range',2.5,[(.2,0),(1.1,2),(2.3,1)])]:
  row={'repeat':repeat,'action':action}
  try:
   target=Editor().execute(Request(action,[src],out/f'{action}-{repeat}',start='.75',end='2.25'))[0];info=core.detect(target);duration=Editor().duration(target);assert abs(duration-expected)<.15,(duration,expected)
   streams=json.loads(run(['ffprobe','-v','error','-show_streams','-of','json',str(target)]))['streams']
   assert all(abs(float(x['duration'])-expected)<.15 for x in streams if x['codec_type'] in {'video','audio'}),streams
   ff(['-i',str(target),'-f','null','-'])
   for t,channel in checks:
    data=ff(['-ss',str(t),'-i',str(target),'-frames:v','1','-vf','scale=1:1','-f','rawvideo','-pix_fmt','rgb24','pipe:1']);assert len(data)==3,(t,len(data));assert data[channel]>150 and data[channel]>max(v for i,v in enumerate(data) if i!=channel)*2,(t,list(data),channel)
   pcm=ff(['-i',str(target),'-vn','-ac','1','-ar','8000','-f','s16le','pipe:1']);import numpy as np
   samples=np.frombuffer(pcm,dtype='<i2').astype(float);peak=float(np.fft.rfftfreq(len(samples),1/8000)[np.argmax(abs(np.fft.rfft(samples)))]);assert abs(peak-440)<3,peak
   assert info.has_audio and hashlib.sha256(src.read_bytes()).hexdigest()==h
   row.update(passed=True,duration=duration,peak_hz=peak,source_unchanged=True,output=str(target))
  except Exception as e:row.update(passed=False,error=str(e),detail=getattr(e,'detail',''))
  rows.append(row);print(row,flush=True)
report={'version':os.environ.get('DONUSTURUCU_VFR_VERSION','1.6.3'),'cases':6,'failures':sum(not r['passed'] for r in rows),'input_timestamps':ts,'rows':rows,'scope':'VFR solid-color timeline trim/remove_range; decoded colors, duration and 440Hz audio;3 repeats each','source_sha256':h};(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');assert report['failures']==0
