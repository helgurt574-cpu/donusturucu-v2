from pathlib import Path
import requests,time,json,urllib.parse,hashlib,os
b=Path(__file__).resolve().parents[1];url='http://'+(b/os.environ.get('BROWSER_TEST_LOG','qa-folder-1.6.6/browser-server-current.log')).read_text().split('http://')[1].strip();s=requests.Session();rows=[]
def api(path,data=None):
 r=s.get(url+path) if data is None else s.post(url+path,json=data);r.raise_for_status();return r.json()
def upload(name,body,valid=True):
 r=s.post(url+'upload',data=body,headers={'X-Filename':urllib.parse.quote(name)})
 if not valid:assert r.status_code==400;return
 r.raise_for_status();return r.json()['id']
def wait(timeout=120):
 deadline=time.monotonic()+timeout
 while time.monotonic()<deadline:
  d=api('state')
  if not d['busy']:return d
  time.sleep(.05)
 raise AssertionError('Timeout')
for repeat in range(1,4):
 api('clear',{});ids=[];ids.append(upload('Klasor/note.txt',b'Plain text'));ids.append(upload('Klasor/a.srt','1\n00:00:01,000 --> 00:00:02,000\nMerhaba فارسی\n'.encode()));ids.append(upload('Klasor/Alt/a.srt','1\n00:00:01,000 --> 00:00:02,000\nSilav العربية\n'.encode()));upload('Klasor/bad.bin',b'\x00bad',False);state=api('state');assert any(x['name']=='Klasor/Alt/a.srt' for x in state['files']);api('run',{'ids':ids,'action':'subtitle_text'});d=wait();assert d['status']=='done' and len(d['results'])==2 and len(d['issues'])==1,d
 contents={s.get(url+'download?id='+item['id']).content.decode() for item in d['results']};assert contents=={'Merhaba فارسی\n','Silav العربية\n'};assert len({item['name'] for item in d['results']})==2;rows.append({'repeat':repeat,'case':'mixed-folder-subtitle-text','outputs':2,'unsupported_upload_reported':True,'incompatible_operation_reported':True,'relative_names_kept':True,'unique_output_names':True})
small=b/'android/instrumentation/assets/folder-video-0.mp4';large=b/'speed-review-20261025/source-720p.mp4';before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in [small,large]}
for repeat in range(1,4):
 api('clear',{});ids=[upload('Input/'+p.name,p.read_bytes()) for p in [small,large]];api('run',{'ids':ids,'target':'webm','quality':'high'});deadline=time.monotonic()+90
 while time.monotonic()<deadline:
  d=api('state')
  if d['progress']>=.5:break
  assert d['busy'],d;time.sleep(.03)
 time.sleep(.15);api('cancel',{});d=wait();assert d['status']=='cancelled' and len(d['results'])==1,d;assert s.get(url+'download?id='+d['results'][0]['id']).content
 api('run',{'ids':[ids[0]],'action':'trim','start':'0.1','end':'0.3'});d=wait();assert d['status']=='done' and len(d['results'])==1,d;rows.append({'repeat':repeat,'case':'cancel-during-second-file','finished_first_output_preserved':True,'next_job_recovered':True})
assert before=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in before}
(b/os.environ.get('BROWSER_TEST_REPORT','qa-folder-1.6.6/browser-batch.json')).write_text(json.dumps({'cases':len(rows),'failures':0,'originals_unchanged':True,'rows':rows},indent=2));print('Passed',len(rows),'browser batch scenarios')
