from pathlib import Path
import requests,json,time,hashlib,urllib.parse,os
root=Path(__file__).resolve().parent;url=Path(os.environ.get('BROWSER_TEST_LOG',str(root/'test-server.log'))).read_text().split('http://')[1].strip();url='http://'+url;s=requests.Session();rows=[]
def api(p,data=None):
 r=s.get(url+p) if data is None else s.post(url+p,json=data);r.raise_for_status();return r.json()
def upload(name,data):
 r=s.post(url+'upload',data=data,headers={'X-Filename':urllib.parse.quote(name)});r.raise_for_status();return r.json()['id']
def wait():
 end=time.monotonic()+120
 while time.monotonic()<end:
  d=api('state')
  if not d['busy']:return d
  time.sleep(.2)
 raise RuntimeError('timeout')
for repeat in range(1,4):
 api('clear',{});original='Merhaba Türkçe Kurmancî العربية فارسی\n'.encode();ident=upload('Belge.txt',original)
 api('run',{'ids':[ident],'target':'pdf'});d=wait();assert d['status']=='done',d;pdf=s.get(url+'download?id='+d['results'][0]['id']).content;assert pdf.startswith(b'%PDF-');rows.append({'repeat':repeat,'case':'txt-pdf','pass':True})
 ident2=upload('test.wav',(root.parent/'assets/speech/turkish-test.wav').read_bytes());api('run',{'ids':[ident2],'target':'flac'});d=wait();assert d['status']=='done',d;assert s.get(url+'download?id='+d['results'][0]['id']).content.startswith(b'fLaC');rows.append({'repeat':repeat,'case':'wav-flac','pass':True})
 api('remove',{'id':ident});assert len(api('state')['files'])==1;api('clear',{});assert not api('state')['files'];rows.append({'repeat':repeat,'case':'remove-clear','pass':True})
assert s.get(url+'state',headers={'Host':'evil.invalid'}).status_code==403
assert s.post(url+'clear',json={},headers={'Origin':'https://evil.invalid'}).status_code==403
(root/os.environ.get('BROWSER_TEST_REPORT','test-report.json')).write_text(json.dumps({'cases':len(rows),'failures':0,'rows':rows,'cross_origin_and_bad_host_rejected':True},indent=2)+'\n');print('Passed',len(rows))
