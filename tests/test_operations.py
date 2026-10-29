import array,hashlib,json,math,subprocess,tempfile,unittest
from pathlib import Path
from donusturucu import core
from donusturucu.operations import Editor,Request,OperationError,seconds,actions
from pypdf import PdfReader,PdfWriter

class OperationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        cls.video=cls.root/'Türkçe û vîdyo.mp4';cls.audio=cls.root/'deng.wav';cls.extra=cls.root/'extra.wav'
        def ff(args):subprocess.run(['ffmpeg','-v','error',*args,'-y'],check=True,capture_output=True)
        ff(['-f','lavfi','-i','testsrc2=s=160x120:r=12:d=4','-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=4','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(cls.video)])
        ff(['-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=4','-c:a','pcm_s16le',str(cls.audio)])
        ff(['-f','lavfi','-i','sine=frequency=220:sample_rate=48000:duration=1','-f','lavfi','-i','sine=frequency=880:sample_rate=48000:duration=1','-f','lavfi','-i','sine=frequency=1320:sample_rate=48000:duration=1','-filter_complex','[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]','-map','[a]',str(cls.extra)])
        cls.pdf=cls.root/'Pages.pdf';w=PdfWriter()
        for width in [200,300,400,500]:w.add_blank_page(width=width,height=600)
        w.write(cls.pdf);w.close()
        cls.digest={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in [cls.video,cls.audio,cls.extra,cls.pdf]}
    @classmethod
    def tearDownClass(cls):
        for p,digest in cls.digest.items():assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
        cls.tmp.cleanup()
    def setUp(self):self.out=self.root/self._testMethodName;self.out.mkdir();self.editor=Editor()
    def run_op(self,action,path=None,**kwargs):
        result=self.editor.execute(Request(action,[path or self.video],self.out,**kwargs))
        for p in result:
            self.assertGreater(p.stat().st_size,0)
            if p.suffix not in {'.pdf','.png'}:
                subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','null','-'],check=True,capture_output=True)
        return result
    def duration(self,path):return self.editor.duration(path)
    def test_time_parser_and_validation(self):
        self.assertEqual(seconds('01:02:03.5'),3723.5);self.assertEqual(seconds('1,25'),1.25)
        for value in ['-1','nan','inf','00:75','1:2:3:4','',':1','1.5:2']:
            with self.subTest(value=value),self.assertRaises(OperationError):seconds(value)
        for start,end in [('2','1'),('0','99')]:
            with self.assertRaises(OperationError):self.run_op('trim',start=start,end=end)
    def test_video_trim_remove_split(self):
        trim=self.run_op('trim',start='1',end='3')[0];self.assertAlmostEqual(self.duration(trim),2,delta=.2)
        cut=self.run_op('remove_range',start='1',end='3')[0];self.assertAlmostEqual(self.duration(cut),2,delta=.3)
        parts=self.run_op('split',start='1',end='3.5',part='1');self.assertEqual(len(parts),3)
        self.assertAlmostEqual(sum(self.duration(p) for p in parts),2.5,delta=.3)
    def test_merge_individual_ranges(self):
        for path in [self.video,self.audio]:
            r=Request('merge',[path,path],self.out,segments=[('0.5','1.5'),('2','3')]);out=self.editor.execute(r)[0]
            self.assertAlmostEqual(self.duration(out),2,delta=.3)
    def test_silent_mixed_video_join_and_audio_insert(self):
        silent=self.out/'silent.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=green:s=320x180:r=25:d=1.5','-c:v','libx264','-pix_fmt','yuv420p','-y',str(silent)],check=True,capture_output=True)
        result=self.editor.execute(Request('merge',[self.video,silent],self.out))[0]
        info=core.detect(result);self.assertEqual((info.width,info.height),(160,120));self.assertTrue(info.has_audio)
        self.assertAlmostEqual(self.duration(result),5.5,delta=.3)
        self.assertLess(self.rms(result,4.5),25)
        out=self.run_op('add_audio',silent,start='.25',end='1.25',audio=str(self.extra),audio_start='1',audio_end='2')[0]
        self.assertGreater(self.energy(out,.5,880),100)
        faster=self.run_op('speed',silent,start='.25',end='1.25',factor='2')[0]
        self.assertAlmostEqual(self.duration(faster),1,delta=.2)
    def test_audio_parts_and_boundary_cuts(self):
        parts=self.run_op('split',self.audio,start='1',end='3.5',part='1')
        self.assertEqual(len(parts),3);self.assertAlmostEqual(sum(self.duration(p) for p in parts),2.5,delta=.1)
        for path in [self.audio,self.video]:
            out=self.run_op('remove_range',path,start='0',end='1')[0];self.assertAlmostEqual(self.duration(out),3,delta=.2)
            out=self.run_op('remove_range',path,start='1',end='4')[0];self.assertAlmostEqual(self.duration(out),1,delta=.2)
        with self.assertRaises(OperationError):self.run_op('add_audio',start='0',audio=str(self.extra),audio_start='99')
    def test_fractional_split_has_no_empty_tail(self):
        for path in [self.video,self.audio]:
            parts=self.run_op('split',path,start='.1',end='.4',part='.15')
            self.assertEqual(len(parts),2)
    def test_transport_stream_precise_seek(self):
        source=core.Runner().convert(core.detect(self.video),'ts',self.out)
        result=self.run_op('trim',source,start='.5',end='1')[0]
        self.assertEqual(core.detect(result).kind,'video');self.assertAlmostEqual(self.duration(result),.5,delta=.15)
        self.run_op('frame',source,start='.5')
        self.run_op('gif',source,start='.5',end='1')
    def samples(self,path,start,duration=.25):
        p=subprocess.run(['ffmpeg','-v','error','-ss',str(start),'-i',str(path),'-t',str(duration),'-f','s16le','-ac','1','-ar','48000','pipe:1'],capture_output=True,check=True)
        result=array.array('h');result.frombytes(p.stdout);return result
    def rms(self,path,start):
        x=self.samples(path,start);return math.sqrt(sum(i*i for i in x)/max(1,len(x)))
    def test_mute_only_interval(self):
        for path in [self.video,self.audio]:
            out=self.run_op('mute_range',path,start='1',end='2')[0]
            self.assertGreater(self.rms(out,.3),100);self.assertLess(self.rms(out,1.3),20);self.assertGreater(self.rms(out,2.5),100)
            self.assertAlmostEqual(self.duration(out),4,delta=.15)
    def energy(self,path,start,freq):
        samples=self.samples(path,start);n=len(samples)
        return abs(sum(x*complex(math.cos(2*math.pi*freq*i/48000),math.sin(2*math.pi*freq*i/48000)) for i,x in enumerate(samples)))/n
    def test_add_replace_selected_audio_at_time(self):
        for action in ['add_audio','replace_audio']:
            out=self.run_op(action,start='1',end='2',audio=str(self.extra),audio_start='1',audio_end='2')[0]
            self.assertAlmostEqual(self.duration(out),4,delta=.15)
            self.assertGreater(self.energy(out,1.3,880),100)
            self.assertGreater(self.energy(out,.3,440),100);self.assertGreater(self.energy(out,2.5,440),100)
            if action=='replace_audio':self.assertLess(self.energy(out,1.3,440),30)
            else:self.assertGreater(self.energy(out,1.3,440),100)
            self.assertLess(self.energy(out,.3,880),30);self.assertLess(self.energy(out,2.5,880),30)
    def test_video_mute_extract_frame_gif_rotate(self):
        muted=self.run_op('mute')[0];self.assertFalse(core.detect(muted).has_audio)
        audio=self.run_op('extract_audio',start='1',end='2')[0];self.assertAlmostEqual(self.duration(audio),1,delta=.15)
        frame=self.run_op('frame',start='1')[0];self.assertEqual(frame.read_bytes()[:8],b'\x89PNG\r\n\x1a\n')
        gif=self.run_op('gif',start='1',end='2')[0];self.assertTrue(gif.read_bytes().startswith(b'GIF'))
        rotated=self.run_op('rotate',start='1',end='2',factor='90')[0];info=core.detect(rotated);self.assertEqual((info.width,info.height),(120,160));self.assertAlmostEqual(info.duration,1,delta=.15)
    def test_audio_and_video_speed_selected_region(self):
        for path in [self.audio,self.video]:
            out=self.run_op('speed',path,start='1',end='3',factor='2')[0]
            self.assertAlmostEqual(self.duration(out),3,delta=.35)
    def test_audio_volume_and_fades(self):
        out=self.run_op('volume',self.audio,start='1',end='2',factor='0')[0]
        self.assertLess(self.rms(out,1.2),1);self.assertGreater(self.rms(out,2.5),100)
        for action in ['fade_in','fade_out']:
            out=self.run_op(action,self.audio,start='1',end='2')[0]
            self.assertGreater(self.rms(out,.3),100);self.assertGreater(self.rms(out,2.5),100)
            if action=='fade_in':self.assertLess(self.rms(out,1.02),self.rms(out,1.7))
            else:self.assertGreater(self.rms(out,1.02),self.rms(out,1.7))
    def test_pdf_split_ranges_and_merge_order(self):
        out=self.run_op('split',self.pdf,pages='3-4;1,2');self.assertEqual(len(out),2)
        self.assertEqual([float(p.mediabox.width) for p in PdfReader(out[0]).pages],[400,500])
        self.assertEqual([float(p.mediabox.width) for p in PdfReader(out[1]).pages],[200,300])
        merged=self.editor.execute(Request('merge',list(reversed(out)),self.out))[0]
        self.assertEqual([float(p.mediabox.width) for p in PdfReader(merged).pages],[200,300,400,500])
        each=self.run_op('split',self.pdf,page_count='3');self.assertEqual([len(PdfReader(p).pages) for p in each],[3,1])
    def test_document_normalization(self):
        p=self.out/'Test.txt';p.write_text('Silav cîhan! مرحبا بالعالم',encoding='utf-8')
        out=self.run_op('split',p,page_count='1')[0];self.assertEqual(len(PdfReader(out).pages),1)
    def test_invalid_operations_and_no_overwrite(self):
        with self.assertRaises(OperationError):self.editor.execute(Request('merge',[self.audio,self.video],self.out))
        with self.assertRaises(OperationError):self.run_op('split',self.pdf,pages='0-99')
        with self.assertRaises(OperationError):self.run_op('remove_range',start='0',end='4')
        first=self.run_op('trim',start='0',end='1')[0];digest=first.read_bytes();second=self.run_op('trim',start='0',end='1')[0]
        self.assertNotEqual(first,second);self.assertEqual(first.read_bytes(),digest)
        runner=core.Runner();runner.cancel()
        with self.assertRaises(core.Cancelled):Editor(runner).execute(Request('trim',[self.video],self.out,start='0',end='1'))
        self.assertFalse(list(self.out.glob('.islem-*')))
    def test_contextual_actions(self):
        self.assertEqual(actions(core.detect(self.pdf)),['split','merge'])
        self.assertIn('replace_audio',actions(core.detect(self.video)));self.assertNotIn('replace_audio',actions(core.detect(self.audio)))

if __name__=='__main__':unittest.main(verbosity=2)
