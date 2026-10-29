from pathlib import Path
import requests,json,time,urllib.parse,subprocess
b=Path(__file__).resolve().parent;url='http://'+(b/'portable-server.log').read_text().split('http://')[1].strip();s=requests.Session();rows=[]
def api(p,d=None):
 r=s.get(url+p) if d is None else s.post(url+p,json=d);r.raise_for_status();return r.json()
def upload(p):
 r=s.post(url+'upload',data=p.read_bytes(),headers={'X-Filename':urllib.parse.quote(p.name)});r.raise_for_status();return r.json()['id']
def wait():
 until=time.monotonic()+180
 while time.monotonic()<until:
  d=api('state')
  if not d['busy']:return d
  time.sleep(.2)
 raise RuntimeError('timeout')
video=b.parent/'speed-review-20261025/source-720p.mp4'
for repeat in range(1,4):
 api('clear',{});i=upload(video);api('run',{'ids':[i],'target':'webm','quality':'high'});time.sleep(.2);api('cancel',{});d=wait();assert d['status']=='cancelled' and not d['results'],d;rows.append({'case':'cancel-active-video','repeat':repeat,'pass':True})
for repeat in range(1,4):
 api('clear',{});i=upload(b.parent/'assets/speech/english-test.mp3');api('run',{'ids':[i],'action':'transcribe','speech_language':'en'});d=wait();assert d['status']=='done',d;t=s.get(url+'download?id='+d['results'][0]['id']).content.decode();assert 'could you repeat that' in t.lower(),t;rows.append({'case':'speech-en-keyword','repeat':repeat,'pass':True,'text':t})
# Rendered-page OCR exercise: image PDF supplied as a real file, no hidden text.
from PIL import Image
im=Image.open(b.parent/'android/instrumentation/assets/tur-plain.png').convert('RGB');pdf=b/'scan.pdf';im.save(pdf,'PDF',resolution=150)
for repeat in range(1,4):
 api('clear',{});i=upload(pdf);api('run',{'ids':[i],'target':'txt','ocr':True,'ocr_language':'tur'});d=wait();assert d['status']=='done',d;t=s.get(url+'download?id='+d['results'][0]['id']).content.decode();assert t.strip();rows.append({'case':'ocr-turkish-scanned-pdf','repeat':repeat,'pass':True,'text':t})
api('clear',{});(b/'extra-report.json').write_text(json.dumps({'cases':len(rows),'failures':0,'rows':rows,'scope':'Loopback HTTP packaged runtime; recognition keyword/nonempty checks, not full fidelity'},ensure_ascii=False,indent=2)+'\n');print('Passed',len(rows))
