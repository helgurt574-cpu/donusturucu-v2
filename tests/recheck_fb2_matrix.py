"""Recheck every FB2 matrix edge after the XML/import fixes; retain history."""
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from donusturucu import core

root=Path(sys.argv[1]).resolve()
report_path=root/'report.json'
report=json.loads(report_path.read_text())
if 'finished' not in report:raise SystemExit('Wait for the full matrix to finish first')
(root/'before-fb2-recheck.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
for number,row in enumerate(report['cases']):
    source=Path(row['source'])
    if row['target']!='fb2' and source.suffix!='.fb2':continue
    previous={k:v for k,v in row.items() if k!='previous_attempts'}
    row.setdefault('previous_attempts',[]).append(previous)
    row.pop('error',None)
    start=time.monotonic()
    try:
        folder=root/'fb2-recheck'/str(number)
        out=core.Runner().convert(core.detect(source),row['target'],folder)
        text=(out.read_text(encoding='utf-8-sig') if row['target']=='txt' else
              core.Runner().convert(core.detect(out),'txt',folder/'readback').read_text(encoding='utf-8-sig'))
        if 'Silav' not in text:raise AssertionError('Reference text missing after re-import')
        row.update(status='pass',output=str(out),bytes=out.stat().st_size,content_checked=True)
    except Exception as exc:row.update(status='fail',error=str(exc))
    row.update(seconds=round(time.monotonic()-start,2),rechecked_after_fix=True)
    print(source.suffix,'->',row['target'],row['status'],row.get('error',''),flush=True)
report['passed']=sum(c['status']=='pass' for c in report['cases'])
report['failed']=sum(c['status']=='fail' for c in report['cases'])
report['fb2_rechecked']=True
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('FINAL',report['passed'],'PASS',report['failed'],'FAIL')
sys.exit(bool(report['failed']))
