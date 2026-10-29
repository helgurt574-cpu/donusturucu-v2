from pathlib import Path
import subprocess,json,time
r=Path(__file__).resolve().parents[1];a=[str(r/'sdk/platform-tools/adb'),'-P','5038','-s','emulator-5580'];report='/sdcard/Android/data/org.local.donusturucu/files/feature-test/report.json'
def run(*args):return subprocess.run(a+list(args),capture_output=True,check=True).stdout
for repeat in range(1,4):
 run('shell','am','force-stop','org.local.donusturucu');run('shell','rm','-f',report);run('shell','am','start','-n','org.local.donusturucu/.MainActivity','--ez','feature_test','true','--ez','speech_test','true');deadline=time.monotonic()+120
 while True:
  time.sleep(3)
  raw=run('exec-out','cat',report)
  try:p=json.loads(raw)
  except Exception:p={}
  if p.get('cases')==12:break
  assert time.monotonic()<deadline,p
 assert p['failures']==0,p
 (r/f'long-speech-results/regression-{repeat}.json').write_bytes(raw);print(repeat,p['cases'],p['failures'],flush=True)
