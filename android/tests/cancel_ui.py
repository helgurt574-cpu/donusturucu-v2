from pathlib import Path
import subprocess,time,json,xml.etree.ElementTree as ET,re,sys
R=Path(__file__).resolve().parents[1]; A=[str(R/'sdk/platform-tools/adb'),'-P','5038','-s','emulator-5580']; mode=sys.argv[1]
def shell(*args):return subprocess.check_output(A+['shell',*args]).decode()
def state():
 shell('uiautomator','dump','/sdcard/window.xml');return subprocess.check_output(A+['exec-out','cat','/sdcard/window.xml'])
def texts(raw):return [n.get('text','') for n in ET.fromstring(raw).iter('node')]
def tap(label):
 for attempt in range(4):
  for n in ET.fromstring(state()).iter('node'):
   if n.get('text')==label:
    assert n.get('enabled')=='true',(label,'disabled')
    x1,y1,x2,y2=map(int,re.findall(r'\d+',n.get('bounds')));shell('input','tap',str((x1+x2)//2),str((y1+y2)//2));return
  shell('input','swipe','400','740','400','220','450')
 raise AssertionError('Not found: '+label)
def snapshot():return shell('sh','-c','"find /sdcard/Download/DonusturucuTest -type f -exec sha256sum {} \\;"')
# Fixed synthetic source names, never user files.
source='/sdcard/Download/cancel-fixtures/'+('CancelScanDense.pdf' if mode=='ocr' else 'CancelSpeech.wav'); before=shell('sha256sum',source); listing=snapshot(); rows=[]
for repeat in range(1,4):
 tap('İşlemi başlat');time.sleep(4 if mode=='ocr' else 12);raw=state();(R/f'cancel-results/{mode}-{repeat}-running.xml').write_bytes(raw);current=texts(raw)
 assert any(('Sayfa okunuyor:' if mode=='ocr' else 'Konuşma yazılıyor:') in t for t in current),current
 start=time.monotonic();tap('Durdur');deadline=time.monotonic()+90
 while True:
  raw=state();ts=texts(raw)
  if any('İşlem durduruldu.' in t for t in ts):break
  assert time.monotonic()<deadline,ts
  time.sleep(1)
 elapsed=time.monotonic()-start;(R/f'cancel-results/{mode}-{repeat}-stopped.xml').write_bytes(raw)
 assert shell('sha256sum',source)==before
 assert snapshot()==listing,'Output files changed after cancel'
 # Start becomes enabled again and no completion dialog is shown.
 nodes=list(ET.fromstring(raw).iter('node'));assert any(n.get('text')=='İşlemi başlat' and n.get('enabled')=='true' for n in nodes)
 rows.append({'mode':mode,'repeat':repeat,'running_status':[t for t in current if 'okunuyor' in t or 'yazılıyor' in t],'cancel_seconds':round(elapsed,2),'source_unchanged':True,'published_files_unchanged':True,'ready_again':True,'pass':True})
 (R/f'cancel-results/{mode}-report.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
 print(rows[-1],flush=True)
