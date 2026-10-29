"""Real offline recognition, failures, interval and cancellation contracts."""
import tempfile,unittest,subprocess,threading,time
from pathlib import Path
from unittest.mock import patch
from donusturucu import core,speech
from donusturucu.operations import Editor,Request,actions
ROOT=Path(__file__).resolve().parents[1]
class SpeechTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.out=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def test_real_english_selected_interval(self):
  source=ROOT/'assets/speech/english-test.mp3';before=source.read_bytes()
  result=Editor().execute(Request('transcribe',[source],self.out,start='0.05',end='3',speech_language='en'))
  self.assertEqual(len(result),1);text=result[0].read_text();self.assertIn('could you repeat that',text.lower());self.assertNotIn('out_time',text);self.assertEqual(source.read_bytes(),before)
 def test_real_turkish(self):
  result=Editor().execute(Request('transcribe',[ROOT/'assets/speech/turkish-test.wav'],self.out,speech_language='tr'))
  text=result[0].read_text().lower();self.assertIn('merhaba',text);self.assertIn('bugün hava',text)
 def test_silence_has_no_published_output(self):
  source=self.out/'silence.wav';subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','anullsrc=r=16000:cl=mono','-t','2',str(source)],check=True)
  with self.assertRaisesRegex(speech.SpeechUnavailable,'speech_no_text'):Editor().execute(Request('transcribe',[source],self.out/'output'))
  self.assertFalse(list((self.out/'output').glob('*.txt')))
 def test_missing_model(self):
  with patch.object(speech.runtime,'ROOT',self.out),patch.object(speech,'settings',return_value={}),patch.dict('os.environ',{'DONUSTURUCU_SPEECH_MODEL':str(self.out)}):
   with self.assertRaisesRegex(speech.SpeechUnavailable,'speech_model_missing'):speech.resources()
 def test_invalid_language(self):
  with self.assertRaisesRegex(speech.SpeechUnavailable,'speech_language_invalid'):speech.transcribe(None,None,None,'ku',1)
 def test_cancel_worker(self):
  import sys
  runner=core.Runner();timer=threading.Timer(.4,runner.cancel);timer.start();start=time.monotonic()
  try:
   with self.assertRaises(core.Cancelled):runner.run([sys.executable,'-c','import time;time.sleep(30)'])
  finally:timer.cancel()
  self.assertLess(time.monotonic()-start,6)
if __name__=='__main__':unittest.main()
