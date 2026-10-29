"""Local conversion engine. No network clients, no shell command evaluation."""
from __future__ import annotations
import codecs
import errno
import dataclasses
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import zipfile
from . import runtime

class ConversionError(Exception):
    def __init__(self, code, detail=''):
        self.code, self.detail = code, detail
        super().__init__(f'{code}: {detail}')

class Cancelled(ConversionError):
    def __init__(self):
        super().__init__('cancelled')

@dataclasses.dataclass
class FileInfo:
    path: Path
    kind: str
    fmt: str
    duration: float = 0
    has_audio: bool = False
    width: int = 0
    height: int = 0

@dataclasses.dataclass
class Options:
    quality: str = 'original'
    resolution: str = 'original'
    bitrate: str = 'auto'
    only_text: bool = False
    ocr: bool = False
    ocr_language: str = 'tur+eng'

DOC = {'docx','doc','odt','rtf','txt','html','epub','pdf'}
SHEET = {'xlsx','xls','ods','csv','tsv','pdf','html'}
SLIDES = {'pptx','ppt','odp','pdf'}
TEXT_EXPORT = {'md','rst','fb2'}
AUDIO = {'mp3','wav','flac','ogg','opus','m4a','aac','aiff','wma'}
VIDEO = {'mp4','mkv','webm','avi','mov','mpeg','ts','gif'}
TEXT_INPUT = {'srt','txt','md','rst','csv','tsv','html','htm','rtf','tex','fb2'}
DOCUMENT_INPUT = {'doc','docx','odt','ott','dot','dotx','docm','wps','abw','rtf','txt','html','htm','epub','md','rst','fb2'}
SHEET_INPUT = {'xls','xlsx','xlsm','xlsb','ods','ots','csv','tsv'}
SLIDE_INPUT = {'ppt','pptx','pptm','pps','ppsx','odp','otp'}
# Explicit export filters avoid choosing an incompatible LibreOffice component.
FILTERS = {
 'document': {'docx':'Office Open XML Text','doc':'MS Word 97','odt':'writer8','rtf':'Rich Text Format','txt':'Text (encoded):UTF8','html':'HTML (StarWriter):EmbedImages','epub':'EPUB','pdf':'writer_pdf_Export'},
 'spreadsheet': {'xlsx':'Calc MS Excel 2007 XML','xls':'MS Excel 97','ods':'calc8','csv':'Text - txt - csv (StarCalc):44,34,76,1','tsv':'Text - txt - csv (StarCalc):9,34,76,1','pdf':'calc_pdf_Export','html':'HTML (StarCalc)'},
 'presentation': {'pptx':'Impress MS PowerPoint 2007 XML','ppt':'MS PowerPoint 97','odp':'impress8','pdf':'impress_pdf_Export'}
}

def tools():
    return {x: runtime.available(x) for x in ('ffmpeg','ffprobe','libreoffice','pandoc','pdftotext','pypdf','tesseract','pdftoppm')}

def _capture(args, timeout=25):
    try:
        return subprocess.run(runtime.resolve_command(args), stdin=subprocess.DEVNULL, capture_output=True, text=True, errors='replace', timeout=timeout, **({'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}))
    except FileNotFoundError as e:
        raise ConversionError('missing_tool', args[0]) from e
    except subprocess.TimeoutExpired as e:
        raise ConversionError('probe_timeout') from e

def _text_format(path, head):
    if re.match(br'(?:\xef\xbb\xbf)?\s*\d+\r?\n\d{2,}:[0-5]\d:[0-5]\d,\d{3} --> ',head):return 'srt'
    if head.lstrip().startswith(b'{\\rtf'): return 'rtf'
    if re.search(br'<(?:!doctype\s+html|html)\b', head.lower()): return 'html'
    if b'\x00' in head and not head.startswith((b'\xff\xfe',b'\xfe\xff')): return None
    try:
        codecs.getincrementaldecoder('utf-16' if head.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8')().decode(head,final=False)
    except UnicodeError:
        return None
    ext = path.suffix.lower().lstrip('.')
    return ext if ext in TEXT_INPUT else 'txt'

def expand_paths(paths):
    """Snapshot recursive folder input; never follow directory or file symlinks in a folder."""
    seen=set()
    for value in paths:
        path=Path(value).expanduser()
        if path.is_dir():
            problems=[]
            for base,dirs,names in os.walk(path,followlinks=False,onerror=lambda e:problems.append(Path(e.filename))):
                dirs[:]=sorted(d for d in dirs if not (Path(base)/d).is_symlink())
                for name in sorted(names):
                    file=Path(base)/name
                    if file.is_symlink():continue
                    resolved=file.resolve()
                    if resolved not in seen:seen.add(resolved);yield resolved
            for problem in problems:yield problem
        else:
            resolved=path.resolve()
            if resolved not in seen:seen.add(resolved);yield resolved

def detect(filename):
    path = Path(filename).expanduser().resolve()
    if not path.is_file(): raise ConversionError('not_file',str(path))
    if not path.stat().st_size: raise ConversionError('empty_file')
    with path.open('rb') as f: head=f.read(8192)
    ext=path.suffix.lower().lstrip('.')
    if head.startswith(b'%PDF-'): return FileInfo(path,'pdf','pdf')
    if head.startswith(b'PK'):
        try:
            with zipfile.ZipFile(path) as z:
                names=set(z.namelist())
                if 'mimetype' in names:
                    mime=z.read('mimetype')[:200].decode(errors='replace')
                    if mime=='application/epub+zip': return FileInfo(path,'ebook','epub')
                    if mime.startswith('application/vnd.oasis.opendocument.'):
                        kind='spreadsheet' if 'spreadsheet' in mime else 'presentation' if 'presentation' in mime else 'document'
                        return FileInfo(path,kind,{'document':'odt','spreadsheet':'ods','presentation':'odp'}[kind])
                for prefix,kind,fmt in [('word/','document','docx'),('xl/','spreadsheet','xlsx'),('ppt/','presentation','pptx')]:
                    if any(n.startswith(prefix) for n in names): return FileInfo(path,kind,fmt)
        except (zipfile.BadZipFile,RuntimeError,KeyError): pass
        raise ConversionError('unsupported','ZIP')
    if head.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
        # libmagic inspects OLE contents rather than trusting the extension.
        if runtime.available('file'):
            mime=_capture(['file','--brief','--mime-type','--',str(path)]).stdout.strip()
            for hint,kind,fmt in [('msword','document','doc'),('ms-excel','spreadsheet','xls'),('ms-powerpoint','presentation','ppt')]:
                if hint in mime: return FileInfo(path,kind,fmt)
        if ext in DOCUMENT_INPUT|SHEET_INPUT|SLIDE_INPUT:
            return FileInfo(path,'spreadsheet' if ext in SHEET_INPUT else 'presentation' if ext in SLIDE_INPUT else 'document',ext)
        raise ConversionError('unsupported','OLE')
    textfmt=_text_format(path,head)
    # Raw audio demuxers can accept arbitrary ASCII as low-confidence audio.
    # Prefer valid text before probing media; UTF-8 controls exclude binary data.
    if textfmt and not any(byte < 32 and byte not in (9,10,12,13,27) for byte in head):
        return FileInfo(path,'spreadsheet' if textfmt in {'csv','tsv'} else 'document',textfmt)
    # Probe containers/streams. Audio-only M4A, attached album art, and silent video
    # are distinguished using stream metadata, not their suffix.
    if runtime.available('ffprobe'):
        probe=_capture(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_format','-show_streams','-of','json',str(path)])
        if probe.returncode==0:
            data=json.loads(probe.stdout)
            streams=data.get('streams',[])
            audio=any(s.get('codec_type')=='audio' for s in streams)
            videos=[s for s in streams if s.get('codec_type')=='video' and not s.get('disposition',{}).get('attached_pic')]
            container=data.get('format',{})
            fmt=container.get('format_name','').split(',')[0]
            if fmt=='mov':
                brand=container.get('tags',{}).get('major_brand','').strip()
                fmt='mov' if brand=='qt' else 'm4a' if brand.startswith('M4A') else '3gp' if brand.startswith('3gp') else 'mp4'
            elif fmt=='matroska': fmt='webm' if b'webm' in head[:256] else 'mkv'
            elif fmt=='asf' and audio and not videos: fmt='wma'
            elif fmt=='ogg' and any(s.get('codec_name')=='opus' for s in streams): fmt='opus'
            try: duration=float(data.get('format',{}).get('duration',0))
            except (TypeError,ValueError): duration=0
            # Single still images are outside the media-conversion workflow.
            still=fmt.endswith('_pipe') or fmt=='image2'
            if videos and not still:
                return FileInfo(path,'video',fmt,duration,audio,int(videos[0].get('width',0)),int(videos[0].get('height',0)))
            if audio: return FileInfo(path,'audio',fmt,duration,True)
    textfmt=_text_format(path,head)
    if textfmt:
        return FileInfo(path,'spreadsheet' if textfmt in {'csv','tsv'} else 'document',textfmt)
    if ext in {'wps','abw'}: return FileInfo(path,'document',ext)
    raise ConversionError('unsupported',ext.upper() or '?')

def targets(info):
    if info.fmt=='srt':return ['txt']
    if info.kind=='audio': return sorted(AUDIO)
    if info.kind=='video': return sorted(VIDEO | (AUDIO if info.has_audio else set()))
    if info.kind=='spreadsheet': return sorted(SHEET | DOC | TEXT_EXPORT)
    if info.kind=='presentation': return sorted(SLIDES | DOC | TEXT_EXPORT)
    return sorted(DOC | TEXT_EXPORT)

def required_tools(info, target, options=None):
    options=options or Options()
    if info.kind in {'audio','video'}: return ['ffmpeg','ffprobe']
    if info.fmt=='srt' and target=='txt':return []
    req=[]
    if info.kind=='pdf': req.append('pdftotext' if runtime.available('pdftotext') else 'pypdf')
    if info.kind=='ebook' or info.fmt in {'md','rst','fb2'} or target in {'md','rst','fb2'}: req.append('pandoc')
    if not (info.kind=='pdf' and target=='txt'): req.append('libreoffice')
    if options.ocr and text_options_apply(info,target):
        req.append('tesseract')
        if info.kind=='pdf':req += ['pdftoppm','pypdf']
    return list(dict.fromkeys(req))

def text_options_apply(info,target):
    return info.kind in {'pdf','presentation','spreadsheet','document'} and info.fmt not in {'md','rst','fb2'} and target in DOC|TEXT_EXPORT

class Runner:
    def __init__(self, progress=lambda fraction: None):
        self.progress=progress
        self.notes=[]  # e.g. ('auto_ocr', ocr_pages, total_pages) for the UI log
        self.cancelled=threading.Event()
        self.process=None
        self._lock=threading.Lock()

    def cancel(self):
        self.cancelled.set()
        with self._lock:
            if self.process and self.process.poll() is None:
                runtime.terminate_tree(self.process)

    def check(self):
        if self.cancelled.is_set(): raise Cancelled()

    def run(self,args,duration=0,timeout=1800):
        self.check()
        args=runtime.isolate(args)
        with tempfile.TemporaryDirectory(prefix='donustur-log-') as logdir:
            logpath=Path(logdir)/'process.log'
            with logpath.open('w+b') as log:
                with self._lock:
                    self.process=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=runtime.process_env(),**runtime.popen_options())
                    runtime.lower_priority(self.process.pid)
                proc=self.process
                started=time.monotonic(); cancelled_at=None
                while proc.poll() is None:
                    if self.cancelled.is_set():
                        if cancelled_at is None:
                            cancelled_at=time.monotonic()
                            runtime.terminate_tree(proc)
                        elif time.monotonic()-cancelled_at>2:
                            runtime.terminate_tree(proc,force=True)
                    if time.monotonic()-started>timeout:
                        runtime.terminate_tree(proc,force=True); proc.wait(); log.close()
                        raise ConversionError('timeout')
                    if duration:
                        # An independent reader works on Windows and never moves the writer offset.
                        tail=self._tail(logpath,8192)
                        times=re.findall(r'out_time_us=(\d+)',tail)
                        if times: self.progress(min(.99,int(times[-1])/1_000_000/duration))
                    time.sleep(.12)
                log.close()
                with self._lock: self.process=None
                self.check()
                if proc.returncode:
                    detail=self._tail(logpath,5000)
                    raise ConversionError('conversion_failed',detail)

    @staticmethod
    def _tail(path,size):
        with path.open('rb') as reader:
            reader.seek(max(0,path.stat().st_size-size))
            return reader.read(size).decode('utf-8',errors='replace')

    def convert(self,info,target,directory,options=None):
        self.check(); options=options or Options()
        if target not in targets(info): raise ConversionError('invalid_target',target)
        for tool in required_tools(info,target,options):
            if not runtime.available(tool): raise ConversionError('missing_tool',tool)
        directory=Path(directory).expanduser().resolve()
        directory.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.donustur-',dir=directory) as work:
            work=Path(work)
            if info.fmt=='srt' and target=='txt':
                from .subtitles import export_text
                product=work/'result.txt';product.write_text(export_text(info.path),encoding='utf-8')
            elif info.kind in {'audio','video'}:
                product=work/('result.'+target)
                self._media(info,target,product,options)
            else:
                product=self._document(info,target,work,options)
            self.check()
            if not product.is_file() or not product.stat().st_size:
                raise ConversionError('no_output')
            # Atomic publish with no overwrite, even if two app instances finish together.
            stem=info.path.stem
            for count in range(10000):
                name=f'{stem}{"" if count==0 else " ("+str(count)+")"}.{target}'
                result=directory/name
                try:
                    os.link(product,result)
                    self.progress(1)
                    return result
                except FileExistsError: continue
                except OSError as e:
                    if e.errno not in {errno.EPERM,errno.EOPNOTSUPP,errno.EXDEV,errno.ENOSYS}:raise
                    # FAT/exFAT and some Windows volumes do not support links.
                    try:
                        with result.open('xb') as dst,product.open('rb') as src:
                            try:
                                while chunk:=src.read(1024*1024):self.check();dst.write(chunk)
                            except BaseException:
                                dst.close();result.unlink(missing_ok=True);raise
                        self.progress(1);return result
                    except FileExistsError:continue
            raise ConversionError('name_conflict')

    def _media(self,info,target,out,opt):
        if opt.bitrate=='auto' and target!='gif':
            return self._media_original(info,target,out,opt)
        if opt.bitrate=='auto':opt=dataclasses.replace(opt,bitrate='192k')
        args=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-protocol_whitelist','file,pipe','-i',str(info.path)]
        if target in AUDIO:
            args+=['-map','0:a:0','-vn','-sn','-dn']
            codecs={'mp3':'libmp3lame','wav':'pcm_s16le','flac':'flac','ogg':'libvorbis','opus':'libopus','m4a':'aac','aac':'aac','aiff':'pcm_s16be','wma':'wmav2'}
            args+=['-c:a',codecs[target]]
            if target not in {'wav','flac','aiff'}:
                args+=['-b:a',opt.bitrate]
            if target in {'opus','wma','ogg'}: args+=['-ac','2','-ar','48000' if target in {'opus','ogg'} else '44100']
        elif target=='gif':
            height={'original':info.height or 480,'1080':1080,'720':720,'480':480}.get(opt.resolution,480)
            prefix='' if opt.quality=='original' else f'fps=12,scale=-2:min({height}\\,ih):flags=lanczos,'
            args+=['-filter_complex',f'[0:v:0]{prefix}split[a][b];[a]palettegen[p];[b][p]paletteuse', '-an','-loop','0']
        else:
            args+=['-map','0:v:0','-map','0:a:0?','-sn','-dn']
            filters=[]
            if opt.resolution!='original': filters.append(f'scale=-2:min({int(opt.resolution)}\\,ih)')
            # H.264/YUV420 requires even dimensions, including unusual phone clips.
            filters.append('pad=ceil(iw/2)*2:ceil(ih/2)*2')
            args+=['-vf',','.join(filters)]
            crf={'small':'29','balanced':'23','high':'18'}[opt.quality]
            if target=='webm': args+=['-c:v','libvpx-vp9','-crf',crf,'-b:v','0','-deadline','good','-cpu-used','4','-c:a','libopus','-ac','2','-ar','48000']
            elif target=='avi': args+=['-c:v','mpeg4','-q:v',{'small':'8','balanced':'5','high':'2'}[opt.quality],'-c:a','libmp3lame']
            elif target=='mpeg': args+=['-c:v','mpeg2video','-q:v','4','-c:a','mp2','-ar','48000']
            else:
                args+=['-c:v','libx264','-preset','medium','-crf',crf,'-pix_fmt','yuv420p','-c:a','aac']
                if target in {'mp4','mov'}: args+=['-movflags','+faststart']
                if target=='ts': args+=['-f','mpegts']
            args+=['-b:a',opt.bitrate]
        args+=['-progress','pipe:1','-y',str(out)]
        self.run(args,duration=info.duration,timeout=24*3600)

    def _media_original(self,info,target,out,opt=None):
        opt=opt or Options()
        probe=_capture(['ffprobe','-v','error','-show_streams','-of','json',str(info.path)])
        streams=json.loads(probe.stdout).get('streams',[])
        audio=next((s for s in streams if s.get('codec_type')=='audio'),None)
        video=next((s for s in streams if s.get('codec_type')=='video' and not s.get('disposition',{}).get('attached_pic')),None)
        args=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-fflags','+genpts','-protocol_whitelist','file,pipe','-i',str(info.path)]
        video_ok={'mp4':{'h264','hevc','av1','mpeg4'},'mov':{'h264','hevc','mpeg4','prores'},'mkv':{'*'},'webm':{'vp8','vp9','av1'},'avi':{'mpeg4','mjpeg'},'mpeg':{'mpeg1video','mpeg2video'},'ts':{'h264','hevc','mpeg2video'}}
        audio_ok={'mp3':{'mp3'},'wav':{'pcm_s16le','pcm_s24le','pcm_s32le','pcm_f32le'},'flac':{'flac'},'ogg':{'vorbis'},'opus':{'opus'},'m4a':{'aac','alac'},'aac':{'aac'},'aiff':{'pcm_s16be','pcm_s24be','pcm_s32be'},'wma':{'wmav1','wmav2'},'mp4':{'aac','mp3','alac'},'mov':{'aac','mp3','alac','pcm_s16le'},'mkv':{'*'},'webm':{'opus','vorbis'},'avi':{'mp3','pcm_s16le'},'mpeg':{'mp2','mp3'},'ts':{'aac','mp2','mp3'}}
        if target in VIDEO:
            args+=['-map','0:v:0','-map','0:a:0?','-sn','-dn']
            allowed=video_ok[target]
            if opt.quality=='original' and opt.resolution=='original' and ('*' in allowed or video.get('codec_name') in allowed):args+=['-c:v','copy']
            else:
                codec={'webm':'libvpx-vp9','avi':'mpeg4','mpeg':'mpeg2video'}.get(target,'libx264')
                filt='pad=ceil(iw/2)*2:ceil(ih/2)*2'
                if opt.resolution!='original':filt=f'scale=-2:min({int(opt.resolution)}\\,ih),'+filt
                args+=['-c:v',codec,'-vf',filt]
                crf={'original':'18','small':'29','balanced':'23','high':'18'}[opt.quality]
                if codec=='libx264':args+=['-crf',crf,'-preset','medium','-pix_fmt','yuv420p']
                elif codec=='libvpx-vp9':args+=['-crf',crf,'-b:v','0','-cpu-used','4']
                else:args+=['-q:v',{'original':'2','small':'8','balanced':'5','high':'2'}[opt.quality]]
        else:args+=['-map','0:a:0','-vn','-sn','-dn']
        if audio:
            allowed=audio_ok[target]
            if '*' in allowed or audio.get('codec_name') in allowed:args+=['-c:a','copy']
            else:
                codec={'mp3':'libmp3lame','wav':'pcm_s16le','flac':'flac','ogg':'libvorbis','opus':'libopus','aiff':'pcm_s16be','wma':'wmav2','webm':'libopus','avi':'libmp3lame','mpeg':'mp2'}.get(target,'aac')
                args+=['-c:a',codec]
                try:rate=int(audio.get('bit_rate',0))
                except (ValueError,TypeError):rate=0
                if codec=='libmp3lame':
                    if rate:args+=['-b:a',str(min([32000,40000,48000,56000,64000,80000,96000,112000,128000,160000,192000,224000,256000,320000],key=lambda x:abs(x-rate)))]
                    else:args+=['-q:a','2']
                elif codec=='libopus':
                    args+=['-ar','48000']
                    if rate:args+=['-b:a',str(max(6000,min(rate,256000*int(audio.get('channels',1)))))]
                elif codec=='libvorbis':args+=['-q:a','6']
                elif codec=='wmav2':args+=['-ar','44100','-ac','2','-b:a',str(max(32000,min(rate or 128000,320000)))]
                elif codec=='mp2':args+=['-ar','48000','-b:a',str(min([64000,96000,128000,160000,192000,224000,256000,320000,384000],key=lambda x:abs(x-(rate or 192000))))]
                elif codec=='aac' and rate:args+=['-b:a',str(max(16000,min(rate,512000)))]
        if target in {'mp4','mov','m4a'}:args+=['-movflags','+faststart']
        if target=='ts':args+=['-f','mpegts']
        args+=['-progress','pipe:1','-y',str(out)]
        self.run(args,duration=info.duration,timeout=24*3600)

    def _ocr_image_pages(self,pdf,extracted,work,options):
        """Pages whose text is only drawn as pictures (scans, Word 'print as image') are read with OCR."""
        from .ocr import meaningful,page_text
        pages=extracted.read_text(encoding='utf-8').split('\f')
        if pages and not pages[-1].strip():pages=pages[:-1]
        if not pages:
            from pypdf import PdfReader
            pages=['']*len(PdfReader(pdf).pages)
        image_pages=[n for n,text in enumerate(pages) if meaningful(text)<20]
        if not image_pages:return
        if not (runtime.available('tesseract') and runtime.available('pdftoppm')):
            if all(meaningful(t)<20 for t in pages):raise ConversionError('pdf_no_text')
            return
        for done,n in enumerate(image_pages,1):
            self.check();pages[n]=page_text(self,pdf,n,work,options.ocr_language)
            self.progress(min(.9,done/len(image_pages)))
        self.notes.append(('auto_ocr',len(image_pages),len(pages)))
        extracted.write_text('\n\n'.join(pages),encoding='utf-8')
    def _office(self,source,target,kind,work):
        export=work/'export'; export.mkdir(exist_ok=True)
        profile=work/'profile'; (profile/'user').mkdir(parents=True,exist_ok=True)
        (profile/'user/registrymodifications.xcu').write_text('''<?xml version="1.0"?><oor:items xmlns:oor="http://openoffice.org/2001/registry"><item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item><item oor:path="/org.openoffice.Office.Common/Load"><prop oor:name="UpdateDocMode" oor:op="fuse"><value>0</value></prop></item></oor:items>''',encoding='utf-8')
        self.run(['libreoffice','-env:UserInstallation='+profile.as_uri(),'--headless','--nologo','--nodefault','--nolockcheck','--norestore','--convert-to',target+':'+FILTERS[kind][target],'--outdir',str(export),str(source)])
        result=export/(source.stem+'.'+target)
        if not result.exists(): raise ConversionError('no_output')
        if target=='epub':
            from .text_layout import fix_epub_direction
            fix_epub_direction(result)
        return result

    def _document(self,info,target,work,options=None):
        options=options or Options()
        source=info.path; kind=info.kind
        if kind=='pdf':
            source=work/'extracted.txt'
            if options.ocr:
                from .ocr import pdf_text
                source.write_text(pdf_text(self,info.path,work,options.ocr_language),encoding='utf-8')
            elif runtime.available('pdftotext'):
                self.run(['pdftotext','-layout','-enc','UTF-8',str(info.path),str(source)])
            else:
                from pypdf import PdfReader
                reader=PdfReader(info.path)
                if reader.is_encrypted:raise ConversionError('encrypted')
                pages=[]
                for page in reader.pages:self.check();pages.append(page.extract_text() or '')
                source.write_text('\n\n'.join(pages),encoding='utf-8')
            if not options.ocr:self._ocr_image_pages(info.path,source,work,options)
            if not source.read_text(encoding='utf-8').strip(): raise ConversionError('ocr_no_text' if options.ocr else 'pdf_no_text')
            if target=='txt': return source
            kind='document'
        if source.suffix.lower()=='.txt' and kind=='document':
            from .text_layout import read_text,has_rtl,text_to_html
            content=read_text(source)
            if target=='txt':
                out=work/'unicode.txt';out.write_text(content,encoding='utf-8');return out
            if has_rtl(content):source=text_to_html(content,work/'rtl.html',info.path.stem)
        if kind=='presentation' and (target not in SLIDES or (target=='pdf' and (options.only_text or options.ocr))):
            from .office_text import office_to_html
            source=office_to_html(self,info,work,options);kind='document'
        elif kind=='spreadsheet' and (target not in SHEET or (target in {'pdf','html'} and (options.only_text or options.ocr))):
            from .office_text import office_to_html
            source=office_to_html(self,info,work,options);kind='document'
        elif kind=='document' and source==info.path and (options.only_text or options.ocr) and info.fmt not in {'md','rst','fb2'}:
            from .office_text import office_to_html
            source=office_to_html(self,info,work,options);kind='document'
        if info.fmt=='fb2':
            from .text_layout import fb2_to_html
            source=fb2_to_html(info.path,work/'prepared.html');kind='document'
        elif kind=='ebook' or info.fmt in {'md','rst'}:
            source=work/'prepared.html'
            template=work/'body-only.html';template.write_text('<!DOCTYPE html><html><head><meta charset="utf-8"/><title>$pagetitle$</title></head><body>$body$</body></html>',encoding='utf-8')
            self.run(['pandoc','--sandbox','--from',('epub' if info.kind=='ebook' else 'markdown' if info.fmt=='md' else info.fmt),'--to','html','--standalone','--embed-resources','--template',str(template),'--metadata','pagetitle='+info.path.stem,str(info.path),'--output',str(source)])
            from .text_layout import ensure_html_direction
            ensure_html_direction(source)
            kind='document'
        if target in {'md','rst','fb2'}:
            intermediate=source
            if intermediate.suffix.lower() not in {'.docx','.odt','.html','.epub','.md','.rst','.txt'}:
                intermediate=self._office(source,'docx','document',work)
            out=work/('result.'+target)
            reader='markdown' if intermediate.suffix=='.txt' else 'html' if intermediate.suffix=='.html' else 'markdown' if intermediate.suffix=='.md' else intermediate.suffix.lstrip('.')
            self.run(['pandoc','--sandbox','--from',reader,'--to',('markdown' if target=='md' else target),'--standalone',str(intermediate),'--output',str(out)])
            if target=='fb2':
                # PDF text can contain form-feed/page separators. Pandoc emits
                # them literally, although XML 1.0 forbids those control codes.
                xml=out.read_text(encoding='utf-8')
                xml=re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]',lambda m:'\n' if m[0] in '\x0b\x0c' else '',xml)
                out.write_text(xml,encoding='utf-8')
            return out
        # Work with content-derived suffixes, including intentionally misnamed OOXML files.
        if kind not in FILTERS: kind='document'
        if source==info.path:
            suffix=info.fmt if info.fmt in DOCUMENT_INPUT|SHEET_INPUT|SLIDE_INPUT else info.path.suffix.lstrip('.')
            normalized=work/('source.'+suffix)
            shutil.copyfile(source,normalized); source=normalized
        return self._office(source,target,kind,work)
