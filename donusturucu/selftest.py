"""End-to-end self test for any packaged build (Linux AppImage/deb, Windows, macOS).

    python -m donusturucu.selftest [report.json]

Every check runs the real bundled tools on files generated here, so a package can be
verified on a fresh machine without test fixtures. Exit code 0 only if all checks pass.
"""
from pathlib import Path
import json,platform,sys,tempfile,time,traceback,zipfile
from . import core,runtime,VERSION

def main(argv=None):
    argv=sys.argv[1:] if argv is None else argv
    # Windows consoles may not be UTF-8; a report must never crash on a dash or a Turkish letter.
    for stream in (sys.stdout,sys.stderr):
        try:stream.reconfigure(errors='replace')
        except (AttributeError,ValueError):pass
    report=Path(argv[0]) if argv else None
    results=[];data={'version':VERSION,'platform':sys.platform,'machine':platform.machine(),'python':sys.version.split()[0],
        'tools':core.tools(),'tool_paths':{n:runtime.tool_path(n) for n in ['ffmpeg','ffprobe','libreoffice','pandoc','tesseract','pdftoppm','pdftotext']},
        'isolation':runtime.isolation_status(),'checks':results}
    def check(name,func):
        started=time.monotonic()
        try:detail=func();ok=True
        except KeyError as error:detail=f'önceki adım başarısız olduğu için yapılamadı ({error})';ok=False
        except Exception as error:detail=f'{type(error).__name__}: {error}';ok=False;data.setdefault('tracebacks',{})[name]=traceback.format_exc()
        results.append({'name':name,'ok':ok,'seconds':round(time.monotonic()-started,1),'detail':detail})
        print(('PASS ' if ok else 'FAIL ')+name+(' — '+str(detail) if detail else ''),flush=True)
    with tempfile.TemporaryDirectory(prefix='donustur-selftest-') as tmp:
        root=Path(tmp);runner=core.Runner()
        from .operations import Editor,Request
        editor=Editor(runner)
        def gui():
            found=[]
            try:
                import tkinter;r=tkinter.Tk();r.withdraw();r.destroy();found.append('tk')
            except Exception as error:found.append('tk unavailable: '+type(error).__name__)
            if sys.platform.startswith('linux'):
                try:
                    import gi;gi.require_version('Gtk','3.0');from gi.repository import Gtk;found.append('gtk' if Gtk.init_check()[0] else 'gtk (no display)')
                except Exception as error:found.append('gtk unavailable: '+type(error).__name__)
            return ', '.join(found)
        check('arayuz',gui)
        source=root/'Silav.txt';source.write_text('Merhaba dünya. Silav cîhan! Çğış ÇĞİŞ',encoding='utf-8')
        state={}
        def doc_pdf():
            state['pdf']=runner.convert(core.detect(source),'pdf',root);return state['pdf'].name
        check('belge TXT→PDF (LibreOffice)',doc_pdf)
        def pdf_txt():
            text=runner.convert(core.detect(state['pdf']),'txt',root/'pdf-text').read_text(encoding='utf-8')
            assert 'Silav' in text and 'Çğış' in text,text;return 'Türkçe karakterler korundu'
        check('PDF→TXT',pdf_txt)
        def ebook():
            epub=runner.convert(core.detect(source),'epub',root/'epub');docx=runner.convert(core.detect(epub),'docx',root/'docx')
            assert docx.stat().st_size;return 'TXT→EPUB→DOCX'
        check('e-kitap (Pandoc)',ebook)
        def rtl():
            import xml.etree.ElementTree as ET
            text='سلام دنیا، می‌روم ۱۲۳ (ABC-42)';src=root/'rtl.txt';src.write_text(text,encoding='utf-8')
            docx=runner.convert(core.detect(src),'docx',root/'rtl')
            with zipfile.ZipFile(docx) as archive:xml=ET.fromstring(archive.read('word/document.xml'))
            ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            assert text in ''.join(t.text or '' for t in xml.findall('.//w:t',ns));assert xml.find('.//w:bidi',ns) is not None
            return 'Farsça sağdan sola'
        check('sağdan sola metin',rtl)
        def pdf_split():
            return f"{len(editor.execute(Request('split',[state['pdf']],root/'split',page_count='1')))} parça"
        check('PDF parçalama',pdf_split)
        def ocr():
            from .ocr import image_text
            import shutil
            image=root/'ocr.png';font=root/'font.ttf';shutil.copyfile(runtime.ROOT/'assets/fonts/DejaVuSans-Bold.ttf',font)
            runner.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=white:s=900x200','-frames:v','1','-vf',
                "drawtext=fontfile='"+font.as_posix().replace(':','\\:')+"':text='OFFLINE OCR TEST':fontcolor=black:fontsize=72:x=40:y=60",'-y',str(image)])
            text=image_text(runner,image,'eng');assert 'OFFLINE' in text.upper() and 'TEST' in text.upper(),text
            return text.strip()
        check('OCR (Tesseract)',ocr)
        media={}
        def video():
            clip=root/'klip.mp4'
            runner.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc=s=640x360:r=25:d=3','-f','lavfi','-i','sine=frequency=440:duration=3',
                '-shortest','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-y',str(clip)])
            media['video']=clip;mp3=runner.convert(core.detect(clip),'mp3',root/'mp3');assert mp3.stat().st_size;return 'MP4→MP3'
        check('ses/video dönüştürme (FFmpeg)',video)
        def trim():
            out=editor.execute(Request('trim',[media['video']],root/'trim',start='0.5',end='2'))[0];assert out.stat().st_size;return out.name
        check('video kesme',trim)
        def subtitles():
            srt=root/'alt.srt';srt.write_text('1\n00:00:00,200 --> 00:00:02,000\nMerhaba — Silav!\n\n',encoding='utf-8')
            burned=editor.execute(Request('add_subtitle',[media['video']],root/'burn',audio=str(srt),subtitle_mode='burn'))[0]
            soft=editor.execute(Request('add_subtitle',[media['video']],root/'soft',audio=str(srt),subtitle_mode='soft'))[0]
            streams=Editor(runner).probe(soft)['streams'];assert any(s.get('codec_type')=='subtitle' for s in streams)
            def bottom(video):
                # Grayscale bottom strip at 1 s, where the cue is shown.
                frame=root/(video.stem+'-strip.gray')
                runner.run(['ffmpeg','-v','error','-ss','1','-i',str(video),'-frames:v','1','-vf','crop=iw:ih/4:0:ih*3/4,format=gray','-f','rawvideo','-y',str(frame)])
                return frame.read_bytes()
            before,after=bottom(media['video']),bottom(burned)
            changed=sum(abs(a-b)>40 for a,b in zip(before,after))/max(1,len(before))
            assert changed>0.002,f'altyazı görüntüde yok ({changed:.4f})'
            return f'kalıcı (yazı görünüyor) + açılıp kapatılabilir'
        check('altyazıyı videoya ekleme',subtitles)
        def speech():
            fixture=runtime.ROOT/'assets/selftest/english.mp3'
            out=editor.execute(Request('transcribe',[fixture],root/'speech',speech_language='en',speech_format='srt'))[0]
            text=out.read_text(encoding='utf-8').lower();assert 'repeat' in text,text;return ' '.join(text.split())[:80]
        check('konuşmayı yazıya dökme',speech)
    passed=all(r['ok'] for r in results);data['passed']=passed
    if report:report.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(('TÜM TESTLER GEÇTİ' if passed else 'BAZI TESTLER BAŞARISIZ')+f' ({sum(r["ok"] for r in results)}/{len(results)})',flush=True)
    return 0 if passed else 1

if __name__=='__main__':sys.exit(main())
