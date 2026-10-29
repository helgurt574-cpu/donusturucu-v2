"""Build-time downloads only; verifies every conda archive against its publisher hash."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,urllib.request,subprocess,time
BASE=Path(__file__).resolve().parent;cache=BASE/'cross-cache';pkgs=cache/'packages';pkgs.mkdir(exist_ok=True)
items={}
for tag in ['win-64','osx-arm64','osx-64']:
 r=json.loads((cache/(tag+'-solve.json')).read_text());assert r['success']
 for x in r['actions']['FETCH']:items[x['url']]=x
(cache/'all-packages.json').write_text(json.dumps(list(items.values()),indent=2))
def download(x):
 folder=pkgs/x['subdir'];folder.mkdir(exist_ok=True);target=folder/x['fn']
 if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==x['sha256']:return
 for attempt in range(4):
  try:
   tmp=target.with_suffix(target.suffix+'.part')
   with urllib.request.urlopen(x['url'],timeout=90) as src,tmp.open('wb') as dst:
    while chunk:=src.read(1024*1024):dst.write(chunk)
   assert hashlib.sha256(tmp.read_bytes()).hexdigest()==x['sha256'],'HASH MISMATCH'
   tmp.replace(target);print(x['subdir'],x['fn'],x['size'],flush=True);return
  except Exception as e:
   print('RETRY',attempt,x['fn'],str(e),flush=True);time.sleep(2)
 raise RuntimeError(x['url'])
with ThreadPoolExecutor(max_workers=10) as pool:list(pool.map(download,items.values()))
print('COMPLETE',len(items),flush=True)
