"""Local web interface (same design as Android and the Linux window).

Desktop mode (Windows/macOS app, `python -m donusturucu.webapp`): files are read where they are,
native file dialogs come from Tk on the main thread, results go to the chosen folder and the page
opens in an app window of Edge/Chrome when one is installed. Browser mode (browser-ui/server.py):
files are uploaded and results downloaded. Only 127.0.0.1 with a random token is served."""
from __future__ import annotations
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
import json,os,queue,secrets,shutil,subprocess,sys,tempfile,threading,time,traceback,urllib.parse
from . import core,runtime,VERSION,studio_ops as so,jobs,theme
from .i18n import STRINGS

HERE=Path(__file__).resolve().parent
TYPES={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.gif':'image/gif','.bmp':'image/bmp','.mp4':'video/mp4','.webm':'video/webm','.mkv':'video/x-matroska','.mov':'video/quicktime',
 '.wav':'audio/wav','.mp3':'audio/mpeg','.ogg':'audio/ogg','.opus':'audio/ogg','.flac':'audio/flac','.m4a':'audio/mp4','.aac':'audio/aac','.pdf':'application/pdf','.txt':'text/plain; charset=utf-8'}

class Studio:
    """Everything the page sees: files, the running job, previews and results."""
    def __init__(self,desktop):
        self.desktop=desktop;self.lock=threading.RLock();self.work=Path(tempfile.mkdtemp(prefix='donusturucu-web-'))
        self.files={};self.media={};self.order=[];self.busy=False;self.progress=None;self.status='';self.error='';self.results=[];self.summary='';self.preview=None
        self.runner=None;self.log=[];self.last_ping=time.monotonic();self.dialogs=queue.Queue()
        s=theme.load_settings();self.settings=s;self.output=Path(s.get('output',str(Path.home()/'Dönüştürülenler')))
    def ku(self):return self.settings.get('language','tr')=='ku'
    def t(self,a,b):return b if self.ku() else a
    def save(self):
        try:path=theme.settings_path();path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(self.settings,ensure_ascii=False,indent=1),encoding='utf-8')
        except OSError:pass
    def share(self,path):
        """A file the page may load (thumbnails, previews, results): served by a random key."""
        key=secrets.token_hex(10)
        with self.lock:self.media[key]=Path(path)
        return key
    def error_text(self,e):
        lang='ku' if self.ku() else 'tr';key=str(e) if isinstance(e,so.OperationError) else getattr(e,'code',None)
        from .studio_text import ERRORS
        if key in ERRORS:return ERRORS[key][1 if lang=='ku' else 0]
        try:
            from .extras import TEXT
            if key in TEXT[lang]:return TEXT[lang][key]
        except Exception:pass
        if key and key in STRINGS[lang]:
            detail=getattr(e,'detail','');return STRINGS[lang][key]+((': '+detail) if key in {'missing_tool','unsupported','not_file'} and detail else '')
        return str(e)[:400]

    # ---------------------------------------------------------- files
    def add(self,paths):
        added=[];errors=[]
        for path in core.expand_paths(paths):
            try:
                info=so.detect(path);key=secrets.token_hex(8);thumb=self.thumb(info)
                with self.lock:self.files[key]={'info':info,'name':info.path.name,'thumb':self.share(thumb) if thumb else None,'uploaded':False};self.order.append(key)
                added.append(key)
            except Exception as e:errors.append(f'{Path(path).name}: {self.error_text(e)}')
        return added,errors
    def thumb(self,info):
        try:
            folder=self.work/'thumbs';folder.mkdir(exist_ok=True);out=folder/(secrets.token_hex(6)+'.png');st=so.Studio()
            if info.kind=='video':return st.still(info.path,min(1,info.duration*0.1),320,out)
            if info.kind=='image':st.ff([*st.inp(info.path),'-frames:v','1','-vf',"scale='min(320,iw)':-2",str(out)]);return out
            if info.kind=='pdf':return st.render_page(info.path,0,240,folder)
        except Exception:return None
    def describe(self,key):
        f=self.files[key];info=f['info']
        try:size=info.path.stat().st_size
        except OSError:size=0
        return {'id':key,'name':f['name'],'kind':info.kind,'fmt':info.fmt,'duration':info.duration,'width':info.width,'height':info.height,'size':size,'thumb':f['thumb'],
                'targets':so.convert_targets(info),'tools':jobs.tools_for(info),'audio':info.has_audio}
    def view_pdf(self,key):
        """PDF used to show a file page by page; documents are converted once per session."""
        f=self.files[key];info=f['info']
        if info.kind=='pdf':return info.path
        if f.get('pdf') and Path(f['pdf']).is_file():return Path(f['pdf'])
        folder=self.work/'view'/secrets.token_hex(4);folder.mkdir(parents=True)
        f['pdf']=str(core.Runner().convert(info,'pdf',folder,core.Options()));return Path(f['pdf'])
    def base(self,key,page=0,at=-1):
        """Picture of a file for its workspace (frame, page or photo) and, for sound, the wave."""
        info=self.files[key]['info'];st=so.Studio();folder=self.work/'base'/secrets.token_hex(4);folder.mkdir(parents=True)
        out={'pages':0}
        if info.kind=='video':out['img']=self.share(st.still(info.path,at if at>=0 else min(1,info.duration*0.1),1400,folder/'frame.png'));out['media']=self.share(info.path)
        elif info.kind=='audio':out['peaks']=st.peaks(info.path,140);out['media']=self.share(info.path)
        elif info.kind=='pdf' or (info.kind in ('document','spreadsheet','presentation','ebook') and info.fmt!='srt'):
            pdf=self.view_pdf(key);n=len(st.reader(pdf).pages);out['pages']=n;out['img']=self.share(st.render_page(pdf,min(page,max(0,n-1)),1200,folder))
        elif info.kind=='image':out['img']=self.share(st.still_png(info.path,folder))
        elif info.fmt in ('txt','srt','md','csv','tsv','html','rst'):text=info.path.read_text(encoding='utf-8',errors='replace');out['text']=text[:1800]+('…' if len(text)>1800 else '')
        return out

    # ---------------------------------------------------------- jobs
    def begin(self,text):
        self.busy=True;self.progress=None;self.status=text;self.error='';self.runner=core.Runner(progress=lambda v:setattr(self,'progress',max(0.0,min(1.0,float(v)))))
    def info_of(self,key):return self.files[key]['info'] if key and key in self.files else None
    def start(self,data):
        with self.lock:
            if self.busy:raise RuntimeError('busy')
            ids=[k for k in data.get('ids',[]) if k in self.files];assert ids,'choose_file'
            source=self.files[data['source']]['info'] if data.get('source') in self.files else self.files[ids[0]]['info']
            action=data.get('action','convert');opts={k:str(v) for k,v in (data.get('opts') or {}).items()};other=self.info_of(data.get('other'))
            jobs.check(source,action,opts,other,len(ids)>1)
            targets=[self.files[k]['info'] for k in ids];c=data.get('conv') or {}
            conv=core.Options(c.get('quality','original'),c.get('resolution','original'),'auto',bool(c.get('only_text')),bool(c.get('ocr')),c.get('ocr_language','tur+eng'))
            output=self.output if self.desktop else self.work/('output-'+secrets.token_hex(6))
            self.begin(self.t('İşlem başladı…','Kar dest pê kir…'));self.results=[];self.summary='';runner=self.runner
        def work():
            outputs=[];failed=0;cancelled=False
            try:outputs,failed=jobs.run(runner,targets,source,action,data.get('target',''),opts,conv,other,output,self.ku(),self.log.append,self.error_text,lambda s:setattr(self,'status',s))
            except core.Cancelled:cancelled=True
            except Exception as e:failed+=1;self.error=self.error_text(e);self.log.append(traceback.format_exc()[-2000:])
            with self.lock:
                self.results=[{'id':self.share(o),'name':Path(o).name,'path':str(o) if self.desktop else ''} for o in outputs]
                for o in outputs:remember(o,action)
                self.summary=(self.t('Kaydedilen: ','Tomarkirî: ')+str(len(outputs))+(self.t(' · Hatalı: ',' · Çewt: ')+str(failed) if failed else '')) if outputs or failed else ''
                self.status=self.t('İşlem durduruldu. Tamamlanan çıktılar ve orijinaller korunuyor.','Kar hat rawestandin.') if cancelled else (self.t('İşlem bitti.','Kar qediya.') if outputs else self.t('İşlem tamamlanamadı. Ayrıntılar işlem kaydında.','Kar nehat temamkirin.'))
                self.busy=False;self.runner=None;self.progress=None
        threading.Thread(target=work,daemon=True).start()
    def make_preview(self,data):
        with self.lock:
            if self.busy:raise RuntimeError('busy')
            info=self.files[data['source']]['info'];action=data.get('action','convert');opts={k:str(v) for k,v in (data.get('opts') or {}).items()};other=self.info_of(data.get('other'))
            jobs.check(info,action,opts,other,True);c=data.get('conv') or {}
            conv=core.Options(c.get('quality','original'),c.get('resolution','original'),'auto',bool(c.get('only_text')),bool(c.get('ocr')),c.get('ocr_language','tur+eng'))
            self.begin(self.t('Önizleme hazırlanıyor…','Pêşdîtin tê amadekirin…'));self.preview=None;runner=self.runner
        def work():
            folder=self.work/'preview'/secrets.token_hex(4);folder.mkdir(parents=True)
            try:
                p=jobs.preview(runner,info,action,data.get('target',''),opts,conv,other,int(data.get('page',0) or 0),folder,self.ku(),lambda s:setattr(self,'status',s))
                if p.get('result') is not None:p['result_ext']=Path(p['result']).suffix.lower()
                for key in ('before','after','original','result'):
                    if p.get(key) is not None:p[key]=self.share(p[key])
                if p.get('thumbs'):p['thumbs']=[[self.share(path),cap] for path,cap in p['thumbs']]
                p['id']=secrets.token_hex(4);self.preview=p;self.status=self.t('Önizleme hazır. Beğendiysen Başlat\'a bas.','Pêşdîtin amade ye. Ger baş be, Dest pê bike.')
            except core.Cancelled:self.status=self.t('Önizleme durduruldu.','Pêşdîtin hat rawestandin.')
            except Exception as e:self.error=self.error_text(e);self.status=self.t('Önizleme hazırlanamadı: ','Pêşdîtin nehat amadekirin: ')+self.error;self.log.append(traceback.format_exc()[-1500:])
            finally:
                with self.lock:self.busy=False;self.runner=None;self.progress=None
        threading.Thread(target=work,daemon=True).start()
    def cancel(self):
        r=self.runner
        if r:r.cancel();self.status=self.t('Durduruluyor…','Tê rawestandin…')
    def state(self):
        with self.lock:
            return {'mode':'desktop' if self.desktop else 'browser','version':VERSION,'busy':self.busy,'progress':self.progress,'status':self.status,'error':self.error,'results':self.results,'summary':self.summary,
                    'preview':self.preview,'files':[self.describe(k) for k in self.order if k in self.files],'output':str(self.output),'settings':{k:self.settings.get(k) for k in ('language','theme','accent')},
                    'history':history()[:60],'log':self.log[-150:],'platform':sys.platform}

# ------------------------------------------------------------------ history (shared with the GTK window)
def history_path():return runtime.config_dir()/'history.json'
def history():
    try:return json.loads(history_path().read_text(encoding='utf-8'))
    except Exception:return []
def remember(path,action):
    h=[{'path':str(path),'action':action,'time':time.time()}]+[x for x in history() if x.get('path')!=str(path)]
    try:history_path().parent.mkdir(parents=True,exist_ok=True);history_path().write_text(json.dumps(h[:80],ensure_ascii=False),encoding='utf-8')
    except OSError:pass

def open_path(path,reveal=False):
    path=Path(path)
    if sys.platform=='win32':
        if reveal:subprocess.Popen(['explorer','/select,',str(path)])
        else:os.startfile(str(path))
    elif sys.platform=='darwin':subprocess.Popen(['open','-R',str(path)] if reveal else ['open',str(path)])
    else:subprocess.Popen(['xdg-open',str(path.parent if reveal else path)])

# ------------------------------------------------------------------ HTTP
def make_handler(app,token):
    class Handler(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def log_message(self,*a):pass
        def allowed(self):
            host=self.headers.get('Host','');origin=self.headers.get('Origin')
            return host==f'127.0.0.1:{self.server.server_port}' and (not origin or origin=='http://'+host) and self.path.startswith('/'+token+'/')
        def send(self,status,body,ctype,extra=()):
            self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            for k,v in extra:self.send_header(k,v)
            self.end_headers();self.wfile.write(body)
        def reply(self,value,status=200):self.send(status,json.dumps(value,ensure_ascii=False).encode(),'application/json; charset=utf-8')
        def route(self):
            parts=urllib.parse.urlsplit(self.path);return parts.path[len(token)+2:],urllib.parse.parse_qs(parts.query)
        def do_GET(self):
            if not self.allowed():return self.reply({'error':'forbidden'},403)
            route,q=self.route();app.last_ping=time.monotonic()
            try:
                if route in ('','index.html'):
                    self.send(200,(HERE/'web'/'index.html').read_bytes(),'text/html; charset=utf-8',[('Content-Security-Policy',"default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'")])
                elif route=='state':self.reply(app.state())
                elif route=='base':self.reply(app.base(q['id'][0],int(q.get('page',['0'])[0]),float(q.get('at',['-1'])[0])))
                elif route=='media':self.media(q['id'][0],q.get('download',['0'])[0]=='1')
                else:self.reply({'error':'not_found'},404)
            except Exception as e:self.reply({'error':app.error_text(e)},400)
        def media(self,key,download):
            with app.lock:path=app.media.get(key)
            if path is None or not path.is_file():return self.reply({'error':'not_found'},404)
            size=path.stat().st_size;ctype=TYPES.get(path.suffix.lower(),'application/octet-stream');start,end=0,size-1;status=200
            rng=self.headers.get('Range','')
            if rng.startswith('bytes='):
                a,_,b=rng[6:].split(',')[0].partition('-')
                try:
                    if a:start=int(a);end=int(b) if b else size-1
                    else:start=max(0,size-int(b))
                    end=min(end,size-1);status=206
                except ValueError:pass
            self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(end-start+1));self.send_header('Cache-Control','no-store')
            if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            if download:self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+urllib.parse.quote(path.name))
            self.end_headers()
            with path.open('rb') as f:
                f.seek(start);left=end-start+1
                try:
                    while left>0:
                        chunk=f.read(min(left,1<<20))
                        if not chunk:break
                        self.wfile.write(chunk);left-=len(chunk)
                except (BrokenPipeError,ConnectionResetError):pass
        def do_POST(self):
            if not self.allowed():return self.reply({'error':'forbidden'},403)
            route,q=self.route();app.last_ping=time.monotonic()
            try:
                if route=='upload':
                    length=int(self.headers.get('Content-Length','0'));assert 0<length<=32*1024**3,'invalid_size'
                    name=urllib.parse.unquote(self.headers.get('X-Filename','dosya')).replace('\\','/').split('/')[-1] or 'dosya'
                    folder=app.work/'uploads'/secrets.token_hex(8);folder.mkdir(parents=True);p=folder/name
                    with p.open('wb') as f:
                        while length:
                            chunk=self.rfile.read(min(length,1<<20))
                            if not chunk:raise ValueError('incomplete_upload')
                            f.write(chunk);length-=len(chunk)
                    added,errors=app.add([p]);return self.reply({'ids':added,'errors':errors})
                length=int(self.headers.get('Content-Length','0'));assert length<8*1024*1024;data=json.loads(self.rfile.read(length) or b'{}')
                if route=='ping':return self.reply({'ok':True})
                if route=='cancel':app.cancel();return self.reply({'ok':True})
                if route=='settings':
                    for k in ('language','theme','accent'):
                        if k in data:app.settings[k]=data[k]
                    app.save();return self.reply({'ok':True})
                if route=='history_clear':history_path().unlink(missing_ok=True);return self.reply({'ok':True})
                if route=='remove':
                    with app.lock:app.files.pop(data['id'],None);app.order=[k for k in app.order if k!=data['id']]
                    return self.reply({'ok':True})
                if route=='clear':
                    with app.lock:app.files.clear();app.order.clear()
                    return self.reply({'ok':True})
                if route=='run':app.start(data);return self.reply({'ok':True})
                if route=='preview':app.make_preview(data);return self.reply({'ok':True})
                if route=='clear_preview':app.preview=None;return self.reply({'ok':True})
                if not app.desktop:return self.reply({'error':'not_found'},404)
                if route=='pick':
                    paths=ask(app,data.get('mode','files'))
                    added,errors=app.add(paths) if paths else ([],[])
                    return self.reply({'ids':added,'errors':errors})
                if route=='pick_output':
                    paths=ask(app,'folder',title=app.t('Kayıt klasörü','Peldanka tomarkirinê'))
                    if paths:app.output=Path(paths[0]);app.settings['output']=str(app.output);app.save()
                    return self.reply({'output':str(app.output)})
                if route in ('open','reveal'):
                    path=Path(data['path']) if data.get('path') else app.output
                    open_path(path,route=='reveal');return self.reply({'ok':True})
                return self.reply({'error':'not_found'},404)
            except Exception as e:
                app.log.append(traceback.format_exc()[-1200:]);self.reply({'error':app.error_text(e) if not isinstance(e,AssertionError) else str(e)},400)
    return Handler

# ------------------------------------------------------------------ native dialogs (Tk must live on the main thread)
def ask(app,mode,title=None):
    reply=queue.Queue();app.dialogs.put((mode,title,reply))
    return reply.get()
def dialog_loop(app,stop):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk()
    except Exception:
        # No Tk (or no display): the page still works with drag and drop.
        while not stop.wait(0.2):
            try:app.dialogs.get_nowait()[2].put([])
            except queue.Empty:pass
        return
    root.withdraw()
    def poll():
        if stop.is_set():root.quit();return
        try:
            while True:
                mode,title,reply=app.dialogs.get_nowait()
                root.attributes('-topmost',True);root.lift();root.update()
                try:
                    if mode=='folder':value=filedialog.askdirectory(parent=root,title=title or app.t('Klasör seç','Peldankê hilbijêre'));value=[value] if value else []
                    else:value=list(filedialog.askopenfilenames(parent=root,title=title or app.t('Dosya seç','Dosye hilbijêre')))
                except Exception:value=[]
                reply.put(value)
        except queue.Empty:pass
        root.after(120,poll)
    root.after(120,poll);root.mainloop()
    try:root.destroy()
    except Exception:pass

# ------------------------------------------------------------------ app window
def browser_command(url,profile):
    """An app-style window of a Chromium browser (no address bar), when one is installed."""
    candidates=[]
    if sys.platform=='win32':
        for base in (os.environ.get('ProgramFiles(x86)'),os.environ.get('ProgramFiles'),os.environ.get('LOCALAPPDATA')):
            if base:candidates+=[Path(base)/'Microsoft/Edge/Application/msedge.exe',Path(base)/'Google/Chrome/Application/chrome.exe',Path(base)/'BraveSoftware/Brave-Browser/Application/brave.exe']
    elif sys.platform=='darwin':
        for app in ('Google Chrome','Microsoft Edge','Brave Browser','Chromium'):candidates.append(Path('/Applications')/(app+'.app')/'Contents/MacOS'/app)
    else:
        for name in ('microsoft-edge','google-chrome','chromium','chromium-browser','brave-browser'):
            found=shutil.which(name)
            if found:candidates.append(Path(found))
    for c in candidates:
        if c.is_file():return [str(c),'--app='+url,'--user-data-dir='+str(profile),'--no-first-run','--no-default-browser-check','--window-size=1280,880','--disable-features=Translate']
    return None

def serve(desktop=True,open_window=True,port=0,paths=()):
    app=Studio(desktop);token=secrets.token_urlsafe(24)
    server=ThreadingHTTPServer(('127.0.0.1',port),make_handler(app,token));server.daemon_threads=True
    url=f'http://127.0.0.1:{server.server_port}/{token}/'
    if paths:app.add(paths)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    print('Dönüştürücü: '+url,flush=True)
    stop=threading.Event();window=None
    if open_window:
        command=browser_command(url,runtime.config_dir()/'pencere')
        if command:
            try:window=subprocess.Popen(command)
            except OSError:window=None
        if window is None:
            import webbrowser;webbrowser.open(url)
    def watch():
        # Close with the app window; without one, after the page has been gone for a while.
        while not stop.is_set():
            time.sleep(1)
            if window is not None and window.poll() is not None and not app.busy:break
            if window is None and open_window and time.monotonic()-app.last_ping>120 and not app.busy:break
        stop.set()
    threading.Thread(target=watch,daemon=True).start()
    try:
        if desktop:dialog_loop(app,stop)
        else:stop.wait()
    except KeyboardInterrupt:pass
    finally:
        stop.set();app.cancel();server.shutdown();server.server_close();shutil.rmtree(app.work,ignore_errors=True)
    return url

def main():
    args=[a for a in sys.argv[1:]]
    desktop='--browser' not in args;open_window='--no-window' not in args
    port=0
    if '--port' in args:port=int(args[args.index('--port')+1])
    paths=[a for a in args if not a.startswith('--') and Path(a).exists()]
    serve(desktop,open_window,port,paths)

if __name__=='__main__':main()
