#!/usr/bin/env python3
from pathlib import Path
import argparse
import os, shutil, subprocess
parser=argparse.ArgumentParser();parser.add_argument('--with-speech',action='store_true');parser.add_argument('--arch',choices=['amd64','arm64'],default='amd64');parser.add_argument('--speech-wheels',type=Path);args=parser.parse_args()
base=Path(__file__).resolve().parent
root=base/('build/package-arm64' if args.arch=='arm64' else 'build/package')
if root.exists():shutil.rmtree(root)
(root/'DEBIAN').mkdir(parents=True)
app=root/'usr/share/donusturucu';app.mkdir(parents=True)
shutil.copytree(base/'donusturucu',app/'donusturucu',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy2(base/'KULLANIM.txt',app/'KULLANIM.txt')
# Ship the pure Python PDF reader on every architecture, and the tested local
# amd64 document/OCR tools instead of depending on the source checkout PATH.
shutil.copytree(base/'vendor/python',app/'vendor/python',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copytree(base/'vendor/licenses',app/'vendor/licenses')
if args.arch=='amd64':
    for name in ['bin','runtime','ocr']:
        shutil.copytree(base/'vendor'/name,app/'vendor'/name,symlinks=True,ignore=shutil.ignore_patterns('__pycache__'))

if args.with_speech:
    import platform,sys,zipfile,hashlib,json
    if args.arch=='arm64':
        if not args.speech_wheels:raise SystemExit('ARM64 speech requires --speech-wheels with CPython 3.12 aarch64 wheels')
        wheels=sorted(args.speech_wheels.glob('*.whl'))
        if not wheels:raise SystemExit('No speech wheels found')
        site=app/'asr-env/lib/python3.12/site-packages';site.mkdir(parents=True)
        manifest=[]
        for wheel in wheels:
            if not (wheel.name.endswith('-any.whl') or 'aarch64' in wheel.name):raise SystemExit('Wrong wheel architecture: '+wheel.name)
            with zipfile.ZipFile(wheel) as archive:
                if archive.testzip():raise SystemExit('Corrupt wheel: '+wheel.name)
                for item in archive.infolist():
                    name=Path(item.filename)
                    if name.is_absolute() or '..' in name.parts:raise SystemExit('Unsafe wheel path')
                    if '.data' in name.parts[0]:raise SystemExit('Unsupported wheel .data layout: '+wheel.name)
                archive.extractall(site)
            manifest.append({'file':wheel.name,'sha256':hashlib.sha256(wheel.read_bytes()).hexdigest()})
        shutil.copytree(base/'asr-models/whisper-small',app/'asr-models/whisper-small')
        (app/'arm64-speech-manifest.json').write_text(json.dumps(manifest,indent=2))
    else:
        if platform.machine()!='x86_64' or sys.version_info[:2]!=(3,12):raise SystemExit('Speech package requires Ubuntu amd64 / Python 3.12')
        from donusturucu.speech import resources
        model,command=resources()
        subprocess.run([command[0],'-c','import faster_whisper,ctranslate2,numpy'],check=True)
        shutil.copytree(model,app/'asr-models/whisper-small')
        shutil.copytree(base/'asr-env',app/'asr-env',symlinks=True,ignore=shutil.ignore_patterns('__pycache__','pip','pip-*','bin'))
    (app/'asr-env/bin').mkdir()
    (app/'asr-env/bin/python').symlink_to('/usr/bin/python3.12')
    (app/'asr-env/pyvenv.cfg').write_text('home = /usr/bin\ninclude-system-site-packages = false\nversion = 3.12.3\n')

for report in base.glob('TEST-SONUCLARI-*.txt'):shutil.copy2(report,app/report.name)
(root/'usr/bin').mkdir(parents=True)
launcher=root/'usr/bin/donusturucu'
launcher.write_text('#!/bin/sh\ncd /usr/share/donusturucu\nexec /usr/bin/python3 -m donusturucu.app "$@"\n')
launcher.chmod(0o755)
for target,source in [('usr/share/applications/donusturucu.desktop','assets/donusturucu.desktop'),('usr/share/icons/hicolor/scalable/apps/donusturucu.svg','assets/donusturucu.svg')]:
 dest=root/target;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(base/source,dest)
control='''Package: donusturucu
Version: 1.6.7
Section: utils
Priority: optional
Architecture: all
Maintainer: Local Applications <local@localhost>
Depends: python3 (>= 3.10), python3-gi, python3-cairo, python3-tk, gir1.2-gtk-3.0, ffmpeg, libreoffice-writer, libreoffice-calc, libreoffice-impress, pandoc (>= 2.19), poppler-utils, python3-pypdf, tesseract-ocr, tesseract-ocr-eng, tesseract-ocr-tur, tesseract-ocr-kmr, tesseract-ocr-ara, tesseract-ocr-fas, fonts-dejavu-core, file, bubblewrap
Description: Offline document, audio and video converter
 Turkish and Kurmanji interface. Detects input types and offers compatible
 conversion formats using local tools with network-isolated subprocesses.
'''
if args.with_speech:control=control.replace('Architecture: all','Architecture: '+args.arch).replace('python3 (>= 3.10)','python3 (>= 3.12), python3 (<< 3.13)')
control=control.replace(', python3-pypdf','')
if args.arch=='arm64':
    control=control.replace('fonts-dejavu-core, file','fonts-dejavu-core, file, libseccomp2')
if args.arch=='amd64':
    for dependency in ['pandoc (>= 2.19)','tesseract-ocr','tesseract-ocr-eng','tesseract-ocr-tur','tesseract-ocr-kmr','tesseract-ocr-ara','tesseract-ocr-fas','bubblewrap']:
        control=control.replace(', '+dependency+',',',').replace(', '+dependency+'\n','\n')
    control=control.replace('fonts-dejavu-core, file','fonts-dejavu-core, file, libtesseract5, liblept5, liblua5.4-0, libyaml-0-2, libgmp10, libffi8, libseccomp2')
control=control.replace('with network-isolated subprocesses.','with locally bundled document and OCR components.')
(root/'DEBIAN/control').write_text(control)
dist=base/'dist';dist.mkdir(exist_ok=True)
subprocess.run(['dpkg-deb','--root-owner-group','--build',str(root),str(dist/('donusturucu_1.6.7_'+args.arch+'.deb' if args.with_speech else 'donusturucu_1.6.7_all.deb'))],check=True)
print(dist/('donusturucu_1.6.7_'+args.arch+'.deb' if args.with_speech else 'donusturucu_1.6.7_all.deb'))
