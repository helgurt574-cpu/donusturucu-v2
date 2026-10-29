from pathlib import Path
import tempfile
import unittest
import zipfile
import cairo
from test_conversion import odf
from donusturucu import core,runtime

class OCRTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        image=self.root/'scan.png'
        surface=cairo.ImageSurface(cairo.FORMAT_RGB24,1400,240);ctx=cairo.Context(surface);ctx.set_source_rgb(1,1,1);ctx.paint();ctx.set_source_rgb(0,0,0);ctx.select_font_face('DejaVu Sans');ctx.set_font_size(65);ctx.move_to(50,130);ctx.show_text('OFFLINE OCR TEST');surface.write_to_png(str(image))
        self.slide=self.root/'Resimli sunu.odp'
        odf(self.slide,'presentation','''<draw:page draw:name="Scan"><draw:frame><draw:image xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="Pictures/scan.png"/></draw:frame></draw:page>''')
        with zipfile.ZipFile(self.slide,'a') as z:z.write(image,'Pictures/scan.png')
    def tearDown(self):self.temp.cleanup()
    def test_only_text_requires_ocr_for_scanned_slide(self):
        with self.assertRaises(core.ConversionError) as result:core.Runner().convert(core.detect(self.slide),'docx',self.root,core.Options(only_text=True))
        self.assertEqual(result.exception.code,'no_text')
    def test_image_ocr_to_text_and_editable_docx(self):
        for target in ['txt','docx','pdf']:
            with self.subTest(target=target):
                out=core.Runner().convert(core.detect(self.slide),target,self.root,core.Options(only_text=True,ocr=True,ocr_language='eng'))
                if target=='txt':self.assertIn('OFFLINE OCR TEST',out.read_text(encoding='utf-8'))
                if target=='docx':
                    with zipfile.ZipFile(out) as z:
                        xml=z.read('word/document.xml').decode();self.assertIn('OFFLINE OCR TEST',xml);self.assertNotIn('<w:drawing',xml)
    def test_images_excluded_without_losing_native_text(self):
        slide=self.root/'Mixed.odp'
        odf(slide,'presentation','''<draw:page draw:name="Mixed"><draw:frame><draw:text-box><text:p>Native selectable text.</text:p></draw:text-box><draw:image xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="Pictures/scan.png"/></draw:frame></draw:page>''')
        with zipfile.ZipFile(slide,'a') as z:z.write(self.root/'scan.png','Pictures/scan.png')
        out=core.Runner().convert(core.detect(slide),'docx',self.root,core.Options(only_text=True))
        with zipfile.ZipFile(out) as z:
            xml=z.read('word/document.xml').decode();self.assertIn('Native selectable text.',xml);self.assertNotIn('<w:drawing',xml)
    def test_scanned_pdf_ocr(self):
        pdf=self.root/'scanned.pdf'
        surface=cairo.PDFSurface(str(pdf),600,250);ctx=cairo.Context(surface);ctx.select_font_face('DejaVu Sans');ctx.set_font_size(30);ctx.move_to(30,100);ctx.text_path('OFFLINE OCR TEST');ctx.fill();surface.finish()
        out=core.Runner().convert(core.detect(pdf),'txt',self.root,core.Options(only_text=True,ocr=True,ocr_language='eng'))
        self.assertIn('OFFLINE OCR TEST',out.read_text(encoding='utf-8'))

if __name__=='__main__':unittest.main(verbosity=2)
