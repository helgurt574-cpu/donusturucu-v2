"""Regression cases found by stress testing and destructive-edge safeguards."""
import hashlib,subprocess,tempfile,threading,time,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from donusturucu import core
from donusturucu.operations import Editor,Request
class EditingEdges(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
  cls.video=cls.root/"Çığ فارسی û ' özel ; video.mkv";cls.audio=cls.root/'ses.wav'
  for args in [ ['-f','lavfi','-i','testsrc=s=177x145:r=12:d=3','-f','lavfi','-i','sine=frequency=440:duration=3','-c:v','libx264','-pix_fmt','yuv444p','-c:a','flac',str(cls.video)], ['-f','lavfi','-i','sine=frequency=880:duration=1',str(cls.audio)]]:
   subprocess.run(['ffmpeg','-v','error',*args,'-y'],check=True,capture_output=True)
  cls.digest=hashlib.sha256(cls.video.read_bytes()).hexdigest()
 @classmethod
 def tearDownClass(cls):
  assert hashlib.sha256(cls.video.read_bytes()).hexdigest()==cls.digest
  cls.tmp.cleanup()
 def setUp(self):self.out=self.root/self._testMethodName;self.out.mkdir()
 def test_odd_dimensions_audio_operations(self):
  for action in ['mute','mute_range','add_audio','replace_audio']:
   with self.subTest(action=action):
    result=Editor().execute(Request(action,[self.video],self.out,start='.4',end='1.2',audio=str(self.audio)))[0]
    info=core.detect(result);self.assertEqual((info.width,info.height),(178,146));self.assertAlmostEqual(info.duration,3,delta=.15)
    subprocess.run(['ffmpeg','-v','error','-i',str(result),'-f','null','-'],check=True,capture_output=True)
 def test_concurrent_names_do_not_overwrite(self):
  def task(_):return Editor().execute(Request('trim',[self.video],self.out,start='.25',end='1.25'))[0]
  with ThreadPoolExecutor(max_workers=3) as pool:outputs=list(pool.map(task,range(3)))
  self.assertEqual(len(set(outputs)),3);self.assertTrue(all(p.stat().st_size>0 for p in outputs));self.assertFalse(list(self.out.glob('.islem-*')))
 def test_cancel_active_editor_has_no_output(self):
  class SlowRunner(core.Runner):
   def run(self,args,**kwargs):
    args=list(args)
    if args[0]=='ffmpeg':args.insert(args.index('-i'),'-re')
    return super().run(args,**kwargs)
  runner=SlowRunner();timer=threading.Timer(.5,runner.cancel);timer.start();start=time.monotonic()
  try:
   with self.assertRaises(core.Cancelled):Editor(runner).execute(Request('trim',[self.video],self.out,start='0',end='2.8'))
  finally:timer.cancel()
  self.assertLess(time.monotonic()-start,5);self.assertEqual(list(self.out.iterdir()),[])
 def test_broken_source_not_published(self):
  broken=self.root/'broken.mp4';broken.write_bytes(b'not a real mp4')
  with self.assertRaises(Exception):Editor().execute(Request('trim',[broken],self.out))
  self.assertEqual(list(self.out.iterdir()),[])
 def test_missing_audio_not_published(self):
  with self.assertRaises(Exception):Editor().execute(Request('add_audio',[self.video],self.out,audio=str(self.root/'absent.wav')))
  self.assertEqual(list(self.out.iterdir()),[])
if __name__=='__main__':unittest.main()
