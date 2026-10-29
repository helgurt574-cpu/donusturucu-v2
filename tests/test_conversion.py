import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
import zipfile
from donusturucu.core import detect, targets, Runner, Options, ConversionError, Cancelled


def odf(path,kind,body):
    mime={'document':'text','spreadsheet':'spreadsheet','presentation':'presentation'}[kind]
    xml=f'''<?xml version="1.0" encoding="UTF-8"?><office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:presentation="urn:oasis:names:tc:opendocument:xmlns:presentation:1.0" office:version="1.2"><office:body><office:{mime}>{body}</office:{mime}></office:body></office:document-content>'''
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('mimetype','application/vnd.oasis.opendocument.'+mime,compress_type=zipfile.ZIP_STORED)
        z.writestr('content.xml',xml)
        z.writestr('styles.xml','''<?xml version="1.0" encoding="UTF-8"?><office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" office:version="1.2"><office:styles/></office:document-styles>''')
        z.writestr('META-INF/manifest.xml',f'''<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"><manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.{mime}"/><manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/><manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/></manifest:manifest>''')

class ConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='donustur-test-')
        cls.root=Path(cls.temp.name); cls.out=cls.root/'outputs';cls.out.mkdir()
        cls.text=cls.root/'Türkçe û Kurmancî.txt';cls.text.write_text('Merhaba dünya. Silav cîhan!\nÇığ, şeker, î, ê, û.\n')
        cls.doc=cls.root/'Belge.odt';odf(cls.doc,'document','<text:p>Merhaba dünya. Silav cîhan!</text:p>')
        cls.sheet=cls.root/'Tablo.ods';odf(cls.sheet,'spreadsheet','<table:table table:name="İlk"><table:table-row><table:table-cell office:value-type="string"><text:p>Şehir</text:p></table:table-cell><table:table-cell office:value-type="float" office:value="42"><text:p>42</text:p></table:table-cell></table:table-row></table:table>')
        cls.slide=cls.root/'Sunu.odp';odf(cls.slide,'presentation','<draw:page draw:name="Birinci"><draw:frame><draw:text-box><text:p>Silav!</text:p></draw:text-box></draw:frame></draw:page>')
        cls.audio=cls.root/'Ses.wav'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=0.5','-y',str(cls.audio)],check=True)
        cls.video=cls.root/'Video.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=160x120:r=12:d=0.5','-f','lavfi','-i','sine=frequency=440:duration=0.5','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest','-y',str(cls.video)],check=True)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def convert(self,path,target):
        result=Runner().convert(detect(path),target,self.out)
        self.assertTrue(result.stat().st_size>0)
        return result
    def test_content_detection(self):
        renamed=self.root/'renamed.data';shutil.copy(self.doc,renamed)
        self.assertEqual(detect(renamed).kind,'document')
        renamed=self.root/'video.docx';shutil.copy(self.video,renamed)
        self.assertEqual(detect(renamed).kind,'video')
        self.assertEqual(detect(self.audio).kind,'audio')
        for path,kind in [(self.doc,'document'),(self.sheet,'spreadsheet'),(self.slide,'presentation')]:self.assertEqual(detect(path).kind,kind)
    def test_audio_formats(self):
        for fmt in ('mp3','wav','flac','ogg','opus','m4a','aac','aiff','wma'):
            with self.subTest(fmt=fmt):self.assertEqual(detect(self.convert(self.audio,fmt)).kind,'audio')
    def test_video_formats(self):
        for fmt in ('mp4','mkv','webm','avi','mov','mpeg','ts','gif'):
            with self.subTest(fmt=fmt):
                p=self.convert(self.video,fmt)
                probe=subprocess.run(['ffprobe','-v','error','-show_streams',str(p)],capture_output=True)
                self.assertEqual(probe.returncode,0,probe.stderr.decode())
    def test_extract_audio(self):self.assertEqual(detect(self.convert(self.video,'mp3')).kind,'audio')
    def test_silent_video(self):
        p=self.root/'silent.mp4';subprocess.run(['ffmpeg','-v','error','-i',str(self.video),'-an','-c:v','copy','-y',str(p)],check=True)
        self.assertNotIn('mp3',targets(detect(p)))
    def test_documents(self):
        for fmt in ('docx','doc','odt','rtf','txt','html','epub','pdf'):
            with self.subTest(fmt=fmt):self.convert(self.doc,fmt)
    def test_sheets(self):
        for fmt in ('xlsx','xls','ods','csv','tsv','pdf','html'):
            with self.subTest(fmt=fmt):self.convert(self.sheet,fmt)
    def test_slides(self):
        for fmt in ('pptx','ppt','odp','pdf'):
            with self.subTest(fmt=fmt):self.convert(self.slide,fmt)
    def test_pdf_text_roundtrip(self):
        pdf=self.convert(self.text,'pdf')
        result=self.convert(pdf,'txt')
        self.assertIn('Silav',result.read_text())
        self.convert(pdf,'docx')
    def test_no_overwrite(self):
        digest=hashlib.sha256(self.audio.read_bytes()).digest()
        first=self.convert(self.audio,'mp3'); before=first.read_bytes()
        second=self.convert(self.audio,'mp3')
        self.assertNotEqual(first,second);self.assertEqual(first.read_bytes(),before)
        self.assertEqual(digest,hashlib.sha256(self.audio.read_bytes()).digest())
    def test_reject_invalid(self):
        p=self.root/'empty';p.touch()
        with self.assertRaises(ConversionError):detect(p)
        p=self.root/'unknown';p.write_bytes(b'\0\x89\xff\x81')
        with self.assertRaises(ConversionError):detect(p)
        with self.assertRaises(ConversionError):Runner().convert(detect(self.audio),'docx',self.out)
    def test_ebook_and_markdown(self):
        if not shutil.which('pandoc'):self.skipTest('pandoc missing')
        p=self.root/'Nivîs.md';p.write_text('# Merhaba\n\nSilav cîhan! **Çığ**.\n')
        epub=self.convert(p,'epub');self.assertEqual(detect(epub).kind,'ebook')
        docx=self.convert(epub,'docx');self.assertEqual(detect(docx).kind,'document')
        self.convert(epub,'pdf')
        for target in ('md','rst','fb2'):
            out=self.convert(docx,target)
            self.assertIn('Silav',out.read_text())
    def test_network_isolation(self):
        Runner().run(['python3','-c',"import socket\ntry: s=socket.socket()\nexcept PermissionError: pass\nelse:\n s.settimeout(1)\n assert s.connect_ex(('1.1.1.1',443)) != 0"] )
    def test_multibyte_text_boundary(self):
        p=self.root/'boundary';p.write_text('a'*8191+'ê'*5)
        self.assertEqual(detect(p).fmt,'txt')
    def test_cancel(self):
        runner=Runner(); runner.cancel()
        with self.assertRaises(Cancelled):runner.convert(detect(self.audio),'mp3',self.out)
        runner=Runner(); failures=[]
        def worker():
            try:runner.run(['python3','-c','import time; time.sleep(30)'])
            except Cancelled:failures.append(True)
        thread=threading.Thread(target=worker);thread.start();time.sleep(.25);runner.cancel();thread.join(5)
        self.assertFalse(thread.is_alive());self.assertEqual(failures,[True])

if __name__=='__main__':unittest.main(verbosity=2)
