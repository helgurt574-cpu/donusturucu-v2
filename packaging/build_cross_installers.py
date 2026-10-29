#!/usr/bin/env python3
"""Assemble actual offline installers on Linux from publisher native binaries.
These artifacts are explicitly NOT certified by running Windows/macOS here.
Each installer runs conversion/OCR/RTL/speech self-tests on the target system.
"""
from pathlib import Path
import argparse,hashlib,json,os,plistlib,shutil,subprocess,sys,tarfile,gzip
BASE=Path(__file__).resolve().parents[1];PKG=BASE/'packaging';CACHE=PKG/'cross-cache';DIST=BASE/'dist';VERSION='1.6.7'
p=argparse.ArgumentParser();p.add_argument('platform',choices=['win-64','osx-arm64','osx-64']);args=p.parse_args();tag=args.platform
if tag=='win-64':VERSION='1.6.7.1'
work=BASE/'build/cross'/tag;work.mkdir(parents=True,exist_ok=True)
def copy(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists():return
 try:os.link(src,dst)
 except OSError:shutil.copy2(src,dst)
def verify(path,digest):
 if not path.is_file():raise SystemExit('Missing local file: '+str(path))
 h=hashlib.sha256()
 with path.open('rb') as stream:
  while chunk:=stream.read(1024*1024):h.update(chunk)
 if h.hexdigest()!=digest:raise SystemExit('Hash mismatch: '+str(path))
def cmd(arguments,**kwargs):subprocess.run(list(map(str,arguments)),check=True,**kwargs)
plan=json.loads((CACHE/(tag+'-solve.json')).read_text());assert plan['success']
wheels=json.loads((CACHE/(tag+'-wheel-manifest.json')).read_text())
for record in plan['actions']['FETCH']:verify(CACHE/'packages'/record['subdir']/record['fn'],record['sha256'])
for record in wheels:verify(CACHE/'wheels'/tag/record['filename'],record['digests']['sha256'])
lo_meta=CACHE/'libreoffice'/(tag+'.meta4')
import xml.etree.ElementTree as ET
lo_xml=ET.fromstring(lo_meta.read_bytes());lo_file=next(x for x in lo_xml.iter() if x.tag.endswith('}file'))
lo_archive=CACHE/'libreoffice'/lo_file.get('name');lo_digest=next(x.text for x in lo_xml.iter() if x.tag.endswith('}hash') and x.get('type')=='sha-256');verify(lo_archive,lo_digest)
lo_root=CACHE/'lo-expanded'/tag
if not (lo_root/'READY').exists():
 lo_root.mkdir(parents=True,exist_ok=True)
 if tag=='win-64':
  env=os.environ.copy();env['LD_LIBRARY_PATH']=str(CACHE/'extractors/usr/lib/x86_64-linux-gnu')
  cmd([CACHE/'extractors/usr/bin/msiextract','-C',lo_root,lo_archive],env=env,stdout=subprocess.DEVNULL)
 else:
  extraction=subprocess.run(['7z','x','-y','-o'+str(lo_root),str(lo_archive),'LibreOffice/LibreOffice.app/*'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
  if extraction.returncode and any(line and not line.startswith(('ERROR: Dangerous link path was ignored','ERROR: Dangerous symbolic link path was ignored')) for line in extraction.stderr.splitlines()):raise RuntimeError(extraction.stderr)
  # 7-Zip 23 refuses even safe ../ links. Restore only publisher archive links
  # whose resolved destination remains inside this LibreOffice.app.
  listing=subprocess.check_output(['7z','l','-slt',str(lo_archive)],text=True)
  for block in listing.split('\n\n'):
   fields=dict(line.split(' = ',1) for line in block.splitlines() if ' = ' in line)
   name=fields.get('Path','')
   if not name.startswith('LibreOffice/LibreOffice.app/') or not fields.get('Mode','').startswith('l'):continue
   dest=lo_root/name
   if dest.is_symlink():continue
   link=subprocess.check_output(['7z','x','-so',str(lo_archive),name]).decode().rstrip('\x00')
   base=lo_root/'LibreOffice/LibreOffice.app'
   if Path(link).is_absolute() or not (dest.parent/link).resolve().is_relative_to(base.resolve()):raise RuntimeError('Unsafe app link: '+name)
   dest.parent.mkdir(parents=True,exist_ok=True)
   if dest.exists():dest.unlink()
   dest.symlink_to(link)

 (lo_root/'READY').touch()
lo_binary=next(lo_root.rglob('soffice.com' if tag=='win-64' else 'soffice'),None)
if lo_binary is None:raise SystemExit('LibreOffice extraction did not expose the native executable')
if tag=='win-64':lo_source=lo_binary.parent.parent
else:lo_source=next(parent for parent in lo_binary.parents if parent.suffix=='.app')
if tag=='win-64':app=work/'app'
else:app=work/'payload/Applications/Donusturucu.app/Contents/Resources/app'
app.mkdir(parents=True,exist_ok=True)
# Rebuild source directories so an old module cannot survive a new release.
for dirname in ['donusturucu']:
 dest=app/dirname
 if dest.exists():shutil.rmtree(dest)
 shutil.copytree(BASE/dirname,dest,ignore=shutil.ignore_patterns('__pycache__'))
for name in ['KULLANIM.txt','TEST-SONUCLARI-WINDOWS-MACOS-'+VERSION+'.txt']:
 if (BASE/name).exists():shutil.copy2(BASE/name,app/name)
shutil.copy2(PKG/'launch_bundle.py',app/'launch.py')
for name in ['entry.py','ocr-smoke.png','ocr-smoke-ara.png','ocr-smoke-fas.png']:copy(PKG/name,app/'packaging'/name)
# Model is shared data, native dependencies and Python are architecture-specific.
for file in (BASE/'asr-models/whisper-small').iterdir():
 if file.is_file():copy(file,app/'asr-models/whisper-small'/file.name)
for file in (BASE/'assets/speech').iterdir():
 if file.is_file():copy(file,app/'assets/speech'/file.name)
for record in plan['actions']['FETCH']:copy(CACHE/'packages'/record['subdir']/record['fn'],app/'packages'/record['fn'])
for record in wheels:copy(CACHE/'wheels'/tag/record['filename'],app/'wheels'/record['filename'])
for lang in ['eng','tur','kmr','ara','fas']:
 candidates=[BASE/'vendor/ocr/usr/share/tesseract-ocr/5/tessdata'/(lang+'.traineddata'),Path('/usr/share/tesseract-ocr/5/tessdata')/(lang+'.traineddata')]
 source=next((x for x in candidates if x.is_file()),None)
 if source is None:raise SystemExit('Missing OCR data: '+lang)
 copy(source,app/'tools/tessdata'/source.name)
lo_dest=app/'tools'/('LibreOffice' if tag=='win-64' else 'LibreOffice.app')
if not lo_dest.exists():shutil.copytree(lo_source,lo_dest,symlinks=True)
(app/'native-package-manifest.json').write_text(json.dumps({'version':VERSION,'platform':tag,'native_runtime_tested':False,'conda':plan['actions']['FETCH'],'wheels':wheels,'libreoffice':{'filename':lo_archive.name,'sha256':lo_digest}},indent=2))
DIST.mkdir(exist_ok=True)
if tag=='win-64':
 copy(CACHE/tag/'micromamba.exe',app/'micromamba.exe')
 for name in ['install-offline.ps1','start.vbs','start-windows.cmd']:shutil.copy2(PKG/name,app/name)
 installer=work/'installer.nsi';output=DIST/('Donusturucu-'+VERSION+'-Windows-x64-Kurulum.exe')
 installer.write_text(r'''Unicode true
!include "MUI2.nsh"
!include "x64.nsh"
Name "Donusturucu @VERSION@"
OutFile "@OUTPUT@"
InstallDir "$LOCALAPPDATA\Donusturucu"
RequestExecutionLevel user
SetCompressor zlib
ShowInstDetails show
!define MUI_WELCOMEPAGE_TITLE "Donusturucu @VERSION@"
!define MUI_WELCOMEPAGE_TEXT "Cevrimdisi belge, ses ve video donusturucu. Turkce ve Kurmanci arayuz.$\r$\n$\r$\nBu paket Linux uzerinde hazirlandi. Windows uzerinde kurulum ve donusum testi kurulum sirasinda yapilacak. En az 6 GB bos alan gerekir."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Turkish"
Function .onInit
StrCpy $INSTDIR "$LOCALAPPDATA\Donusturucu"
${IfNot} ${RunningX64}
MessageBox MB_ICONSTOP "64 bit Windows gereklidir."
Abort
${EndIf}
FunctionEnd
Section "Donusturucu"
SetOutPath "$INSTDIR"
File /r "@APP@/*"
nsExec::ExecToLog /TIMEOUT=900000 '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\install-offline.ps1"'
Pop $0
StrCmp $0 "0" ready
MessageBox MB_ICONSTOP "Kurulum testi basarisiz. Ayrintilar: $INSTDIR\installation-test.json"
Abort
ready:
CreateDirectory "$SMPROGRAMS\Donusturucu"
CreateShortcut "$SMPROGRAMS\Donusturucu\Donusturucu.lnk" "$INSTDIR\start-windows.cmd"
CreateShortcut "$DESKTOP\Donusturucu.lnk" "$INSTDIR\start-windows.cmd"
WriteUninstaller "$INSTDIR\Kaldir.exe"
WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Donusturucu" "DisplayName" "Donusturucu @VERSION@"
WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Donusturucu" "UninstallString" '"$INSTDIR\Kaldir.exe"'
WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Donusturucu" "DisplayVersion" "@VERSION@"
SectionEnd
Section "Uninstall"
Delete "$DESKTOP\Donusturucu.lnk"
RMDir /r "$SMPROGRAMS\Donusturucu"
DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Donusturucu"
RMDir /r "$INSTDIR"
SectionEnd
'''.replace('@VERSION@',VERSION).replace('@OUTPUT@',str(output)).replace('@APP@',str(app)))
 env=os.environ.copy();env['NSISDIR']=str(CACHE/'nsis/usr/share/nsis')
 cmd([CACHE/'nsis/usr/bin/makensis','-V2',installer],env=env)
else:
 arch='arm64' if tag=='osx-arm64' else 'x86_64';av='15.1.0' if tag=='osx-arm64' else '16.1.0'
 copy(CACHE/tag/'micromamba',app/'micromamba')
 bundle=work/'payload/Applications/Donusturucu.app';executable=bundle/'Contents/MacOS/Donusturucu';executable.parent.mkdir(exist_ok=True)
 shutil.copy2(PKG/'macos-launcher',executable);executable.chmod(0o755)
 with (bundle/'Contents/Info.plist').open('wb') as f:plistlib.dump({'CFBundleName':'Donusturucu','CFBundleDisplayName':'Dönüştürücü','CFBundleExecutable':'Donusturucu','CFBundleIdentifier':'org.local.donusturucu','CFBundlePackageType':'APPL','CFBundleShortVersionString':VERSION,'CFBundleVersion':VERSION,'LSMinimumSystemVersion':'13.0','NSHighResolutionCapable':True},f)
 scripts=work/'scripts';scripts.mkdir(exist_ok=True);post=scripts/'postinstall'
 post.write_text((PKG/'postinstall-macos').read_text().replace('@ARCH@',arch).replace('@PLATFORM@',tag).replace('@AV@',av));post.chmod(0o755)
 product=work/'product';component=product/'Donusturucu.pkg';component.mkdir(parents=True,exist_ok=True)
 def cpio(source,out):
  files=['.']+[str(f.relative_to(source)) for f in sorted(source.rglob('*'))]
  # Do not traverse directory symlinks. pathlib.rglob does not follow them.
  with out.open('wb') as target:
   a=subprocess.Popen(['cpio','--null','-o','--format=odc','--owner=0:0'],cwd=source,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   b=subprocess.Popen(['gzip','-1','-n'],stdin=a.stdout,stdout=target);a.stdout.close();a.stdout=None
   _,error=a.communicate(('\0'.join(files)+'\0').encode());assert a.returncode==0,error
   assert b.wait()==0
 cpio(work/'payload',component/'Payload');cpio(scripts,component/'Scripts')
 cmd([CACHE/'bomutils-0.2/build/bin/mkbom','-u','0','-g','0',work/'payload',component/'Bom'])
 size=sum(f.stat().st_size for f in (work/'payload').rglob('*') if f.is_file());count=sum(1 for f in (work/'payload').rglob('*'))
 (component/'PackageInfo').write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<pkg-info format-version="2" identifier="org.local.donusturucu.{arch}" version="{VERSION}" install-location="/" auth="root" overwrite-permissions="false"><payload installKBytes="{(size+1023)//1024}" numberOfFiles="{count}"/><scripts><postinstall file="postinstall"/></scripts></pkg-info>''')
 (product/'Distribution').write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2"><title>Dönüştürücü {VERSION}</title><options customize="never" require-scripts="false" hostArchitectures="{arch}" rootVolumeOnly="true"/><allowed-os-versions><os-version min="13.0"/></allowed-os-versions><choices-outline><line choice="default"><line choice="app"/></line></choices-outline><choice id="default"/><choice id="app" visible="false"><pkg-ref id="org.local.donusturucu.{arch}"/></choice><pkg-ref id="org.local.donusturucu.{arch}" version="{VERSION}" onConclusion="none">#Donusturucu.pkg</pkg-ref></installer-gui-script>''')
 output=DIST/('Donusturucu-'+VERSION+'-macOS-'+('Apple-Silicon' if tag=='osx-arm64' else 'Intel')+'-Kurulum.pkg')
 cmd([CACHE/'extractors/usr/bin/bsdtar','--format=xar','--options','xar:compression=none','-cf',output,'Distribution','Donusturucu.pkg'],cwd=product)
if tag!='win-64':
 from check_xar import normalize
 normalize(output)
# Read-only integrity validation; this is NOT an execution test on the target OS.
if tag=='win-64':cmd(['7z','t',output],stdout=subprocess.DEVNULL)
else:cmd([CACHE/'extractors/usr/bin/bsdtar','-tf',output],stdout=subprocess.DEVNULL)
h=hashlib.sha256()
with output.open('rb') as f:
 while chunk:=f.read(1024*1024):h.update(chunk)
(output.with_suffix(output.suffix+'.sha256')).write_text(h.hexdigest()+'  '+output.name+'\n')
print('BUILT',output,output.stat().st_size,flush=True)
