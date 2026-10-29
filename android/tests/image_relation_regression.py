from pathlib import Path
import subprocess,time,json
r=Path(__file__).resolve().parents[1];out=r/'image-relation-results';a=[str(r/'sdk/platform-tools/adb'),'-P','5038','-s','emulator-5580']
def cmd(args,check=True):return subprocess.run(a+args,capture_output=True,check=check).stdout
for kind,folder in [('TextOnlyImages','text-only-images'),('ImageRelations','image-relation-test'),('RichChains','rich-chains'),('LargeImages','large-rich-chains'),('PdfPages','pdf-page-chains'),('StyledHtml','styled-html')]:
 cmd(['shell','am','instrument','-w','org.local.donusturucu.qa/org.local.donusturucu.qa.'+kind]);raw=cmd(['exec-out','cat','/sdcard/Android/data/org.local.donusturucu/files/'+folder+'/report.json']);d=json.loads(raw);assert d['failures']==0; (out/(folder+'-regression.json')).write_bytes(raw);print(folder,d['cases'],flush=True)
for repeat in range(1,4):
 path='/sdcard/Android/data/org.local.donusturucu/files/rich-test/report.json';cmd(['shell','am','force-stop','org.local.donusturucu']);cmd(['shell','rm','-f',path]);cmd(['shell','am','start','-n','org.local.donusturucu/.MainActivity','--ez','rich_test','true']);deadline=time.monotonic()+120
 while True:
  time.sleep(2);raw=cmd(['exec-out','cat',path],False)
  try:d=json.loads(raw)
  except Exception:d={}
  if d.get('cases')==15:break
  assert time.monotonic()<deadline
 assert d['failures']==0; (out/f'rich-regression-{repeat}.json').write_bytes(raw);print(repeat,d['cases'],flush=True)
