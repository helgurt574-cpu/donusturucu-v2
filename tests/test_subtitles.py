import unittest,tempfile,json,hashlib,subprocess
from pathlib import Path
from donusturucu import core,subtitles
from donusturucu.operations import Editor,Request
SRT='7\n00:00:01,250 --> 00:00:03,500\nHello there.\nSecond line.\n\n9\n01:02:03,004 --> 01:02:06,999\nHow are you?\n\n'
class SubtitleTests(unittest.TestCase):
 def test_translation_roundtrip_three_times(self):
  rows=[]
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for repeat in range(3):
    original=root/f'original-{repeat}.srt';original.write_text('\ufeff'+SRT.replace('\n','\r\n'),encoding='utf-8');before=original.read_bytes()
    info=core.detect(original);self.assertEqual(info.fmt,'srt');self.assertEqual(core.targets(info),['txt'])
    text=core.Runner().convert(info,'txt',root/f'export-{repeat}');self.assertEqual(text.read_text(),'Hello there. Second line.\nHow are you?\n')
    translated=root/f'translated-{repeat}.txt';translated.write_text('Merhaba — سڵاو العربية فارسی\nTu çawa yî? İyi misin?\n',encoding='utf-8');snapshot=translated.read_bytes()
    output=Editor().execute(Request('subtitle_restore',[translated],root/f'import-{repeat}',audio=str(original)))[0]
    old,new=subtitles.parse(SRT),subtitles.parse(output.read_text());self.assertEqual([(n,t) for n,t,_ in old],[(n,t) for n,t,_ in new]);self.assertIn('فارسی',new[0][2]);self.assertEqual(snapshot,translated.read_bytes());self.assertEqual(before,original.read_bytes())
    check=subprocess.run(['ffprobe','-v','error','-select_streams','s','-show_entries','packet=pts_time,duration_time','-of','json',str(output)],capture_output=True,text=True,check=True);self.assertEqual(len(json.loads(check.stdout)['packets']),2)
    bad=root/'bad.txt';bad.write_text('One line only\n')
    with self.assertRaisesRegex(subtitles.SubtitleError,'subtitle_line_count'):Editor().execute(Request('subtitle_restore',[bad],root/'rejected',audio=str(original)))
    self.assertFalse(list((root/'rejected').glob('*.srt')))
    rows.append({'repeat':repeat+1,'utf8_rtl':True,'timing_and_numbers_preserved':True,'originals_unchanged':True,'ffprobe_readable':True,'wrong_line_count_rejected':True})
  out=Path(__file__).resolve().parents[1]/'qa-subtitles-1.6.5';out.mkdir(exist_ok=True);(out/'roundtrip.json').write_text(json.dumps(rows,indent=2))
 def test_invalid(self):
  for text in ['', '1\n00:00:00,000 --> 00:00:00,000\nword','1\n00:65:00,000 --> 00:66:00,000\nword','word']:
   with self.assertRaises(subtitles.SubtitleError):subtitles.parse(text)
if __name__=='__main__':unittest.main()
