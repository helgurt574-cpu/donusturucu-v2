"""Native package entry point and executable end-to-end smoke test."""
from pathlib import Path
import json
import sys
import tempfile
if not getattr(sys,'frozen',False):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from donusturucu import core,runtime

def self_test(report):
    data={'platform':sys.platform,'tools':core.tools(),'tool_paths':{n:runtime.tool_path(n) for n in ['ffmpeg','ffprobe','libreoffice','pandoc','tesseract','pdftoppm']},'bundle_root':str(runtime.ROOT),'passed':False,'error':None}
    try:
        with tempfile.TemporaryDirectory(prefix='donustur-selftest-') as tmp:
            root=Path(tmp);source=root/'Silav.txt';source.write_text('Merhaba dünya. Silav cîhan!',encoding='utf-8')
            runner=core.Runner();pdf=runner.convert(core.detect(source),'pdf',root)
            original=runtime.tool_path
            runtime.tool_path=lambda name:None if name=='pdftotext' else original(name)
            try:text=runner.convert(core.detect(pdf),'txt',root)
            finally:runtime.tool_path=original
            assert 'Silav' in text.read_text(encoding='utf-8')
            epub=runner.convert(core.detect(source),'epub',root)
            assert runner.convert(core.detect(epub),'docx',root).stat().st_size
            audio=root/'test.wav'
            runner.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=0.2','-y',str(audio)])
            assert runner.convert(core.detect(audio),'mp3',root).stat().st_size
            from donusturucu.operations import Editor,Request
            editor=Editor()
            assert editor.execute(Request('trim',[audio],root/'edit-audio',start='0.02',end='0.15'))[0].stat().st_size
            assert editor.execute(Request('split',[pdf],root/'edit-pdf',page_count='1'))[0].stat().st_size
            if runtime.available('tesseract'):
                from donusturucu.ocr import image_text
                image=runtime.ROOT/'ocr-smoke.png'
                if not image.exists():image=runtime.ROOT/'packaging/ocr-smoke.png'
                assert 'OFFLINE OCR TEST' in image_text(runner,image,'eng')
                for lang,expected in [('ara','مرحبا بالعالم'),('fas','سلام دنیا')]:
                    image=runtime.ROOT/('ocr-smoke-'+lang+'.png')
                    if not image.exists():image=runtime.ROOT/('packaging/ocr-smoke-'+lang+'.png')
                    assert expected in image_text(runner,image,lang)
            import xml.etree.ElementTree as ET
            source=root/'rtl.txt';rtl='سلام دنیا، می\u200cروم ۱۲۳ (ABC-42)';source.write_text(rtl,encoding='utf-8')
            docx=runner.convert(core.detect(source),'docx',root)
            import zipfile
            with zipfile.ZipFile(docx) as archive:xml=ET.fromstring(archive.read('word/document.xml'))
            ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            assert rtl in ''.join(t.text or '' for t in xml.findall('.//w:t',ns))
            assert xml.find('.//w:bidi',ns) is not None
            from donusturucu import speech
            model,_=speech.resources()
            fixture=runtime.ROOT/'speech-test/english-test.mp3'
            if not fixture.exists():fixture=runtime.ROOT/'assets/speech/english-test.mp3'
            spoken=editor.execute(Request('transcribe',[fixture],root/'speech',speech_language='en'))[0]
            assert 'could you repeat that' in spoken.read_text(encoding='utf-8').lower()
            data['speech_model']=str(model)
            data['passed']=True
    except Exception as e:data['error']=str(e)
    Path(report).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(0 if data['passed'] else 1)

if '--speech-worker' in sys.argv:
    from donusturucu.speech_worker import main as speech_main
    speech_main(sys.argv[sys.argv.index('--speech-worker')+1:]);raise SystemExit(0)

if '--self-test' in sys.argv:self_test(sys.argv[sys.argv.index('--self-test')+1])
from donusturucu.portable import main
main()
