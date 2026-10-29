from pathlib import Path
import subprocess,time,json
R=Path(__file__).resolve().parents[1];A=[str(R/'sdk/platform-tools/adb'),'-P','5038','-s','emulator-5580'];OUT=R/'retest-20261024';OUT.mkdir(exist_ok=True);rows=[]
def cmd(args,check=True):return subprocess.run(A+args,capture_output=True,check=check).stdout
cmd(['wait-for-device'])
while cmd(['shell','getprop','sys.boot_completed']).strip()!=b'1':time.sleep(2)
cmd(['install','-r',str(R/'instrumentation/build/diagnostic.apk')]);cmd(['shell','am','force-stop','org.local.donusturucu'])
p=cmd(['shell','am','instrument','-w','org.local.donusturucu.qa/org.local.donusturucu.qa.OcrRobustness']);(OUT/'instrumentation.log').write_bytes(p)
raw=cmd(['exec-out','cat','/sdcard/Android/data/org.local.donusturucu/files/ocr-robustness/report.json']);d=json.loads(raw);assert d['cases']==45 and d['failures']==0;(OUT/'robustness.json').write_bytes(raw);rows.append({'phase':'robustness','cases':45,'failures':0})
for flag,folder,total,reps,extra in [('orientation_test','orientation-test',120,1,[]),('detection_test','detection-test',45,1,[]),('self_test','self-test',105,3,[]),('document_matrix','document-matrix',64,3,[]),('rich_test','rich-test',15,3,[]),('feature_test','feature-test',12,3,['--ez','speech_test','true'])]:
 for rep in range(1,reps+1):
  path='/sdcard/Android/data/org.local.donusturucu/files/'+folder+'/report.json';cmd(['shell','am','force-stop','org.local.donusturucu']);cmd(['shell','rm','-f',path]);cmd(['shell','am','start','-n','org.local.donusturucu/.MainActivity','--ez',flag,'true',*extra]);deadline=time.monotonic()+900
  while True:
   time.sleep(3);raw=cmd(['exec-out','cat',path],check=False)
   try:d=json.loads(raw)
   except Exception:d={}
   if d.get('cases')==total:break
   assert time.monotonic()<deadline,(flag,d)
  dest=OUT/(folder+'-'+str(rep)+'.json');dest.write_bytes(raw);assert d['failures']==0,(flag,d)
  row={'phase':flag,'repeat':rep,'cases':total,'failures':0};rows.append(row);(OUT/'summary.json').write_text(json.dumps({'phases':rows,'cases':sum(r['cases'] for r in rows),'failures':sum(r['failures'] for r in rows)},indent=2));print(row,flush=True)
cmd(['uninstall','org.local.donusturucu.qa']);cmd(['emu','kill'])
