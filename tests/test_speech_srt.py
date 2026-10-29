import unittest,re,tempfile,json,subprocess
from pathlib import Path
from donusturucu.speech_worker import stamp,cue
from donusturucu.operations import Editor,Request
ROOT=Path(__file__).resolve().parents[1]
class SrtTests(unittest.TestCase):
 def test_timestamp(self):
  self.assertEqual(stamp(3599.9996),'01:00:00,000')
  self.assertEqual(stamp(3661.125),'01:01:01,125')
  self.assertIn('Türkçe العربية فارسی',cue(1,0,1,'Türkçe  العربية\nفارسی',3))
  for value in [-1,float('nan'),float('inf')]:
   with self.assertRaises(ValueError):stamp(value)
 def test_srt_silence_three_times(self):
  from donusturucu.speech import SpeechUnavailable
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);source=root/'silence.wav'
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','anullsrc=r=16000:cl=mono','-t','2',str(source)],check=True)
   for repeat in range(3):
    folder=root/str(repeat)
    with self.assertRaisesRegex(SpeechUnavailable,'speech_no_text'):Editor().execute(Request('transcribe',[source],folder,speech_format='srt'))
    self.assertFalse(list(folder.glob('*.srt')))
 def test_multiple_cues_three_times(self):
  with tempfile.TemporaryDirectory() as directory:
   rows=[];source=ROOT/'android/instrumentation/assets/long-en.wav';before=source.read_bytes()
   for repeat in range(3):
    result=Editor().execute(Request('transcribe',[source],Path(directory)/str(repeat),start='3',speech_language='en',speech_format='srt'))[0]
    value=result.read_text();blocks=value.strip().split('\n\n');self.assertGreater(len(blocks),1);self.assertEqual(value.lower().count('repeat that'),12);previous=3
    for index,block in enumerate(blocks,1):
     lines=block.splitlines();self.assertEqual(int(lines[0]),index)
     times=[]
     for stamp_ in lines[1].split(' --> '):
      h,m,s=stamp_.replace(',','.').split(':');times.append(int(h)*3600+int(m)*60+float(s))
     self.assertGreaterEqual(times[0],previous-.001);self.assertGreater(times[1],times[0]);previous=times[1]
    self.assertEqual(source.read_bytes(),before);rows.append({'repeat':repeat+1,'cues':len(blocks),'pass':True})
   (ROOT/'qa-srt-1.6.4/multiple-cues.json').write_text(json.dumps(rows,indent=2))
 def test_real_outputs_three_times(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);rows=[]
   for repeat in range(3):
    for lang,name,end,word in [('en','english-test.mp3','3','repeat that'),('tr','turkish-test.wav','6','merhaba')]:
     source=ROOT/'assets/speech'/name;before=source.read_bytes();texts={}
     for fmt in ['txt','srt']:
      result=Editor().execute(Request('transcribe',[source],root/f'{repeat}-{lang}-{fmt}',start='0.05',end=end,speech_language=lang,speech_format=fmt))[0]
      value=result.read_text();self.assertEqual(result.suffix,'.'+fmt);self.assertIn(word,value.lower());texts[fmt]=value
      if fmt=='srt':
       blocks=value.strip().split('\n\n');plain=[];previous=0.05
       for index,block in enumerate(blocks,1):
        lines=block.splitlines();self.assertEqual(int(lines[0]),index);a,b=lines[1].split(' --> ')
        def seconds(s):
         self.assertRegex(s,r'^\d{2}:\d{2}:\d{2},\d{3}$');h,m,rest=s.split(':');return int(h)*3600+int(m)*60+float(rest.replace(',','.'))
        start,stop=seconds(a),seconds(b);self.assertGreaterEqual(start,previous-.001);self.assertGreater(stop,start);self.assertLessEqual(stop,float(end)+.001);previous=stop;plain.extend(lines[2:])
       texts['srt']=' '.join(plain)
     self.assertNotIn(' --> ',texts['txt']);self.assertEqual(before,source.read_bytes());rows.append({'repeat':repeat+1,'language':lang,'formats':['txt','srt'],'pass':True})
   out=ROOT/'qa-srt-1.6.4';out.mkdir(exist_ok=True);(out/'desktop.json').write_text(json.dumps({'cases':12,'rows':rows,'source_unchanged':True},indent=2))
if __name__=='__main__':unittest.main()
