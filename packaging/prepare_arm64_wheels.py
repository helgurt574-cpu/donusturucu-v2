from pathlib import Path
import requests,concurrent.futures,hashlib,json,shutil,subprocess
from packaging.tags import cpython_tags,compatible_tags
from packaging.utils import parse_wheel_filename
BASE=Path(__file__).resolve().parents[1];dest=BASE/'build/arm64-wheels';dest.mkdir(exist_ok=True)
platforms=['manylinux2014_aarch64','manylinux_2_28_aarch64'];supported=list(cpython_tags((3,12),['cp312'],platforms))+list(compatible_tags((3,12),'cp312',platforms));rank={tag:i for i,tag in reversed(list(enumerate(supported)))}
requirements=[s.strip().split('==') for s in (BASE/'packaging/requirements-speech-linux.txt').read_text().splitlines() if s.strip()]
def resolve(item):
 name,version=item;r=requests.get('https://pypi.org/pypi/'+name+'/'+version+'/json',timeout=30);r.raise_for_status();candidates=[]
 for f in r.json()['urls']:
  if not f['filename'].endswith('.whl'):continue
  tags=parse_wheel_filename(f['filename'])[3];matching=[rank[t] for t in tags if t in rank]
  if matching:candidates.append((min(matching),f))
 if not candidates:raise RuntimeError('Missing ARM64 wheel '+name)
 return min(candidates,key=lambda x:x[0])[1]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:files=list(pool.map(resolve,requirements))
urls=[]
for f in files:
 name=f['filename'];digest=f['digests']['sha256'];target=dest/name
 candidates=[target,*Path('/tmp').glob('pip-unpack-*/'+name),*(BASE/'asr-wheelhouse').glob(name)]
 for candidate in candidates:
  if candidate.is_file() and hashlib.file_digest(candidate.open('rb'),'sha256').hexdigest()==digest:
   if candidate!=target:shutil.copy2(candidate,target)
   break
 else:urls.extend([f['url'],'  out='+name,'  checksum=sha-256='+digest])
manifest=BASE/'build/arm64-wheel-publishers.json';manifest.write_text(json.dumps(files,indent=2))
if urls:
 listing=dest/'urls.txt';listing.write_text('\n'.join(urls)+'\n');subprocess.run(['aria2c','-c','-j','6','-x','4','-s','4','--console-log-level=warn','--summary-interval=0','-d',str(dest),'-i',str(listing)],check=True)
for f in files:
 p=dest/f['filename'];assert hashlib.file_digest(p.open('rb'),'sha256').hexdigest()==f['digests']['sha256'],p
print('Publisher hashes verified:',len(files),flush=True)
