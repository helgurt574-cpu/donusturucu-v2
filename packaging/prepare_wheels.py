from pathlib import Path
from packaging.utils import parse_wheel_filename
import re,json,urllib.request,concurrent.futures,hashlib
cache=Path(__file__).resolve().parent/'cross-cache'
logs={'win-64':'win-wheels.log','osx-arm64':'mac-arm-wheels.log','osx-64':'mac-intel-wheels.log'}
def prepare(item):
 tag,log=item;names=set(re.findall(r'(?:Downloading|cached) ([^\s/]+\.whl)(?:\.metadata)?', (cache/log).read_text()))
 records=[]
 for filename in sorted(names):
  name,version,_,_=parse_wheel_filename(filename)
  r=json.load(urllib.request.urlopen('https://pypi.org/pypi/'+name+'/'+str(version)+'/json',timeout=30))
  record=next(x for x in r['urls'] if x['filename']==filename);records.append(record)
 if tag=='win-64':
  r=json.load(urllib.request.urlopen('https://pypi.org/pypi/colorama/json',timeout=30));records.append(next(x for x in r['urls'] if x['filename'].endswith('.whl')))
 (cache/(tag+'-wheel-manifest.json')).write_text(json.dumps(records,indent=2))
 print(tag,len(records),sum(x['size'] for x in records)//1000000,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(prepare,logs.items()))
lines=[]
for tag in logs:
 dest=cache/'wheels'/tag;dest.mkdir(exist_ok=True,parents=True)
 for x in json.loads((cache/(tag+'-wheel-manifest.json')).read_text()):
  lines.extend([x['url'],'  dir='+str(dest),'  out='+x['filename'],'  checksum=sha-256='+x['digests']['sha256']])
(cache/'wheels-aria.txt').write_text('\n'.join(lines)+'\n')
