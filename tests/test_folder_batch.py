import unittest,tempfile,subprocess,json,hashlib
from pathlib import Path
from donusturucu import core
from donusturucu.operations import Editor,Request
SRT='1\n00:00:01,000 --> 00:00:02,000\nMerhaba فارسی\n\n'
class FolderBatchTests(unittest.TestCase):
 def test_nested_srt_three_times(self):
  rows=[]
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for repeat in range(3):
    source=root/str(repeat)/'input';(source/'alt فارسی').mkdir(parents=True);(source/'a.srt').write_text(SRT);(source/'alt فارسی/a.srt').write_text(SRT.replace('Merhaba','Silav'));(source/'bad.bin').write_bytes(b'\x00\x00bad');(source/'empty.txt').touch();(source/'loop').symlink_to(source,target_is_directory=True);(source/'link.srt').symlink_to(source/'a.srt')
    paths=list(core.expand_paths([source,source/'a.srt']));self.assertEqual(len(paths),4);before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    products,issues=Editor().execute_many(Request('subtitle_text',paths,root/str(repeat)/'output'));self.assertEqual(len(products),2);self.assertEqual(len(issues),2);self.assertEqual(len({p.name for p in products}),2)
    self.assertTrue(all('فارسی' in p.read_text() for p in products));self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths});rows.append({'repeat':repeat+1,'recursive_inputs':4,'outputs':2,'issues':2,'symlink_cycle_skipped':True,'originals_unchanged':True,'colliding_names_unique':True})
  out=Path(__file__).resolve().parents[1]/'qa-folder-1.6.6';(out/'srt-batch.json').write_text(json.dumps(rows,indent=2))
 def test_bad_media_does_not_stop_next_three_times(self):
  rows=[]
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);good=root/'good.wav';bad=root/'bad.bin';bad.write_bytes(b'\x00not media');short=root/'short.wav'
   for p,duration in [(good,'2'),(short,'0.2')]:subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:sample_rate=16000','-t',duration,str(p)],check=True)
   before={p:p.read_bytes() for p in [good,bad,short]}
   for repeat in range(3):
    progress=[];outputs,issues=Editor(core.Runner(progress=progress.append)).execute_many(Request('trim',[bad,short,good],root/str(repeat),start='.1',end='1'));self.assertEqual(len(outputs),1);self.assertEqual(len(issues),2);self.assertAlmostEqual(core.detect(outputs[0]).duration,.9,places=2);self.assertEqual(progress[-1],1);self.assertEqual(before,{p:p.read_bytes() for p in before});rows.append({'repeat':repeat+1,'outputs':1,'corrupt_and_invalid_range_reported':2,'following_file_passed':True})
   (Path(__file__).resolve().parents[1]/'qa-folder-1.6.6/media-batch.json').write_text(json.dumps(rows,indent=2))
 def test_merge_eligible_files_three_times(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);a=root/'a.wav';b=root/'b.wav';text=root/'note.txt';text.write_text('Document')
   for path in [a,b]:subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=0.4',str(path)],check=True)
   for repeat in range(3):
    outputs,issues=Editor().execute_many(Request('merge',[text,a,b],root/str(repeat),segments=[('0','')]*3),reference=a)
    self.assertEqual(len(outputs),1);self.assertEqual(len(issues),1);self.assertAlmostEqual(core.detect(outputs[0]).duration,.8,places=2)
 def test_cancel_between_files_three_times(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);files=[]
   for n in range(3):
    p=root/f'{n}.srt';p.write_text(SRT);files.append(p)
   for repeat in range(3):
    runner=core.Runner();runner.progress=lambda value:runner.cancel() if value>=1/3 else None
    with self.assertRaises(core.Cancelled):Editor(runner).execute_many(Request('subtitle_text',files,root/f'out{repeat}'))
    self.assertEqual(len(list((root/f'out{repeat}').glob('*.txt'))),1)
if __name__=='__main__':unittest.main()
