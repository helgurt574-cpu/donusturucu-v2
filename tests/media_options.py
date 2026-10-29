"""Exercise every media output with the UI quality/resolution/bitrate values."""
from concurrent.futures import ThreadPoolExecutor
import dataclasses
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from donusturucu import core

root=Path(sys.argv[1]).resolve();root.mkdir(parents=True,exist_ok=True)
seed=Path(sys.argv[2]).resolve()
jobs=[]
for target in sorted(core.VIDEO):
    for quality in ['small','balanced','high']:
        for resolution in ['original','1080','720','480']:
            for bitrate in ['96k','128k','192k','256k','320k']:
                jobs.append((seed/'Video.mp4',target,core.Options(quality=quality,resolution=resolution,bitrate=bitrate)))
for target in sorted(core.AUDIO):
    for bitrate in ['96k','128k','192k','256k','320k']:
        jobs.append((seed/'Ses.wav',target,core.Options(bitrate=bitrate)))
def check(job):
    source,target,options=job
    row={'source':source.name,'target':target,'options':dataclasses.asdict(options)}
    try:
        out=core.Runner().convert(core.detect(source),target,root,options)
        subprocess.run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'],check=True,capture_output=True,timeout=60)
        info=core.detect(out)
        if target in core.VIDEO:
            assert info.kind=='video'
            if options.resolution!='original':assert info.height<=int(options.resolution)
        else:assert info.kind=='audio'
        row.update(status='pass',output=str(out))
    except Exception as exc:row.update(status='fail',error=str(exc))
    print(target,options.quality,options.resolution,options.bitrate,row['status'],flush=True)
    return row
with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(check,jobs))
(root/'report.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print('TOTAL',len(results),'FAILED',sum(r['status']=='fail' for r in results))
sys.exit(any(r['status']=='fail' for r in results))
