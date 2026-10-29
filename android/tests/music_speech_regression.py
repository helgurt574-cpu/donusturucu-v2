from pathlib import Path
import subprocess,time,json
r=Path(__file__).resolve().parents[1];out=r/'noisy-speech-results';a=[str(r/'sdk/platform-tools/adb'),'-P','5038','-s','emulator-5580']
def cmd(args,check=True):return subprocess.run(a+args,capture_output=True,check=check).stdout
for cls,folder in [('InstrumentalSpeech','instrumental-speech-test'),('NoisySpeech','noisy-speech-test'),('LongSpeech','long-speech-test')]:
 cmd(['shell','am','instrument','-w','org.local.donusturucu.qa/org.local.donusturucu.qa.'+cls]);raw=cmd(['exec-out','cat','/sdcard/Android/data/org.local.donusturucu/files/'+folder+'/report.json']);p=json.loads(raw);(out/(folder+'-after.json')).write_bytes(raw)
 if cls!='NoisySpeech':assert p['failures']==0,p
 print(cls,p['cases'],p['failures'],flush=True)
for repeat in range(1,4):
 path='/sdcard/Android/data/org.local.donusturucu/files/feature-test/report.json';cmd(['shell','am','force-stop','org.local.donusturucu']);cmd(['shell','rm','-f',path]);cmd(['shell','am','start','-n','org.local.donusturucu/.MainActivity','--ez','feature_test','true','--ez','speech_test','true']);deadline=time.monotonic()+180
 while True:
  time.sleep(2);raw=cmd(['exec-out','cat',path],False)
  try:p=json.loads(raw)
  except Exception:p={}
  if p.get('cases')==12:break
  assert time.monotonic()<deadline,p
 assert p['failures']==0,p;(out/f'feature-regression-{repeat}.json').write_bytes(raw);print(repeat,p['cases'],p['failures'],flush=True)
