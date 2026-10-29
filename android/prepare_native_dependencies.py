from pathlib import Path
import zipfile,stat,subprocess,re,json,posixpath,shutil
ROOT=Path(__file__).resolve().parent
SYSTEM={'libc.so','libm.so','libdl.so','liblog.so','libandroid.so','libOpenSLES.so','libvulkan.so','libEGL.so','libGLESv2.so','libGLESv1_CM.so','libjnigraphics.so','libz.so','libmediandk.so','libcamera2ndk.so','libstdc++.so'}
for abi in ['x86_64','arm64-v8a','armeabi-v7a']:
 out=ROOT/'extra-libs'/abi
 if out.exists():shutil.rmtree(out)
 out.mkdir(parents=True);scan=ROOT/'dependency-scan'/abi;scan.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(ROOT/'native/lib'/abi/'libffmpeg.zip.so') as original,zipfile.ZipFile(ROOT/'cache'/('python-'+abi+'.zip')) as py:
  visited=set();links={};missing=set()
  def visit(name):
   if name in SYSTEM or name in visited:return
   visited.add(name);native=ROOT/'native/lib'/abi/name
   if native.is_file() and not name.endswith('.zip.so'):data=native.read_bytes()
   else:
    full='usr/lib/'+name;source=original if full in original.namelist() else py if full in py.namelist() else None
    if source is None:missing.add(name);return
    entry=source.getinfo(full);data=source.read(entry)
    if stat.S_ISLNK(entry.external_attr>>16):
     target=data.decode()
     if source is py:links[entry.filename]=target
     visit(Path(target).name);return
    if source is py:
     p=out/full;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
   if data.startswith(b'\x7fELF'):
    p=scan/name;p.write_bytes(data);dynamic=subprocess.check_output(['readelf','-d',str(p)],text=True)
    for needed in re.findall(r'\(NEEDED\).*\[(.*?)\]',dynamic):visit(needed)
  visit('libffmpeg.so');visit('libffprobe.so')
  (out/'_links.json').write_text(json.dumps(links));print(abi,'missing',sorted(missing),'copied',[(p.name,p.stat().st_size) for p in out.rglob('*') if p.is_file()],flush=True)
  (ROOT/'cache'/('native-closure-'+abi+'.json')).write_text(json.dumps(dict(visited=sorted(visited),missing=sorted(missing),system=sorted(SYSTEM)),indent=2))
