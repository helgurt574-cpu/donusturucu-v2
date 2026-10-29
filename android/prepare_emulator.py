from pathlib import Path
import zipfile,stat,shutil,hashlib,json,os
ROOT=Path(__file__).resolve().parent;sdk=ROOT/'sdk';sdk.mkdir(exist_ok=True)
for item in json.loads((ROOT/'cache/emulator-manifest.json').read_text()):
 name=item['name'];archive=ROOT/'cache'/(name+'.zip')
 if archive.with_suffix('.zip.aria2').exists():print('NOT READY',name);continue
 h=hashlib.sha1()
 with archive.open('rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 assert h.hexdigest()==item['sha1']
 target=sdk if name!='image28' else sdk/'system-images/android-28/default'
 target.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(archive) as z:
  for i in z.infolist():
   dest=target/i.filename
   assert dest.resolve().is_relative_to(target.resolve())
   if i.is_dir():dest.mkdir(parents=True,exist_ok=True);continue
   dest.parent.mkdir(parents=True,exist_ok=True);mode=i.external_attr>>16
   if stat.S_ISLNK(mode):
    value=z.read(i).decode();assert (dest.parent/value).resolve().is_relative_to(target.resolve())
    if not dest.is_symlink():dest.symlink_to(value)
   else:
    with z.open(i) as f,dest.open('wb') as out:shutil.copyfileobj(f,out)
    if mode&0o777:dest.chmod(mode&0o777)
 print('EXTRACTED',name,flush=True)
