#!/usr/bin/env python3
from pathlib import Path
import subprocess,os,zipfile,stat,json,posixpath,secrets,struct,hashlib,shutil
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent;BUILD=ROOT/'build';BUILD.mkdir(exist_ok=True)
CACHE=ROOT/'cache'
SDK=Path(os.environ.get('ANDROID_HOME',Path.home()/'Android/Sdk'));TOOLS=SDK/'build-tools'/os.environ.get('DONUSTURUCU_BUILD_TOOLS','36.0.0')
JAR=Path(os.environ.get('DONUSTURUCU_ANDROID_JAR',SDK/'platforms/android-35/android.jar'));AAPT=TOOLS/'aapt2'
VERSION='1.4.2'
def run(args,**kwargs):subprocess.run(list(map(str,args)),check=True,**kwargs)
classes=BUILD/'classes';
if classes.exists():shutil.rmtree(classes)
classes.mkdir(exist_ok=True)
cp=os.pathsep.join(str(CACHE/n) for n in ['pdfbox.jar','bcprov.jar','bcpkix.jar','bcutil.jar','tesseract.jar','sherpa.jar','kotlin.jar'])
run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-source','8','-target','8','-bootclasspath',JAR,'-cp',cp,'-d',classes,*sorted((ROOT/'src').rglob('*.java'))])
compiled=BUILD/'resources.zip';run([AAPT,'compile','--dir',ROOT/'res','-o',compiled])
resource_apk=BUILD/'resources.apk';run([AAPT,'link','-o',resource_apk,'-I',JAR,'--manifest',ROOT/'AndroidManifest.xml','-A',ROOT/'assets','-0','onnx',compiled])
classjar=BUILD/'classes.jar'
with zipfile.ZipFile(classjar,'w',zipfile.ZIP_DEFLATED) as z:
 for f in classes.rglob('*.class'):z.write(f,str(f.relative_to(classes)))
dex=BUILD/'dex';
if dex.exists():shutil.rmtree(dex)
dex.mkdir(exist_ok=True)
run(['java','-cp',TOOLS/'lib/d8.jar','com.android.tools.r8.D8','--min-api','28','--lib',JAR,'--output',dex,classjar,*[CACHE/n for n in ['pdfbox.jar','bcprov.jar','bcpkix.jar','bcutil.jar','tesseract.jar','sherpa.jar','kotlin.jar']]])
# Keep the publisher ELF executables. Shared-library symlinks are recreated by
# Android Os.symlink in private app storage after the bundled zip is unpacked.
abi=os.environ.get('DONUSTURUCU_ANDROID_ABI','arm64-v8a');libdir=ROOT/'native/lib'/abi;original=libdir/'libffmpeg.zip.so';flat=BUILD/'libffmpeg.zip.so'
with zipfile.ZipFile(original) as src,zipfile.ZipFile(flat,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
 links={}
 for i in src.infolist():
  if i.is_dir():continue
  if stat.S_ISLNK(i.external_attr>>16):links[i.filename]=src.read(i).decode()
  else:dst.writestr(i.filename,src.read(i))
 extra=ROOT/'extra-libs'/abi
 if extra.exists():
  links.update(json.loads((extra/'_links.json').read_text()))
  for f in extra.rglob('*'):
   if f.is_file() and f.name!='_links.json':dst.writestr(str(f.relative_to(extra)),f.read_bytes())
 dst.writestr('_links.json',json.dumps(links))
unsigned=BUILD/'unsigned.apk'
with zipfile.ZipFile(resource_apk) as src,zipfile.ZipFile(unsigned,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
 for i in src.infolist():dst.writestr(i,src.read(i))
 for f in dex.glob('*.dex'):dst.write(f,f.name)
 for f in libdir.iterdir():
  if f.is_file():dst.write(flat if f.name=='libffmpeg.zip.so' else f,'lib/'+abi+'/'+f.name)
# Align uncompressed resource data, without requiring a host-installed zipalign.
aligned=BUILD/'aligned.apk'
with zipfile.ZipFile(unsigned) as src,zipfile.ZipFile(aligned,'w') as dst:
 for old in src.infolist():
  info=zipfile.ZipInfo(old.filename,old.date_time);info.external_attr=old.external_attr;info.compress_type=zipfile.ZIP_STORED if old.filename=='resources.arsc' else old.compress_type
  if info.compress_type==zipfile.ZIP_STORED:
   offset=dst.fp.tell()+30+len(info.filename.encode('utf-8'));padding=(-offset)%4
   if padding:info.extra=struct.pack('<HH',0xd935,padding)+b'\0'*padding
  dst.writestr(info,src.read(old))
signing=Path(os.environ.get('DONUSTURUCU_SIGNING_DIR',ROOT/'signing'));signing.mkdir(parents=True,exist_ok=True);signing.chmod(0o700);password=signing/'password.txt';key=signing/'release.p12'
if not password.exists():password.write_text(secrets.token_urlsafe(32));password.chmod(0o600)
if not key.exists():
 env=os.environ.copy();env['DONUSTURUCU_APK_SIGNING_PASSWORD']=password.read_text().strip()
 run(['keytool','-genkeypair','-keystore',key,'-storetype','PKCS12','-alias','donusturucu','-keyalg','RSA','-keysize','3072','-validity','10000','-dname','CN=Donusturucu Local,OU=Offline Applications,O=Local,C=TR','-storepass:env','DONUSTURUCU_APK_SIGNING_PASSWORD','-keypass:env','DONUSTURUCU_APK_SIGNING_PASSWORD'],env=env);key.chmod(0o600)
dist=Path(os.environ.get('DONUSTURUCU_DIST',PROJECT/'dist'));dist.mkdir(parents=True,exist_ok=True)
out=dist/('Donusturucu-Android-'+{'arm64-v8a':'arm64','armeabi-v7a':'arm32','x86_64':'x86_64'}.get(abi,abi)+'.apk');signer=TOOLS/'lib/apksigner.jar'
run(['java','-cp',signer,'com.android.apksigner.ApkSignerTool','sign','--ks',key,'--ks-pass','file:'+str(password),'--ks-key-alias','donusturucu','--out',out,aligned])
run(['java','-cp',signer,'com.android.apksigner.ApkSignerTool','verify','--verbose',out])
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None;assert 'classes.dex' in z.namelist();assert 'lib/'+abi+'/libffmpeg.so' in z.namelist()
 data=z.read('AndroidManifest.xml');assert 'android.permission.INTERNET'.encode('utf-16-le') not in data
out.with_suffix('.apk.sha256').write_text(hashlib.sha256(out.read_bytes()).hexdigest()+'  '+out.name+'\n');print('BUILT',out,out.stat().st_size)
