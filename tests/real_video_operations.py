from pathlib import Path
import hashlib,json,subprocess,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from donusturucu import core
from donusturucu.operations import Editor,Request,actions
source=Path('/home/gabar/Music/Ahmed Arif - Hani Kurşun Sıksan Geçmez Geceden.mp4')
root=Path('real-video-operations-results');root.mkdir(exist_ok=True);before=hashlib.sha256(source.read_bytes()).hexdigest()
clip=Editor().execute(Request('trim',[source],root/'seeds',start='30',end='42'))[0]
audio=Editor().execute(Request('extract_audio',[clip],root/'seeds',start='0',end='10'))[0]
rows=[]
for path in [clip,audio]:
 for action in actions(core.detect(path)):
  if action=='transcribe':continue
  try:
   files=[path,path] if action=='merge' else [path]
   options=dict(start='1.25',end='4.75',part='1.1',factor='180' if action=='rotate' else '.75',audio=str(audio),audio_start='2.25',audio_end='3.5')
   if action=='merge':options['segments']=[('1.25','3.75'),('5.5','7.75')]
   products=Editor().execute(Request(action,files,root/('video' if path==clip else 'audio')/action,**options))
   for p in products:subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','null','-'],check=True,capture_output=True,timeout=90)
   rows.append(dict(source=str(path),action=action,status='pass',outputs=list(map(str,products))))
  except Exception as e:rows.append(dict(source=str(path),action=action,status='fail',error=str(e)))
  print(action,rows[-1]['status'],flush=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(root/'report.json').write_text(json.dumps(dict(cases=len(rows),failures=sum(x['status']=='fail' for x in rows),original_unchanged=True,rows=rows),ensure_ascii=False,indent=2))
assert all(x['status']=='pass' for x in rows)
