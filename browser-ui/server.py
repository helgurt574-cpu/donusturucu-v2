"""Local-only browser interface to the existing offline engine."""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
import sys,os,json,secrets,tempfile,threading,shutil,urllib.parse,webbrowser
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT.parent))
from donusturucu import core,speech,runtime
from donusturucu.operations import Editor,Request,actions
TOKEN=secrets.token_urlsafe(32);WORK=Path(tempfile.mkdtemp(prefix='donusturucu-web-'));FILES={};OUTPUTS={};LOCK=threading.RLock();STATE={'busy':False,'progress':0,'status':'ready','error':'','results':[]};RUNNER=None
class BrowserRunner(core.Runner):
 def run(self,args,**kwargs):
  # Bundled Python settings must not enter system LibreOffice's Python UNO.
  if not Path(str(args[0])).name.startswith('python'):
   args=['/usr/bin/env','-u','PYTHONHOME','-u','PYTHONPATH',*runtime.resolve_command(args)]
  return super().run(args,**kwargs)
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def reply(self,value,status=200):
  data=json.dumps(value,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
 def allowed(self):
  host=self.headers.get('Host','');origin=self.headers.get('Origin');return host==f'127.0.0.1:{self.server.server_port}' and (not origin or origin=='http://'+host) and self.path.startswith('/'+TOKEN+'/')
 def do_GET(self):
  if not self.allowed():return self.reply({'error':'forbidden'},403)
  route=urllib.parse.urlsplit(self.path).path.split('/')[-1]
  if route=='':
   data=(ROOT/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'");self.end_headers();self.wfile.write(data)
  elif route=='state':
   with LOCK:
    files=[{'id':k,'name':v['name'],'kind':v['info'].kind,'format':v['info'].fmt,'duration':v['info'].duration,'targets':core.targets(v['info']),'actions':actions(v['info'])} for k,v in FILES.items()];s=dict(STATE);s['files']=files;s['tools']=core.tools()
    try:speech.resources();s['speech']=True
    except Exception:s['speech']=False
   self.reply(s)
  elif route=='download':
   key=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('id',[''])[0]
   if key not in OUTPUTS:return self.reply({'error':'not_found'},404)
   p=OUTPUTS[key];self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Content-Length',str(p.stat().st_size));self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+urllib.parse.quote(p.name));self.end_headers()
   with p.open('rb') as f:shutil.copyfileobj(f,self.wfile)
  else:self.reply({'error':'not_found'},404)
 def do_POST(self):
  global RUNNER
  if not self.allowed():return self.reply({'error':'forbidden'},403)
  route=urllib.parse.urlsplit(self.path).path.split('/')[-1]
  try:
   if route=='cancel':
    with LOCK:
     if RUNNER:RUNNER.cancel()
    return self.reply({'ok':True})
   with LOCK:
    if STATE['busy']:return self.reply({'error':'busy'},409)
    if route=='upload':
     length=int(self.headers.get('Content-Length','0'));assert 0<length<=32*1024**3,'invalid_size';display_name=urllib.parse.unquote(self.headers.get('X-Filename','dosya'));name=display_name.replace('\\','/').split('/')[-1];name=name or 'dosya';key=secrets.token_hex(12);folder=WORK/key;folder.mkdir();p=folder/name
     try:
      with p.open('wb') as f:
       while length:
        chunk=self.rfile.read(min(length,1024*1024))
        if not chunk:raise ValueError('incomplete_upload')
        f.write(chunk);length-=len(chunk)
      info=core.detect(p);FILES[key]={'name':display_name,'info':info}
     except Exception:shutil.rmtree(folder);raise
     return self.reply({'id':key})
    length=int(self.headers.get('Content-Length','0'));assert length<8*1024*1024;data=json.loads(self.rfile.read(length) or b'{}')
    if route=='clear':
     for key in list(FILES):shutil.rmtree(WORK/key)
     FILES.clear();return self.reply({'ok':True})
    if route=='remove':
     key=data['id'];assert key in FILES;shutil.rmtree(WORK/key);del FILES[key];return self.reply({'ok':True})
    if route!='run':return self.reply({'error':'not_found'},404)
    selected=[FILES[k]['info'] for k in data['ids']];assert selected;action=data.get('action','convert');assert action=='convert' or any(action in actions(info) for info in selected);STATE.update(busy=True,progress=0,status='running',error='',results=[],issues=[]);RUNNER=BrowserRunner(progress=lambda f:STATE.update(progress=max(0,min(1,f))));runner=RUNNER
   def job():
    global RUNNER
    folder=None
    def preserve_finished():
     with LOCK:
      results=[]
      if folder and folder.is_dir():
       for path in folder.iterdir():
        if path.is_file():
         key=secrets.token_hex(12);OUTPUTS[key]=path;results.append({'id':key,'name':path.name})
      STATE['results']=results
    try:
     folder=WORK/('output-'+secrets.token_hex(12));folder.mkdir()
     issues=[]
     if action=='convert':
      products=[]
      for i,info in enumerate(selected):
       runner.check();runner.progress=lambda f,i=i:STATE.update(progress=(i+f)/len(selected))
       try:
        target=data['target'];opt=core.Options(quality=data.get('quality','original'),only_text=data.get('only_text',False),ocr=data.get('ocr',False),ocr_language=data.get('ocr_language','tur+eng'));products.append(runner.convert(info,target,folder,opt))
       except core.Cancelled:raise
       except Exception as error:issues.append({'name':info.path.name,'error':str(error)})
     else:
      allowed={'start','end','part','pages','page_count','audio_start','audio_end','factor','speech_language','speech_format'};kw={k:str(v) for k,v in data.items() if k in allowed}
      if data.get('audio_id'):kw['audio']=str(FILES[data['audio_id']]['info'].path)
      request=Request(action,[i.path for i in selected],folder,**kw)
      if len(selected)>1:
       products,failures=Editor(runner).execute_many(request);issues=[{'name':path.name,'error':str(error)} for path,error in failures]
      else:products=Editor(runner).execute(request)
     with LOCK:
      runner.check();results=[]
      for p in products:
       k=secrets.token_hex(12);OUTPUTS[k]=p;results.append({'id':k,'name':p.name})
      STATE.update(status='done' if results else 'error',results=results,issues=issues)
    except core.Cancelled:
     preserve_finished();STATE.update(status='cancelled')
    except Exception as e:
     preserve_finished();STATE.update(status='error',error=str(e)+' '+getattr(e,'detail',''))
    finally:
     with LOCK:STATE['busy']=False;RUNNER=None
   threading.Thread(target=job,daemon=True).start();self.reply({'ok':True})
  except Exception as e:self.reply({'error':str(e)},400)
def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);url=f'http://127.0.0.1:{server.server_port}/{TOKEN}/';print('Tarayıcıda aç / Di gerokê de veke: '+url,flush=True)
 if '--no-browser' not in sys.argv:webbrowser.open(url)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:
  if RUNNER:RUNNER.cancel()
  server.server_close();shutil.rmtree(WORK,ignore_errors=True)
if __name__=='__main__':main()
