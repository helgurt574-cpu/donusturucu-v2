"""Host orchestrator; actual release speech_worker runs as AArch64 under QEMU."""
from pathlib import Path
import subprocess,os,json,hashlib,time,wave
base=Path(__file__).resolve().parents[1];out=base/'build/arm64-1.6.2-results';out.mkdir(exist_ok=True)
root=base/'build/arm64-test/root';app=base/'build/package-arm64/usr/share/donusturucu';qemu=base/'build/arm64-test/qemu/usr/bin/qemu-aarch64'
env=os.environ.copy();env.update(PYTHONHOME=str(root/'usr'),PYTHONPATH=str(app)+':'+str(app/'asr-env/lib/python3.12/site-packages'),LD_LIBRARY_PATH=str(root/'usr/lib/aarch64-linux-gnu'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
cmd=[str(qemu),'-L',str(root),str(root/'usr/bin/python3.12')]
proof=subprocess.run(cmd+['-c','import platform,json,numpy,ctranslate2,faster_whisper;print(json.dumps({"machine":platform.machine(),"python":platform.python_version()}))'],env=env,capture_output=True,text=True,check=True)
(out/'imports.json').write_text(proof.stdout);assert json.loads(proof.stdout)['machine']=='aarch64'
src=base/'assets/speech/turkish-test.wav';before=hashlib.sha256(src.read_bytes()).hexdigest();audio=out/'turkish-pcm.wav'
subprocess.run(['ffmpeg','-v','error','-y','-i',str(src),'-ar','16000','-ac','1','-c:a','pcm_s16le',str(audio)],check=True)
silence=out/'silence.wav'
with wave.open(str(silence),'wb') as w:w.setparams((1,2,16000,0,'NONE','not compressed'));w.writeframes(b'\0\0'*32000)
report={'version':'1.6.2','emulated':True,'physical_device':False,'pipeline':'unmodified packaged donusturucu.speech_worker.main; host FFmpeg PCM preparation','cases':[],'limitations':['QEMU user mode does not verify native ARM GUI or seccomp kernel behavior','Keyword checks are not full transcription fidelity','No installed ARM operating system integration test']}
for repeat in range(1,4):
 for kind,path in [('turkish',audio),('silence',silence)]:
  target=out/f'{kind}-{repeat}.txt';h=hashlib.sha256(path.read_bytes()).hexdigest();start=time.monotonic()
  p=subprocess.run(cmd+['-m','donusturucu.speech_worker','--model',str(app/'asr-models/whisper-small'),'--audio',str(path),'--output',str(target),'--language','tr'],env=env,capture_output=True,text=True,timeout=1200)
  (out/f'{kind}-{repeat}.log').write_text(p.stdout+'\n'+p.stderr);text=target.read_text() if target.exists() else '';segments=json.loads(target.with_suffix('.segments.json').read_text()) if target.with_suffix('.segments.json').exists() else {}
  ok=p.returncode==0 and 'SPEECH_COMPLETE' in p.stdout and hashlib.sha256(path.read_bytes()).hexdigest()==h and hashlib.sha256(src.read_bytes()).hexdigest()==before
  ok=ok and (('merhaba' in text.casefold() and 'bugün' in text.casefold()) if kind=='turkish' else not text.strip())
  with wave.open(str(path)) as w:duration=w.getnframes()/w.getframerate()
  ok=ok and all(0<=s['start']<=s['end']<=duration+.1 for s in segments.get('segments',[]))
  row={'kind':kind,'repeat':repeat,'pass':ok,'returncode':p.returncode,'text':text,'duration':duration,'source_unchanged':hashlib.sha256(path.read_bytes()).hexdigest()==h,'seconds':round(time.monotonic()-start,2),'segments':segments}
  report['cases'].append(row);report['failures']=sum(not c['pass'] for c in report['cases']);(out/'speech-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(kind,repeat,ok,flush=True)
assert report['failures']==0,report
