"""Every file type × every operation × every output format the desktop app offers.

    python3 tests/full_desktop_test.py [report.json] [--real-pdf PATH]

Uses the same engine calls as the windows: core.detect (adding files), Runner.convert
(main window target formats, incl. text-only/OCR options) and Editor.execute (extras).
Includes real-world media (broken tags, cover art, phone HEVC, multi-track MKV).
"""
from pathlib import Path
import json,shutil,subprocess,sys,tempfile,time,traceback
ROOT=Path(__file__).resolve().parents[1]
from donusturucu import core,runtime
from donusturucu.operations import Editor,Request,actions
from donusturucu.speech import SpeechUnavailable

AUDIO={'mp3','wav','flac','ogg','opus','m4a','aac','aiff','wma'}
def ff(*args):subprocess.run([runtime.tool_path('ffmpeg') or 'ffmpeg','-v','error',*map(str,args),'-y'],check=True)

def inputs(work,real_pdf):
    speech=ROOT/'assets/selftest/english.mp3'
    files={}
    files['video.mp4']=work/'video.mp4';ff('-f','lavfi','-i','testsrc=s=640x360:r=25:d=5','-i',speech,'-shortest','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',files['video.mp4'])
    files['silent.mp4']=work/'silent.mp4';ff('-f','lavfi','-i','testsrc=s=640x360:r=25:d=4','-c:v','libx264','-pix_fmt','yuv420p',files['silent.mp4'])
    files['speech.mp3']=work/'speech.mp3';shutil.copy(speech,files['speech.mp3'])
    for ext,codec in [('wav','pcm_s16le'),('m4a','aac')]:
        files['speech.'+ext]=work/('speech.'+ext);ff('-i',speech,'-c:a',codec,files['speech.'+ext])
    body='Dönüştürücü tam test belgesi.\nMerhaba dünya — Silav cîhan! Çğış ÇĞİŞ 12345\n\nİkinci paragraf: belgeler, sesler ve videolar.\n'
    for name,text in [('belge.txt',body),('belge.md','# Başlık\n\n'+body),('belge.rst','Başlık\n======\n\n'+body),('belge.html','<html><body><h1>Başlık</h1><p>'+body.replace('\n','<br>')+'</p></body></html>'),
                      ('tablo.csv','Ad,Sayı\nElma,3\nArmut,5\n'),('altyazi.srt','1\n00:00:00,500 --> 00:00:02,000\nMerhaba dünya\n\n2\n00:00:02,500 --> 00:00:04,000\nSilav cîhan\n\n'),('ceviri.txt','Hello world\nHello again\n')]:
        (work/name).write_text(text,encoding='utf-8');files[name]=work/name
    made=work/'made';r=core.Runner()
    for target in ['docx','odt','rtf','epub','pdf']:
        out=r.convert(core.detect(files['belge.txt']),target,made);files['belge.'+target]=out.rename(work/('belge.'+target))
    for target in ['xlsx','ods']:
        out=r.convert(core.detect(files['tablo.csv']),target,made);files['tablo.'+target]=out.rename(work/('tablo.'+target))
    fodp=work/'sunu.fodp';fodp.write_text('''<?xml version="1.0" encoding="UTF-8"?><office:document xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:presentation="urn:oasis:names:tc:opendocument:xmlns:presentation:1.0" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" office:version="1.3" office:mimetype="application/vnd.oasis.opendocument.presentation"><office:body><office:presentation><draw:page draw:name="s1"><draw:frame svg:width="20cm" svg:height="3cm" svg:x="2cm" svg:y="2cm"><draw:text-box><text:p>Sunu başlığı — Silav</text:p></draw:text-box></draw:frame></draw:page></office:presentation></office:body></office:document>''',encoding='utf-8')
    for target in ['pptx','odp']:
        subprocess.run([*runtime.resolve_command(['libreoffice']),'--headless','-env:UserInstallation='+(work/'lo').as_uri(),'--convert-to',target,'--outdir',str(work),str(fodp)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        files['sunu.'+target]=work/('sunu.'+target)
    for f in sorted((ROOT/'tests/fixtures-real').iterdir()):files[f.name]=f
    if real_pdf and Path(real_pdf).is_file():files['gercek-resim-yazi.pdf']=Path(real_pdf)
    return files

def expected(action,target,info,src):
    if action=='convert':return target
    if action in {'subtitle_text'}:return 'txt'
    if action=='subtitle_restore':return 'srt'
    if action=='transcribe':return None
    if action=='extract_audio':return 'mp3'
    if action=='frame':return 'png'
    if action=='gif':return 'gif'
    if info.kind in {'pdf','document','presentation','spreadsheet','ebook'}:return 'pdf'
    if info.kind=='video':return 'mp4'
    return src.suffix[1:].lower()

def main():
    args=[a for a in sys.argv[1:] if not a.startswith('--')];real_pdf=None
    if '--real-pdf' in sys.argv:real_pdf=sys.argv[sys.argv.index('--real-pdf')+1];args=[a for a in args if a!=real_pdf]
    report=Path(args[0]) if args else None;rows=[]
    def record(case,func):
        t=time.monotonic()
        try:detail=func();ok=True
        except Exception as e:detail=f'{type(e).__name__}: {e}';ok=False
        rows.append({'case':case,'pass':ok,'detail':str(detail)[:200],'s':round(time.monotonic()-t,1)})
        if not ok:print('FAIL',case,'|',str(detail)[:200],flush=True)
    with tempfile.TemporaryDirectory(prefix='donustur-full-') as tmp:
        work=Path(tmp);files=inputs(work,real_pdf);out=work/'out';speech=files['speech.mp3'];srt=files['altyazi.srt']
        for name,path in files.items():
            info=None
            def detect():
                nonlocal info;info=core.detect(path);ext=path.suffix[1:].lower()
                if ext in AUDIO and info.kind!='audio':raise AssertionError(f'ses olarak tanınmadı: {info.kind}')
                if ext in {'mp4','mkv','mov','webm','avi'} and info.kind!='video':raise AssertionError(f'video olarak tanınmadı: {info.kind}')
                return f'{info.kind}/{info.fmt}'
            record(f'{name} · tür tanıma',detect)
            if info is None:continue
            # main window: every target, plus text-only and OCR options where the window shows them
            for target in core.targets(info):
                variants=[core.Options()]
                if core.text_options_apply(info,target):variants+= [core.Options(only_text=True),core.Options(ocr=True,ocr_language='tur+eng')]
                for opt in variants:
                    tag=' (yalnız metin)' if opt.only_text else ' (OCR)' if opt.ocr else ''
                    def conv(opt=opt,target=target):
                        res=core.Runner().convert(info,target,out/'conv'/name/(target+tag))
                        if res.suffix[1:].lower()!=target or not res.stat().st_size:raise AssertionError(f'beklenen .{target}, çıkan {res.name}')
                        return res.name
                    record(f'{name} · biçim → {target}{tag}',conv)
            # extras window: every operation offered for this file
            for act in actions(info):
                variants=[{}]
                if act=='add_subtitle':variants=[{'subtitle_mode':'burn'},{'subtitle_mode':'soft'}]
                if act=='transcribe':variants=[{'speech_format':'txt'},{'speech_format':'srt'}]
                for extra in variants:
                    kw=dict(start='1',end='2.5',part='1.5',page_count='1',factor={'rotate':'90','volume':'0.5'}.get(act,'1.5'),speech_language='en',**extra)
                    if act in {'transcribe','add_subtitle','mute','merge'}:kw.update(start='0',end='')
                    files_in=[path,path] if act=='merge' else [path]
                    if act in {'add_audio','replace_audio'}:kw['audio']=str(speech)
                    if act=='add_subtitle':kw['audio']=str(srt)
                    if act=='subtitle_restore':kw['audio']=str(srt)
                    label=f"{name} · işlem {act}"+(f" ({list(extra.values())[0]})" if extra else '')
                    def run(act=act,kw=kw,files_in=files_in,extra=extra):
                        try:res=Editor().execute(Request(act,files_in,out/'ops'/name/(act+str(extra)),**kw))
                        except SpeechUnavailable as e:
                            if str(e)=='speech_no_text' and name in {'silent.mp4'}:return 'konuşma yok (beklenen)'
                            raise
                        except Exception as e:
                            # A text that is not a line-by-line translation must be refused clearly.
                            if act=='subtitle_restore' and name!='ceviri.txt' and getattr(e,'code','')=='subtitle_line_count':return 'beklenen uyarı'
                            raise
                        want=expected(act,None,info,path) if act!='transcribe' else kw.get('speech_format','txt')
                        for r in res:
                            if not r.stat().st_size:raise AssertionError('boş çıktı '+r.name)
                            if want and r.suffix[1:].lower()!=want:raise AssertionError(f'beklenen .{want}, çıkan {r.name}')
                        return ' '.join(r.name for r in res)[:120]
                    record(label,run)
    failed=[r for r in rows if not r['pass']]
    if report:report.write_text(json.dumps({'cases':len(rows),'failures':len(failed),'rows':rows},ensure_ascii=False,indent=1),encoding='utf-8')
    print(f'TAM TEST: {len(rows)-len(failed)}/{len(rows)} geçti',flush=True)
    return 0 if not failed else 1

if __name__=='__main__':sys.exit(main())
