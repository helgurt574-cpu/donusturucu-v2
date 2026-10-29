from pathlib import Path
import json,subprocess,array,math
root=Path(__file__).resolve().parents[1]/'device-results';report=json.loads((root/'report.json').read_text());rows=report['rows']
def final(action):
 i=next(i for i,r in enumerate(rows) if r.get('source')=='video.mp4' and r['action']==action)
 return root/('case-'+str(i))/('audio-inserted.mp4' if action in ['add','replace'] else 'result.mp4')
def samples(path,start):
 p=subprocess.run(['ffmpeg','-v','error','-ss',str(start),'-i',str(path),'-t','0.2','-f','s16le','-ar','48000','-ac','1','pipe:1'],capture_output=True,check=True);a=array.array('h');a.frombytes(p.stdout);return a
def energy(path,start,f):
 x=samples(path,start);return abs(sum(v*complex(math.cos(2*math.pi*f*i/48000),math.sin(2*math.pi*f*i/48000)) for i,v in enumerate(x)))/len(x)
checks=[];muted=final('mute_range')
for t in [.15,1,2.2]:
 x=samples(muted,t);rms=math.sqrt(sum(v*v for v in x)/len(x));assert rms<20 if t==1 else rms>100;checks.append(dict(operation='mute_range',time=t,rms=rms))
for action in ['add','replace']:
 p=final(action)
 for t in [.15,1,2.2]:
  e440,e880=energy(p,t,440),energy(p,t,880)
  if t==1:assert e880>100;assert e440>100 if action=='add' else e440<30
  else:assert e440>100 and e880<30
  checks.append(dict(operation=action,time=t,energy440=e440,energy880=e880))
(root.parent/'device-audio-validation.json').write_text(json.dumps(dict(passed=True,checks=checks),indent=2));print('PASS Android-native outputs: correct mute interval, 880 Hz insertion/replacement, 440 Hz preserved outside interval')
