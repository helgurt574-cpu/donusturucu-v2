import errno
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from test_conversion import odf
from donusturucu import core,runtime

class ExpandedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='donustur-expanded-');self.root=Path(self.tmp.name)
        self.slide=self.root/'Kürtçe sunu.odp'
        odf(self.slide,'presentation','''<draw:page draw:name="Yekem"><draw:frame><draw:text-box><text:p>Silav cîhan! Çığ. Birinci slayt.</text:p></draw:text-box></draw:frame></draw:page><draw:page draw:name="Duyem"><draw:frame><draw:text-box><text:p>İkinci slayt korunmalı.</text:p></draw:text-box></draw:frame></draw:page>''')
    def tearDown(self):self.tmp.cleanup()
    def test_presentation_targets_and_content(self):
        info=core.detect(self.slide)
        self.assertTrue({'pdf','txt','rtf','odt','docx','epub','md','ppt','pptx','odp','html','doc','rst','fb2'}<=set(core.targets(info)))
        for target in ['txt','rtf','odt','docx','epub','md','html','doc','rst','fb2']:
            with self.subTest(target=target):
                out=core.Runner().convert(info,target,self.root)
                self.assertGreater(out.stat().st_size,0)
                if target in {'txt','md','html','rst','fb2'}:
                    self.assertIn('Silav',out.read_text(encoding='utf-8'))
                    self.assertIn('slayt',out.read_text(encoding='utf-8'))
                elif target=='docx':
                    with zipfile.ZipFile(out) as z:self.assertIn('Silav',z.read('word/document.xml').decode())
                elif target=='odt':
                    with zipfile.ZipFile(out) as z:self.assertIn('Silav',z.read('content.xml').decode())
    def test_pptx_to_document(self):
        pptx=core.Runner().convert(core.detect(self.slide),'pptx',self.root)
        for target in ['txt','docx','epub']:
            with self.subTest(target=target):
                out=core.Runner().convert(core.detect(pptx),target,self.root)
                if target=='txt':self.assertIn('Silav',out.read_text(encoding='utf-8'))
                self.assertGreater(out.stat().st_size,0)
    def test_all_sheets_to_document(self):
        sheet=self.root/'İki sayfa.ods'
        odf(sheet,'spreadsheet','''<table:table table:name="Birinci"><table:table-row><table:table-cell office:value-type="string"><text:p>Diyarbakır</text:p></table:table-cell></table:table-row></table:table><table:table table:name="İkinci"><table:table-row><table:table-cell office:value-type="string"><text:p>Amed</text:p></table:table-cell></table:table-row></table:table>''')
        for target in ['txt','docx','epub','md']:
            with self.subTest(target=target):
                result=core.Runner().convert(core.detect(sheet),target,self.root)
                if target in {'txt','md'}:
                    text=result.read_text(encoding='utf-8');self.assertIn('Diyarbakır',text);self.assertIn('Amed',text)
    def test_pdf_python_fallback(self):
        source=self.root/'silav.txt';source.write_text('Silav cîhan!',encoding='utf-8')
        pdf=core.Runner().convert(core.detect(source),'pdf',self.root)
        original=runtime.tool_path
        with patch.object(runtime,'tool_path',side_effect=lambda name:None if name=='pdftotext' else original(name)):
            self.assertTrue(runtime.available('pypdf'))
            out=core.Runner().convert(core.detect(pdf),'txt',self.root)
            self.assertIn('Silav',out.read_text(encoding='utf-8'))
    def test_fb2_table_roundtrip(self):
        sheet=self.root/'Cells.ods'
        odf(sheet,'spreadsheet','<table:table table:name="Yek"><table:table-row><table:table-cell office:value-type="string"><text:p>Silav cîhan</text:p></table:table-cell><table:table-cell office:value-type="string"><text:p>مرحبا بالعالم</text:p></table:table-cell></table:table-row></table:table>')
        fb2=core.Runner().convert(core.detect(sheet),'fb2',self.root)
        for target in ['txt','docx','html','epub']:
            with self.subTest(target=target):
                out=core.Runner().convert(core.detect(fb2),target,self.root)
                text=out.read_text(encoding='utf-8') if target=='txt' else core.Runner().convert(core.detect(out),'txt',self.root).read_text(encoding='utf-8')
                self.assertIn('Silav cîhan',text);self.assertIn('مرحبا بالعالم',text)
    def test_pdf_page_separator_to_fb2(self):
        source=self.root/'Page.txt';source.write_text('Silav cîhan!',encoding='utf-8')
        pdf=core.Runner().convert(core.detect(source),'pdf',self.root)
        fb2=core.Runner().convert(core.detect(pdf),'fb2',self.root)
        out=core.Runner().convert(core.detect(fb2),'txt',self.root)
        self.assertIn('Silav',out.read_text(encoding='utf-8'))
    def test_output_without_hardlinks(self):
        source=self.root/'metin.txt';source.write_text('Silav',encoding='utf-8')
        existing=self.root/'metin.pdf';existing.write_bytes(b'keep original')
        def unsupported(*_):raise OSError(errno.EOPNOTSUPP,'links not supported')
        with patch.object(core.os,'link',side_effect=unsupported):
            out=core.Runner().convert(core.detect(source),'pdf',self.root)
        self.assertNotEqual(out,existing);self.assertEqual(existing.read_bytes(),b'keep original')
        self.assertTrue(out.read_bytes().startswith(b'%PDF-'))
    def test_no_generated_slide_names(self):
        slide=self.root/'Sunu.odp'
        odf(slide,'presentation','<draw:page draw:name="page 2"><draw:frame><draw:text-box><text:p>Birinci gerçek başlık</text:p></draw:text-box></draw:frame></draw:page><draw:page draw:name="page 3"><draw:frame><draw:text-box><text:p>Page 42 belgenin gerçek metnidir.</text:p></draw:text-box></draw:frame></draw:page>')
        for target in ['txt','docx','md']:
            with self.subTest(target=target):
                out=core.Runner().convert(core.detect(slide),target,self.root,core.Options(only_text=True))
                if target=='docx':
                    with zipfile.ZipFile(out) as z:text=z.read('word/document.xml').decode()
                else:text=out.read_text(encoding='utf-8')
                self.assertNotIn('page 2',text.lower());self.assertNotIn('page 3',text.lower())
                self.assertIn('Birinci gerçek başlık',text);self.assertIn('Page 42 belgenin gerçek metnidir.',text)
    def test_list_header_text_exports(self):
        source=self.root/'List.odp'
        odf(source,'presentation','<draw:page><draw:frame><draw:text-box><text:list><text:list-header><text:p>Silav cîhan list header</text:p></text:list-header></text:list></draw:text-box></draw:frame></draw:page>')
        for fmt in ['md','rst','fb2','epub']:
            with self.subTest(fmt=fmt):
                out=core.Runner().convert(core.detect(source),fmt,self.root)
                text=core.Runner().convert(core.detect(out),'txt',self.root).read_text(encoding='utf-8')
                self.assertIn('Silav',text)
    def test_bundled_tool_discovery(self):
        tools=self.root/'Araçlar';(tools/'LibreOffice/program').mkdir(parents=True)
        # Use native names so this test runs on any target OS.
        import sys,os
        exe='ffmpeg.exe' if sys.platform=='win32' else 'ffmpeg'
        (tools/exe).touch()
        with patch.dict(os.environ,{'DONUSTURUCU_TOOLS':str(tools)}):self.assertEqual(runtime.tool_path('ffmpeg'),str(tools/exe))

if __name__=='__main__':unittest.main(verbosity=2)
