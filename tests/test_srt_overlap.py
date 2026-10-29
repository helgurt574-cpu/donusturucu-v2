import unittest
from donusturucu.speech_worker import normalize_srt,cue
class OverlapTests(unittest.TestCase):
 def test_overlap_keeps_text(self):
  data=[dict(start=1,end=4,text='Türkçe'),dict(start=3.6,end=5,text='العربية'),dict(start=4.8,end=6,text='فارسی')]
  out=normalize_srt(data)
  self.assertEqual([x['text'] for x in out],[x['text'] for x in data]);self.assertEqual(out[0]['end'],3.6)
  self.assertTrue(all(a['end']<=b['start'] for a,b in zip(out,out[1:])));self.assertEqual(data[0]['end'],4)
 def test_contained_cue_merges(self):
  out=normalize_srt([dict(start=1,end=5,text='bir'),dict(start=.5,end=3,text='iki'),dict(start=5,end=6,text='üç')])
  self.assertEqual(out[0]['text'],'bir iki');self.assertEqual(len(out),2)
 def test_millisecond_rounding_and_offset(self):
  out=normalize_srt([dict(start=0,end=1.0006,text='a'),dict(start=1.0004,end=2,text='b')])
  self.assertEqual(out[0]['end'],out[1]['start']);self.assertIn('00:00:04,000 --> 00:00:05,000',cue(2,out[1]['start'],out[1]['end'],'b',3))
if __name__=='__main__':unittest.main()
