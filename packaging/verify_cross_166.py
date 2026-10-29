from pathlib import Path
import subprocess,json,hashlib,plistlib,gzip
BASE=Path(__file__).resolve().parents[1];rows=[]
for tag in ['win-64','osx-arm64','osx-64']:
 work=BASE/'build/cross'/tag
 app=work/'app' if tag=='win-64' else work/'payload/Applications/Donusturucu.app/Contents/Resources/app'
 filename='Windows-x64-Kurulum.exe' if tag=='win-64' else 'macOS-'+('Apple-Silicon' if tag=='osx-arm64' else 'Intel')+'-Kurulum.pkg'
 version='1.6.6.1' if tag=='win-64' else '1.6.6'
 archive=BASE/'dist'/('Donusturucu-'+version+'-'+filename)
 result=subprocess.run(['7z','l' if tag=='win-64' else 't',* ([] if tag=='win-64' else ['-txar']),str(archive)],capture_output=True,text=True);assert result.returncode==0,result.stdout+result.stderr
 manifest=json.loads((app/'native-package-manifest.json').read_text());assert manifest['version']==version and not manifest['native_runtime_tested']
 for source in (BASE/'donusturucu').glob('*.py'):assert source.read_bytes()==(app/'donusturucu'/source.name).read_bytes(),source
 assert all((app/'tools/tessdata'/f'{language}.traineddata').is_file() for language in ['tur','eng','kmr','ara','fas'])
 assert (app/'asr-models/whisper-small/model.bin').is_file()
 if tag=='win-64':
  dest=BASE/'build/cross-166-extracted';dest.mkdir(exist_ok=True)
  subprocess.run(['7z','x','-y','-o'+str(dest),str(archive),'donusturucu/*.py','native-package-manifest.json'],check=True,stdout=subprocess.DEVNULL)
  for source in (BASE/'donusturucu').glob('*.py'):assert (dest/'donusturucu'/source.name).read_bytes()==source.read_bytes(),source
  assert (dest/'native-package-manifest.json').read_bytes()==(app/'native-package-manifest.json').read_bytes()

 else:
  proc=subprocess.Popen(['7z','x','-txar','-so',str(archive),'Donusturucu.pkg/Payload'],stdout=subprocess.PIPE)
  found={};prefix='Applications/Donusturucu.app/Contents/Resources/app/donusturucu/'
  with gzip.GzipFile(fileobj=proc.stdout) as stream:
   while True:
    header=stream.read(76)
    if not header:break
    assert len(header)==76 and header[:6]==b'070707'
    size=int(header[65:76],8);name=stream.read(int(header[59:65],8)).rstrip(b'\0').decode()
    digest=hashlib.sha256();remaining=size
    while remaining:
     chunk=stream.read(min(1024*1024,remaining));assert chunk;digest.update(chunk);remaining-=len(chunk)
    if name.startswith(prefix) and name.endswith('.py'):found[name[len(prefix):]]=digest.hexdigest()
    if name=='TRAILER!!!':
     while stream.read(1024*1024):pass
     break
  assert proc.wait()==0
  print('payload modules',tag,sorted(found),flush=True)
  for source in (BASE/'donusturucu').glob('*.py'):assert found[source.name]==hashlib.sha256(source.read_bytes()).hexdigest(),source
  bundle=app.parents[2];p=plistlib.loads((bundle/'Contents/Info.plist').read_bytes());assert p['CFBundleShortVersionString']=='1.6.6'
 h=hashlib.sha256()
 with archive.open('rb') as f:
  while data:=f.read(1024*1024):h.update(data)
 digest=h.hexdigest();assert archive.with_suffix(archive.suffix+'.sha256').read_text().split()[0]==digest
 rows.append({'platform':tag,'path':str(archive),'bytes':archive.stat().st_size,'sha256':digest,'archive_integrity':True,'source_modules_match':True,'version':version,'ocr_languages_present':True,'speech_model_present':True,'native_runtime_executed':False})
 print(tag,'verified',flush=True)
(BASE/'packaging/cross-static-validation-1.6.6.json').write_text(json.dumps(rows,indent=2)+'\n')
