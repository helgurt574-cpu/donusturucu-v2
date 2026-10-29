from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
import cairo
from test_conversion import odf
from donusturucu import core
from donusturucu.text_layout import direction,attrs,text_to_html

PERSIAN='سلام دنیا، می\u200cروم ۱۲۳ (ABC-42)'
ARABIC='مرحبا بالعالم، رقم ١٢٣ (Test-42)'
W={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

class RTLTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory(prefix='donustur-rtl-');self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_plain_text_unicode_roundtrip(self):
        p=self.root/'فارسی.txt';text=PERSIAN+'\n'+ARABIC+'\nEnglish 123\n';p.write_text(text,encoding='utf-8')
        result=core.Runner().convert(core.detect(p),'txt',self.root)
        self.assertEqual(text,result.read_text(encoding='utf-8'))
    def test_text_to_docx_paragraph_direction(self):
        p=self.root/'Arabic-Persian.txt';p.write_text(PERSIAN+'\n'+ARABIC+'\nEnglish 123',encoding='utf-8')
        out=core.Runner().convert(core.detect(p),'docx',self.root)
        with zipfile.ZipFile(out) as z:root=ET.fromstring(z.read('word/document.xml'))
        paragraphs=root.findall('.//w:p',W)
        for text in [PERSIAN,ARABIC]:
            p=next(p for p in paragraphs if text==''.join(t.text or '' for t in p.findall('.//w:t',W)))
            bidi=p.find('w:pPr/w:bidi',W);self.assertIsNotNone(bidi);self.assertNotEqual(bidi.get('{'+W['w']+'}val'),'0')
    def test_slide_to_document_rtl_and_actual_content(self):
        p=self.root/'عرض.odp';odf(p,'presentation','<draw:page draw:name="page 2"><draw:frame><draw:text-box><text:p>'+PERSIAN+'</text:p><text:p>'+ARABIC+'</text:p><text:p>English 123</text:p></draw:text-box></draw:frame></draw:page>')
        for fmt in ['docx','odt','txt','html','epub','pdf']:
            with self.subTest(fmt=fmt):
                out=core.Runner().convert(core.detect(p),fmt,self.root,core.Options(only_text=True))
                if fmt=='docx':
                    with zipfile.ZipFile(out) as z:
                        xml=z.read('word/document.xml').decode();document=ET.fromstring(xml);text=''.join(t.text or '' for t in document.findall('.//w:t',W));self.assertIn(PERSIAN,text);self.assertIn(ARABIC,text);self.assertIn('w:bidi',xml)
                if fmt=='html':
                    html=out.read_text(encoding='utf-8');self.assertTrue('RTL' in html or 'rtl' in html);self.assertIn('می\u200cروم',html)
                if fmt=='txt':
                    text=out.read_text(encoding='utf-8');self.assertIn(PERSIAN,text);self.assertIn(ARABIC,text);self.assertNotIn('page 2',text.lower())
                if fmt=='odt':
                    with zipfile.ZipFile(out) as z:self.assertIn('rl-tb',z.read('content.xml').decode())
    def test_inherited_explicit_rtl(self):
        source=self.root/'mixed.odp';odf(source,'presentation','<draw:page><draw:frame><draw:text-box><text:p text:style-name="Child">ABC-42 مرحبا بالعالم</text:p></draw:text-box></draw:frame></draw:page>')
        with zipfile.ZipFile(source) as z:files={n:z.read(n) for n in z.namelist()}
        xml=files['content.xml'].decode().replace('<office:body>','<office:automatic-styles xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"><style:style style:name="Parent" style:family="paragraph"><style:paragraph-properties style:writing-mode="rl-tb"/></style:style><style:style style:name="Child" style:family="paragraph" style:parent-style-name="Parent"/></office:automatic-styles><office:body>')
        files['content.xml']=xml.encode()
        with zipfile.ZipFile(source,'w') as z:
            for n,data in files.items():z.writestr(n,data)
        out=core.Runner().convert(core.detect(source),'docx',self.root)
        with zipfile.ZipFile(out) as z:root=ET.fromstring(z.read('word/document.xml'))
        p=root.find('.//w:p',W);self.assertEqual(p.find('w:pPr/w:bidi',W).get('{'+W['w']+'}val'),'1')
    def test_epub_direction(self):
        source=self.root/'farsi.txt';source.write_text(PERSIAN+'\nEnglish 123',encoding='utf-8')
        out=core.Runner().convert(core.detect(source),'epub',self.root)
        with zipfile.ZipFile(out) as z:
            self.assertEqual(z.infolist()[0].filename,'mimetype');self.assertEqual(z.infolist()[0].compress_type,zipfile.ZIP_STORED)
            opf=next(n for n in z.namelist() if n.endswith('.opf'))
            spine=ET.fromstring(z.read(opf)).find('{http://www.idpf.org/2007/opf}spine')
            self.assertEqual(spine.get('page-progression-direction'),'rtl')
            xhtml=next(n for n in z.namelist() if n.endswith('.xhtml') and '/sections/' in n)
            root=ET.fromstring(z.read(xhtml));paragraphs=root.findall('.//{http://www.w3.org/1999/xhtml}p')
            p=next(p for p in paragraphs if PERSIAN in ''.join(p.itertext()));self.assertEqual(p.get('dir'),'rtl')
    def test_epub_to_docx_direction(self):
        source=self.root/'fa.txt';source.write_text(PERSIAN,encoding='utf-8')
        epub=core.Runner().convert(core.detect(source),'epub',self.root)
        out=core.Runner().convert(core.detect(epub),'docx',self.root)
        with zipfile.ZipFile(out) as z:root=ET.fromstring(z.read('word/document.xml'))
        paragraph=next(p for p in root.findall('.//w:p',W) if PERSIAN in ''.join(t.text or '' for t in p.findall('.//w:t',W)))
        self.assertEqual(paragraph.find('w:pPr/w:bidi',W).get('{'+W['w']+'}val'),'1')
    def test_pdf_to_docx_only_text(self):
        source=self.root/'scan.pdf'
        surface=cairo.PDFSurface(str(source),600,250);ctx=cairo.Context(surface);ctx.select_font_face('DejaVu Sans');ctx.set_font_size(30);ctx.move_to(30,100);ctx.text_path('OFFLINE OCR TEST');ctx.fill();surface.finish()
        out=core.Runner().convert(core.detect(source),'docx',self.root,core.Options(only_text=True,ocr=True,ocr_language='eng'))
        with zipfile.ZipFile(out) as z:self.assertIn('OFFLINE OCR TEST',z.read('word/document.xml').decode())
    def test_arabic_and_persian_ocr(self):
        import gi
        gi.require_version('PangoCairo','1.0');gi.require_version('Pango','1.0');from gi.repository import Pango,PangoCairo
        from donusturucu.ocr import image_text
        for language,text in [('ara','مرحبا بالعالم'),('fas','سلام دنیا')]:
            with self.subTest(language=language):
                p=self.root/(language+'.png');surface=cairo.ImageSurface(cairo.FORMAT_RGB24,1500,250);ctx=cairo.Context(surface);ctx.set_source_rgb(1,1,1);ctx.paint();ctx.set_source_rgb(0,0,0)
                layout=PangoCairo.create_layout(ctx);layout.set_font_description(Pango.FontDescription('DejaVu Sans 60'));layout.set_text(text,-1);ctx.move_to(80,60);PangoCairo.show_layout(ctx,layout);surface.write_to_png(str(p))
                result=image_text(core.Runner(),p,language)
                self.assertIn(text,result,(language,result))

if __name__=='__main__':unittest.main(verbosity=2)
