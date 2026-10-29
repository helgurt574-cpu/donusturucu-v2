"""Download/extract an isolated Ubuntu 24.04 ARM Python runtime for QEMU tests.
Does not install packages or register binfmt handlers on the host.
"""
from pathlib import Path
import requests,lzma,concurrent.futures,hashlib,subprocess,json
BASE=Path(__file__).resolve().parents[1];work=BASE/'build/arm64-test';cache=work/'downloads';cache.mkdir(parents=True,exist_ok=True);root=work/'root';root.mkdir(exist_ok=True)
names={'python3.12-minimal','libpython3.12-minimal','libpython3.12-stdlib','libc6','libstdc++6','libgcc-s1','zlib1g','libexpat1','libbz2-1.0','liblzma5','libffi8','libssl3t64','libcrypt1','libuuid1','libreadline8t64','libtinfo6','libsqlite3-0','libgomp1'}
records={}
for suite in ['noble-updates','noble']:
 p=cache/(suite+'-main-Packages.xz')
 if not p.exists():
  r=requests.get('https://ports.ubuntu.com/ubuntu-ports/dists/'+suite+'/main/binary-arm64/Packages.xz',timeout=60);r.raise_for_status();p.write_bytes(r.content)
 for record in lzma.decompress(p.read_bytes()).decode().split('\n\n'):
  fields={}
  for line in record.splitlines():
   if line and not line.startswith(' ') and ': ' in line:
    k,v=line.split(': ',1);fields[k]=v
  if fields.get('Package') in names and fields['Package'] not in records:records[fields['Package']]=fields
assert set(records)==names,names-set(records)
def get(item):
 name,info=item;p=cache/Path(info['Filename']).name
 if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=info['SHA256']:
  r=requests.get('https://ports.ubuntu.com/ubuntu-ports/'+info['Filename'],timeout=90);r.raise_for_status();p.write_bytes(r.content)
 assert hashlib.sha256(p.read_bytes()).hexdigest()==info['SHA256'];print(name,info['Version'],flush=True);return p
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:packages=list(pool.map(get,records.items()))
for p in packages:subprocess.run(['dpkg-deb','-x',str(p),str(root)],check=True)
if not (root/'lib').exists():(root/'lib').symlink_to('usr/lib')
(work/'runtime-manifest.json').write_text(json.dumps(records,indent=2));print(root,flush=True)
