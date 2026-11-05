#!/usr/bin/env python3
"""Build the Windows (.exe, NSIS) and macOS (.pkg) installers on Linux.

Inputs come from a build cache prepared once with internet access (see --help):
conda packages + explicit.txt per platform, speech wheels, FFmpeg, an extracted
LibreOffice, micromamba and the Whisper model. The installers never download:
they build the Python runtime offline on the target and then run donusturucu.selftest.

These installers are assembled, not executed, here: Windows can be partly checked
with Wine; macOS cannot be run on Linux at all.
"""
from pathlib import Path
import argparse,hashlib,os,plistlib,shutil,struct,subprocess,sys

BASE=Path(__file__).resolve().parents[1];PKG=BASE/'packaging'
sys.path.insert(0,str(BASE))
from donusturucu import VERSION

def run(args,**kw):subprocess.run([str(a) for a in args],check=True,**kw)
def link_tree(src,dst):
    """Hard-link a tree into the payload (falls back to copying across filesystems)."""
    if dst.exists():shutil.rmtree(dst)
    def copy(s,d):
        try:os.link(s,d)
        except OSError:shutil.copy2(s,d)
    shutil.copytree(src,dst,symlinks=True,copy_function=copy)

def common_payload(app,cache,platform,ffmpeg,lo,lo_name,micromamba,micromamba_name,prebuilt=None):
    app.mkdir(parents=True,exist_ok=True)
    for name in ['donusturucu']:
        if (app/name).exists():shutil.rmtree(app/name)
        shutil.copytree(BASE/name,app/name,ignore=shutil.ignore_patterns('__pycache__'))
    assets=app/'assets'
    if assets.exists():shutil.rmtree(assets)
    for name in ['fonts','selftest']:shutil.copytree(BASE/'assets'/name,assets/name)
    shutil.copy2(BASE/'assets/donusturucu.svg',assets/'donusturucu.svg')
    shutil.copy2(PKG/'launch_bundle.py',app/'launch.py')
    for name in ['KULLANIM.txt','KULLANIM-ALTYAZI.txt','KULLANIM-KLASOR.txt']:
        if (BASE/name).exists():shutil.copy2(BASE/name,app/name)
    if prebuilt:
        # Ready runtime built with the platform's own micromamba: installing needs no tools and
        # works under any user name (micromamba breaks on non-ASCII profile paths like C:\Users\efrın).
        for stale in ['packages','wheels',micromamba_name]:
            target=app/stale
            if target.is_dir():shutil.rmtree(target)
            elif target.exists():target.unlink()
        link_tree(prebuilt,app/'runtime')
        # Build-only files: debug symbols, C headers, import libraries, docs (NSIS has a 2 GB data limit).
        rt=app/'runtime'
        for pattern in ['**/*.pdb','Library/include','include','libs','Library/share/doc','Library/share/man','Lib/site-packages/pip','Scripts/pip*.exe']:
            for f in list(rt.glob(pattern)):
                if f.is_dir():shutil.rmtree(f)
                else:f.unlink()
        for f in list((rt/'Library/lib').glob('*.lib')):f.unlink()
    else:
        link_tree(cache/'packages'/platform,app/'packages')
        link_tree(cache/'wheels'/platform,app/'wheels')
    tools=app/'tools';tools.mkdir(exist_ok=True)
    for f in ffmpeg.iterdir():
        if f.is_file():shutil.copy2(f,tools/f.name)
    link_tree(ffmpeg/'licenses',app/'licenses/ffmpeg')
    link_tree(cache/'tessdata',tools/'tessdata')
    link_tree(lo,tools/lo_name)
    link_tree(cache/'asr-models/whisper-small',app/'asr-models/whisper-small')
    if not prebuilt:shutil.copy2(micromamba,app/micromamba_name)

def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while chunk:=f.read(1<<20):h.update(chunk)
    return h.hexdigest()

def windows(cache,work,dist):
    app=work/'app'
    common_payload(app,cache,'win-64',cache/'ffmpeg/windows-x64',cache/'lo-win','LibreOffice',cache/'micromamba.exe','micromamba.exe',prebuilt=cache/'win-runtime')
    for name in ['install-offline.ps1','start.vbs','start-windows.cmd']:shutil.copy2(PKG/name,app/name)
    shutil.copy2(cache/'donusturucu.ico',app/'donusturucu.ico')
    output=dist/'Donusturucu-Windows-x64-Kurulum.exe'
    script=work/'installer.nsi'
    script.write_text(r'''Unicode true
!include "MUI2.nsh"
!include "x64.nsh"
Name "Dönüştürücü"
OutFile "@OUTPUT@"
InstallDir "$LOCALAPPDATA\Donusturucu"
RequestExecutionLevel user
SetCompressor lzma
ShowInstDetails show
!define MUI_ICON "@APP@\donusturucu.ico"
!define MUI_UNICON "@APP@\donusturucu.ico"
!define MUI_WELCOMEPAGE_TITLE "Dönüştürücü"
!define MUI_WELCOMEPAGE_TEXT "Çevrimdışı belge, ses, video, OCR, altyazı ve konuşma dönüştürücü.$\r$\nTürkçe ve Kurmancî arayüz.$\r$\n$\r$\nKurulum internet kullanmaz. Sonunda bütün işlevler bu bilgisayarda denenir; bu birkaç dakika sürebilir. En az 6 GB boş alan gerekir."
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "Dönüştürücü'yü aç"
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchApp
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Turkish"
Function LaunchApp
Exec '"$WINDIR\System32\wscript.exe" "$INSTDIR\start.vbs"'
FunctionEnd
Function .onInit
${IfNot} ${RunningX64}
MessageBox MB_ICONSTOP "64 bit Windows 10 veya 11 gereklidir."
Abort
${EndIf}
FunctionEnd
Section "Dönüştürücü"
SetOutPath "$INSTDIR"
File /r "@APP@\*"
DetailPrint "Yerel motorlar kuruluyor ve işlevler deneniyor..."
nsExec::ExecToLog /TIMEOUT=1800000 '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\install-offline.ps1"'
Pop $0
StrCmp $0 "0" ready
DetailPrint "Uyarı: kurulum testi çalıştırılamadı ($0). Uygulama yine de kuruldu."
ready:
CreateDirectory "$SMPROGRAMS\Dönüştürücü"
CreateShortcut "$SMPROGRAMS\Dönüştürücü\Dönüştürücü.lnk" "$WINDIR\System32\wscript.exe" '"$INSTDIR\start.vbs"' "$INSTDIR\donusturucu.ico"
CreateShortcut "$SMPROGRAMS\Dönüştürücü\Kaldır.lnk" "$INSTDIR\Kaldir.exe"
CreateShortcut "$DESKTOP\Dönüştürücü.lnk" "$WINDIR\System32\wscript.exe" '"$INSTDIR\start.vbs"' "$INSTDIR\donusturucu.ico"
WriteUninstaller "$INSTDIR\Kaldir.exe"
WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Donusturucu" "DisplayName" "Dönüştürücü"
WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Donusturucu" "DisplayIcon" "$INSTDIR\donusturucu.ico"
WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Donusturucu" "UninstallString" '"$INSTDIR\Kaldir.exe"'
WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Donusturucu" "DisplayVersion" "@VERSION@"
WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Donusturucu" "Publisher" "Dönüştürücü"
WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Donusturucu" "NoModify" 1
SectionEnd
Section "Uninstall"
Delete "$DESKTOP\Dönüştürücü.lnk"
RMDir /r "$SMPROGRAMS\Dönüştürücü"
DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Donusturucu"
RMDir /r "$INSTDIR"
SectionEnd
'''.replace('@VERSION@',VERSION).replace('@OUTPUT@',str(output)).replace('@APP@',str(app)),encoding='utf-8')
    run(['makensis','-V2','-INPUTCHARSET','UTF8',script])
    return output

def icns(svg,out):
    import gi
    gi.require_version('GdkPixbuf','2.0')
    from gi.repository import GdkPixbuf
    chunks=b''
    for size,kind in [(128,b'ic07'),(256,b'ic08'),(512,b'ic09'),(1024,b'ic10')]:
        ok,data=GdkPixbuf.Pixbuf.new_from_file_at_size(str(svg),size,size).save_to_bufferv('png',[],[])
        chunks+=kind+struct.pack('>I',8+len(data))+data
    out.write_bytes(b'icns'+struct.pack('>I',8+len(chunks))+chunks)

def cpio(source,out):
    # GNU cpio links odc entries by their 18-bit inode numbers; the hard-linked payload made
    # unrelated files collide (a 2 KB icon got a 483 MB body). Every entry is written on its own.
    sys.path.insert(0,str(PKG));import cpio_odc
    cpio_odc.pack(source,out)

def macos(cache,work,dist,platform,mkbom):
    arch='arm64' if platform=='osx-arm64' else 'x86_64'
    payload=work/'payload';bundle=payload/'Applications/Donusturucu.app';app=bundle/'Contents/Resources/app'
    ff='macos-arm64' if arch=='arm64' else 'macos-x64';lo=cache/('lo-mac-'+('aarch64' if arch=='arm64' else 'x86-64'))/'LibreOffice/LibreOffice.app'
    common_payload(app,cache,platform,cache/'ffmpeg'/ff,lo,'LibreOffice.app',cache/('micromamba-'+platform),'micromamba')
    (app/'micromamba').chmod(0o755)
    for tool in ['ffmpeg','ffprobe']:(app/'tools'/tool).chmod(0o755)
    setup=app/'setup-runtime.sh';setup.write_text((PKG/'setup-runtime-macos.sh').read_text(encoding='utf-8').replace('@PLATFORM@',platform),encoding='utf-8');setup.chmod(0o755)
    exe=bundle/'Contents/MacOS/Donusturucu';exe.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PKG/'macos-launcher',exe);exe.chmod(0o755)
    icns(BASE/'assets/donusturucu.svg',bundle/'Contents/Resources/donusturucu.icns')
    with (bundle/'Contents/Info.plist').open('wb') as f:
        plistlib.dump({'CFBundleName':'Donusturucu','CFBundleDisplayName':'Dönüştürücü','CFBundleExecutable':'Donusturucu',
            'CFBundleIdentifier':'org.local.donusturucu','CFBundlePackageType':'APPL','CFBundleShortVersionString':VERSION,'CFBundleVersion':VERSION,
            'CFBundleIconFile':'donusturucu','LSMinimumSystemVersion':'13.0','NSHighResolutionCapable':True,
            'LSArchitecturePriority':[arch],'NSRequiresAquaSystemAppearance':False},f)
    scripts=work/'scripts';scripts.mkdir(exist_ok=True)
    post=scripts/'postinstall';post.write_text((PKG/'postinstall-macos').read_text(encoding='utf-8').replace('@VERSION@',VERSION).replace('@PLATFORM@',platform),encoding='utf-8');post.chmod(0o755)
    product=work/'product';component=product/'Donusturucu.pkg'
    if product.exists():shutil.rmtree(product)
    component.mkdir(parents=True)
    cpio(payload,component/'Payload');cpio(scripts,component/'Scripts')
    run([mkbom,'-u','0','-g','0',payload,component/'Bom'])
    size=sum(f.stat().st_size for f in payload.rglob('*') if f.is_file() and not f.is_symlink());count=sum(1 for _ in payload.rglob('*'))
    ident=f'org.local.donusturucu.{arch}'
    (component/'PackageInfo').write_text(f'<?xml version="1.0" encoding="utf-8"?>\n<pkg-info format-version="2" identifier="{ident}" version="{VERSION}" install-location="/" auth="root" overwrite-permissions="false"><payload installKBytes="{(size+1023)//1024}" numberOfFiles="{count}"/><scripts><postinstall file="./postinstall"/></scripts></pkg-info>',encoding='utf-8')
    (product/'Distribution').write_text(f'<?xml version="1.0" encoding="utf-8"?>\n<installer-gui-script minSpecVersion="2"><title>Dönüştürücü</title><options customize="never" require-scripts="false" hostArchitectures="{arch}" rootVolumeOnly="true"/><allowed-os-versions><os-version min="13.0"/></allowed-os-versions><choices-outline><line choice="default"><line choice="app"/></line></choices-outline><choice id="default"/><choice id="app" visible="false"><pkg-ref id="{ident}"/></choice><pkg-ref id="{ident}" version="{VERSION}" onConclusion="none">#Donusturucu.pkg</pkg-ref></installer-gui-script>',encoding='utf-8')
    name='Apple-Silicon' if arch=='arm64' else 'Intel'
    output=dist/f'Donusturucu-macOS-{name}-Kurulum.pkg'
    if output.exists():output.unlink()
    run(['xar','--compression','none','-cf',output.resolve(),'Distribution','Donusturucu.pkg'],cwd=product)
    return output

def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('platform',choices=['win-64','osx-arm64','osx-64']);p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--dist',type=Path,default=BASE/'dist');p.add_argument('--mkbom',default='mkbom')
    a=p.parse_args();a.dist.mkdir(parents=True,exist_ok=True);work=a.cache/'build'/a.platform;work.mkdir(parents=True,exist_ok=True)
    out=windows(a.cache,work,a.dist) if a.platform=='win-64' else macos(a.cache,work,a.dist,a.platform,a.mkbom)
    out.with_name(out.name+'.sha256').write_text(sha256(out)+'  '+out.name+'\n')
    print('BUILT',out,out.stat().st_size,flush=True)

if __name__=='__main__':main()
