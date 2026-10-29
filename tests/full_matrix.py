"""Real local conversions for every advertised source/target pair.

Run from the project root. Reports are retained, including failing examples.
This does not claim coverage of other operating systems or arbitrary files.
"""
import datetime
import os
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.environ.get('DONUSTURUCU_TEST_APP_ROOT',str(Path(__file__).resolve().parents[1])))
from donusturucu import core
from test_conversion import odf

root = Path(sys.argv[1]).resolve()
root.mkdir(parents=True, exist_ok=True)
report = {'platform': platform.platform(), 'started': datetime.datetime.now().isoformat(),
          'windows': 'not_run_no_guest', 'macos': 'not_run_no_guest', 'cases': [], 'app_root':str(Path(core.__file__).resolve().parents[1]), 'isolation':__import__('donusturucu.runtime',fromlist=['isolation_status']).isolation_status(), 'repeats':int(os.environ.get('DONUSTURUCU_TEST_REPEATS','1'))}
report_lock = threading.RLock()

def save():
    with report_lock:
        pending=root/'report.pending.json'
        pending.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        pending.replace(root/'report.json')

def case(group, source, target, directory, repetition=0):
    row = {'group': group, 'source': str(source), 'target': target,'repetition':repetition}
    start = time.monotonic()
    try:
        output = core.Runner().convert(core.detect(source), target, directory)
        detected = core.detect(output)
        row.update(status='pass', output=str(output), bytes=output.stat().st_size,
                   detected_kind=detected.kind, detected_format=detected.fmt)
        if group in {'audio','video'}:
            # Decode the whole file; header/probe success alone is insufficient.
            subprocess.run(['ffmpeg','-v','error','-i',str(output),'-f','null','-'],
                           check=True, capture_output=True, timeout=90)
            expected = 'audio' if target in core.AUDIO else 'video'
            if detected.kind != expected:
                raise AssertionError(f'Expected {expected}, got {detected.kind}')
        else:
            # Re-import exported documents to verify actual text is readable.
            if detected.fmt == 'txt':
                text = output.read_text(encoding='utf-8-sig')
            else:
                extracted = core.Runner().convert(detected, 'txt', directory/'readback')
                text = extracted.read_text(encoding='utf-8-sig')
            if 'Silav' not in text:
                raise AssertionError('Reference text missing after re-import')
            row['content_checked'] = True
    except Exception as exc:
        row.update(status='fail', error=str(exc)[-3000:])
    row['seconds'] = round(time.monotonic()-start,2)
    with report_lock:
        report['cases'].append(row)
        save()
    print(group, source.suffix, '->', target, row['status'], row.get('error','')[:200], flush=True)
    return Path(row['output']) if row['status']=='pass' else None

seeds = root/'seeds'
seeds.mkdir(exist_ok=True)
doc=seeds/'Belge.odt'
odf(doc,'document','<text:p>Silav cîhan! Türkçe Çığ ve Kurmancî ê î û.</text:p>')
sheet=seeds/'Tablo.ods'
odf(sheet,'spreadsheet','<table:table table:name="Yek"><table:table-row><table:table-cell office:value-type="string"><text:p>Silav cîhan</text:p></table:table-cell><table:table-cell office:value-type="float" office:value="42"><text:p>42</text:p></table:table-cell></table:table-row></table:table>')
slide=seeds/'Sunu.odp'
odf(slide,'presentation','<draw:page draw:name="page 2"><draw:frame xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" svg:x="1cm" svg:y="1cm" svg:width="20cm" svg:height="5cm"><draw:text-box><text:p>Silav cîhan! Gerçek sunu metni.</text:p></draw:text-box></draw:frame></draw:page>')
audio=seeds/'Ses.wav'
subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=0.6','-y',str(audio)],check=True)
video=seeds/'Video.mp4'
subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=160x120:r=12:d=0.6','-f','lavfi','-i','sine=frequency=440:duration=0.6','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest','-y',str(video)],check=True)
for group,seed,formats in [('document',doc,core.DOC|core.TEXT_EXPORT),
                           ('spreadsheet',sheet,{'xlsx','xls','ods','csv','tsv'}),
                           ('presentation',slide,{'ppt','pptx','odp'}),
                           ('audio',audio,core.AUDIO),('video',video,core.VIDEO)]:
    sources=[]
    for fmt in sorted(formats):
        result=case(group,seed,fmt,root/'sources'/group)
        if result:sources.append(result)
    digests={str(source):hashlib.sha256(source.read_bytes()).hexdigest() for source in sources}
    jobs=[(group,source,target,root/'outputs'/group/source.suffix[1:]/('repeat-'+str(repetition)),repetition)
          for source in sources for target in core.targets(core.detect(source)) for repetition in range(1,report['repeats']+1)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda args:case(*args), jobs))
    assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in digests.items()), 'A source changed'
    report.setdefault('preserved_sources',{}).update(digests)
report['finished']=datetime.datetime.now().isoformat()
report['passed']=sum(c['status']=='pass' for c in report['cases'])
report['failed']=sum(c['status']=='fail' for c in report['cases'])
save()
print('TOTAL',report['passed'],'PASS',report['failed'],'FAIL',flush=True)
sys.exit(bool(report['failed']))
