"""Refresh the small existing source handoff without dependency caches or secrets."""
from pathlib import Path
import zipfile,json,hashlib
b=Path(__file__).resolve().parents[1];p=b/'dist/Donusturucu-Son-Surum-Tum-Kaynaklar.zip';prefix='Donusturucu-Kaynak/'
with zipfile.ZipFile(p) as old:data={n:old.read(n) for n in old.namelist() if not n.endswith('/')}
for n in list(data):
 rel=n.removeprefix(prefix);source=b/rel
 if source.is_file() and rel not in ['README-CODEX.md','SOURCE-MANIFEST.json']:data[n]=source.read_bytes()
for folder,pattern in [('donusturucu','*.py'),('tests','test_*srt*.py'),('tests','test_subtitles.py'),('packaging','*167.py'),('tests','test_srt_overlap.py'),('tests','*folder*.py'),('android/instrumentation/src/org/local/donusturucu/qa','Folder*.java'),('packaging','export_sources.py'),('android/src/org/local/donusturucu','SubtitleFiles.java'),('android/instrumentation/src/org/local/donusturucu/qa','Srt*.java'),('android/instrumentation/src/org/local/donusturucu/qa','Subtitle*.java'),('android/tests','srt_regression.py')]:
 for source in (b/folder).glob(pattern):data[prefix+str(source.relative_to(b))]=source.read_bytes()
data[prefix+'DUZELTME-1.6.7.txt']=(b/'DUZELTME-1.6.7.txt').read_bytes()
data[prefix+'TEST-SONUCLARI-1.6.6.txt']=(b/'TEST-SONUCLARI-1.6.6.txt').read_bytes()
data[prefix+'KULLANIM-KLASOR.txt']=(b/'KULLANIM-KLASOR.txt').read_bytes()
data[prefix+'KULLANIM-ALTYAZI.txt']=(b/'KULLANIM-ALTYAZI.txt').read_bytes()
readme=next((n for n in data if n.endswith('README-CODEX.md')),prefix+'README-CODEX.md')
header='''CURRENT HANDOFF: desktop1.6.7, Windows1.6.7.1 candidate, Android1.2.0, browser1.6.7.1.
Generated speechSRT overlap fix: normalize millisecond boundaries, preserve recognized text; unit and real-video regression reports in qa-user-video-20261028-2. Android unchanged.
Recursive folder import and sequential batch operations implemented. See KULLANIM-KLASOR.txt and tests/test_folder_batch.py.
TXT/SRT speech output implemented. Desktop SRT decodes pause-separated utterances separately; Android uses chunk boundaries.
External translation workflow: SRT → one TXT line per cue → translate elsewhere → restore TXT using original SRT. Original cue numbers/times preserved; count mismatch rejected. No translation engine or translated-text ASR realignment.
See KULLANIM-ALTYAZI.txt, tests/test_subtitles.py, tests/test_speech_srt.py, donusturucu/subtitles.py and Android SubtitleFiles.java.
Native Windows/macOS and physical Android/ARM testing unavailable. Never present emulation/static archive checks as native device tests.
Dependencies/models/SDK/binary test fixtures/signing material intentionally excluded; provision dependencies and fixture files before full integration tests. Do not archive signing keys. Historical notes below may name older releases.

'''
data[readme]=header.encode()+data.get(readme,b'')
manifest={n.removeprefix(prefix):hashlib.sha256(v).hexdigest() for n,v in data.items() if not n.endswith('SOURCE-MANIFEST.json')};data[prefix+'SOURCE-MANIFEST.json']=json.dumps(manifest,indent=2).encode()
assert not any(any(key in n for key in ['/signing/','cross-cache/','release.p12','password.txt']) for n in data)
with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
 for n,v in data.items():z.writestr(n,v)
p.with_suffix('.zip.sha256').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n');print(len(data),'source files exported')
