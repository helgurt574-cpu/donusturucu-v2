#!/usr/bin/env python3
"""Android App Bundle for Google Play.

build_apk.py compiles the code, resources and the FFmpeg archive first; this script lays them out as
bundle modules: `base` (code, resources, native libraries, OCR data) and the install-time asset pack
`speech_models` (the 374 MB speech model), which keeps the base module under Play's size limit.
Install-time packs are installed with the app and read through AssetManager like any other asset,
so the app needs no code for them. The bundle is signed with the upload key in signing/.
"""
from pathlib import Path
import subprocess,os,zipfile,json,hashlib,shutil,glob
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent;BUILD=ROOT/'build';CACHE=ROOT/'cache'
SDK=Path(os.environ.get('ANDROID_HOME',Path.home()/'Android/Sdk'));TOOLS=SDK/'build-tools'/os.environ.get('DONUSTURUCU_BUILD_TOOLS','36.0.0')
JAR=Path(os.environ.get('DONUSTURUCU_ANDROID_JAR',SDK/'platforms/android-36/android.jar'));AAPT=TOOLS/'aapt2'
abi=os.environ.get('DONUSTURUCU_ANDROID_ABI','arm64-v8a');libdir=ROOT/'native/lib'/abi
PACK='speech_models'
def run(args,**kw):subprocess.run(list(map(str,args)),check=True,**kw)
# bundletool from the Gradle cache (no Gradle needed): the library jar plus its dependencies.
DEPS=['com.android.tools.build/bundletool','com.google.guava/guava','com.google.guava/failureaccess','com.google.protobuf/protobuf-java',
 'com.google.protobuf/protobuf-java-util','com.android.tools.build/aapt2-proto','com.google.dagger/dagger','javax.inject/javax.inject',
 'org.bitbucket.b_c/jose4j','com.google.code.gson/gson','com.google.auto.value/auto-value-annotations']
def bundletool():
 if os.environ.get('BUNDLETOOL'):return ['java','-jar',os.environ['BUNDLETOOL']]
 cache=Path.home()/'.gradle/caches/modules-2/files-2.1';jars=[]
 def version(v):return [int(x) if x.isdigit() else 0 for x in v.replace('-','.').split('.')]
 for dep in DEPS:
  versions=sorted((d for d in (cache/dep).glob('*') if d.is_dir() and not d.name.endswith('android')),key=lambda d:version(d.name))
  found=[j for d in versions[-1:] for j in d.glob('*/*.jar') if not j.name.endswith('-sources.jar')]
  if not found:raise SystemExit('bundletool için eksik: '+dep+' (BUNDLETOOL=/yol/bundletool-all.jar verin)')
  jars.append(str(found[0]))
 return ['java','-cp',os.pathsep.join(jars),'com.android.tools.build.bundletool.BundleToolMain']
BT=bundletool()

# 1. Code, compiled resources and the flattened FFmpeg archive (the APK is a by-product).
run(['python3',ROOT/'build_apk.py'],env=dict(os.environ,DONUSTURUCU_DIST=str(BUILD/'apk-for-bundle')))
work=BUILD/'bundle';shutil.rmtree(work,ignore_errors=True);work.mkdir(parents=True)

# 2. Base module: resources in protobuf form, as bundletool expects.
proto=work/'base-proto.zip'
run([AAPT,'link','--proto-format','-o',proto,'-I',JAR,'--manifest',ROOT/'AndroidManifest.xml',BUILD/'resources.zip'])
base=work/'base.zip'
with zipfile.ZipFile(proto) as src,zipfile.ZipFile(base,'w',zipfile.ZIP_DEFLATED) as dst:
 for i in src.infolist():
  name='manifest/AndroidManifest.xml' if i.filename=='AndroidManifest.xml' else i.filename
  dst.writestr(name,src.read(i))
 for f in sorted((BUILD/'dex').glob('*.dex')):dst.write(f,'dex/'+f.name)
 for f in sorted(libdir.iterdir()):
  if f.is_file():dst.write(BUILD/'libffmpeg.zip.so' if f.name=='libffmpeg.zip.so' else f,'lib/'+abi+'/'+f.name)
 for f in sorted((ROOT/'assets').rglob('*')):
  rel=f.relative_to(ROOT/'assets').as_posix()
  if f.is_file() and not rel.startswith('speech/'):dst.write(f,'assets/'+rel)

# 3. Install-time asset pack with the speech model.
pack_manifest=work/'pack-manifest.xml'
pack_manifest.write_text('''<manifest xmlns:android="http://schemas.android.com/apk/res/android" xmlns:dist="http://schemas.android.com/apk/distribution" package="com.donusturucu.app" split="%s">
 <dist:module dist:type="asset-pack"><dist:fusing dist:include="true"/><dist:delivery><dist:install-time/></dist:delivery></dist:module>
</manifest>'''%PACK)
pack_proto=work/'pack-proto.zip'
run([AAPT,'link','--proto-format','-o',pack_proto,'-I',JAR,'--manifest',pack_manifest])
pack=work/(PACK+'.zip')
with zipfile.ZipFile(pack_proto) as src,zipfile.ZipFile(pack,'w',zipfile.ZIP_DEFLATED) as dst:
 dst.writestr('manifest/AndroidManifest.xml',src.read('AndroidManifest.xml'))
 for f in sorted((ROOT/'assets/speech').rglob('*')):
  if f.is_file():dst.write(f,'assets/'+f.relative_to(ROOT/'assets').as_posix())

# 4. Bundle. Native libraries stay compressed and are extracted on install (the app runs FFmpeg from
#    the library folder); the ONNX model stays uncompressed so it can be mapped from the APK.
config=work/'BundleConfig.json'
config.write_text(json.dumps({'optimizations':{'uncompressNativeLibraries':{'enabled':False},
 'splitsConfig':{'splitDimension':[{'value':'ABI'},{'value':'SCREEN_DENSITY','negate':True},{'value':'LANGUAGE','negate':True},{'value':'TEXTURE_COMPRESSION_FORMAT','negate':True}]}},
 'compression':{'uncompressedGlob':['assets/**/*.onnx']}}))
dist=Path(os.environ.get('DONUSTURUCU_DIST',PROJECT/'dist'));dist.mkdir(parents=True,exist_ok=True)
out=dist/('Donusturucu-'+{'arm64-v8a':'arm64','x86_64':'x86_64'}.get(abi,abi)+'.aab');out.unlink(missing_ok=True)
run(BT+['build-bundle','--modules',str(base)+','+str(pack),'--config',config,'--output',out])

# 5. Upload signature (same key as the APK; Play re-signs for devices with Play App Signing).
signing=Path(os.environ.get('DONUSTURUCU_SIGNING_DIR',ROOT/'signing'))
run(['jarsigner','-keystore',signing/'release.p12','-storetype','PKCS12','-storepass:file',signing/'password.txt',
     '-sigalg','SHA256withRSA','-digestalg','SHA-256',out,'donusturucu'],stdout=subprocess.DEVNULL)
run(['jarsigner','-verify',out],stdout=subprocess.DEVNULL)
run(BT+['validate','--bundle',out],stdout=subprocess.DEVNULL)
with zipfile.ZipFile(out) as z:
 names=z.namelist();assert 'base/dex/classes.dex' in names and 'base/lib/'+abi+'/libffmpeg.so' in names and any(n.startswith(PACK+'/assets/speech/') for n in names)
out.with_suffix('.aab.sha256').write_text(hashlib.sha256(out.read_bytes()).hexdigest()+'  '+out.name+'\n')
print('BUILT',out,out.stat().st_size)
