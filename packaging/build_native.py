#!/usr/bin/env python3
"""Build on the target OS. All conversion tools are copied into the package.
No download/install is attempted. Building fails if a local tool is missing or
the produced application fails actual offline conversion tests.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
from donusturucu import runtime

p=argparse.ArgumentParser()
p.add_argument('--tools-dir',type=Path,help='Prepared offline folder containing ffmpeg, ffprobe, pandoc and a complete LibreOffice directory/app')
p.add_argument('--work-dir',type=Path,default=BASE/'build/native')
args=p.parse_args()
if args.tools_dir:os.environ['DONUSTURUCU_TOOLS']=str(args.tools_dir.resolve())
try:import PyInstaller
except ImportError:raise SystemExit('Build environment needs PyInstaller. Use the local requirements/wheelhouse before running this script.')
for name in ['libreoffice','ffmpeg','ffprobe','pandoc','tesseract','pdftoppm']:
    if not runtime.available(name):raise SystemExit('Missing local backend: '+name)
import pypdf
from donusturucu.speech import resources
model,_=resources()
import faster_whisper,ctranslate2,numpy
work=args.work_dir.resolve();work.mkdir(parents=True,exist_ok=True)
stage=work/'stage';stage.mkdir(exist_ok=True)
tools=stage/'tools';tools.mkdir(exist_ok=True)
binaries=[]
for name in ['ffmpeg','ffprobe','pandoc','tesseract','pdftoppm']:
    source=Path(runtime.tool_path(name)).resolve()
    if sys.platform.startswith('linux') and name=='pdftoppm' and Path('/usr/bin/pdftoppm').exists():source=Path('/usr/bin/pdftoppm')
    if name=='pandoc' and sys.platform.startswith('linux') and (runtime.ROOT/'vendor/runtime/usr/bin/pandoc').exists():source=runtime.ROOT/'vendor/runtime/usr/bin/pandoc'
    dest=tools/(name+('.exe' if sys.platform=='win32' else ''))
    shutil.copy2(source,dest);binaries.append((dest,'tools'))
    # Windows tool distributions can require sibling DLLs. Copy those too.
    if sys.platform=='win32':
        for dll in source.parent.glob('*.dll'):shutil.copy2(dll,tools/dll.name)
lo=Path(runtime.tool_path('libreoffice')).resolve()
if sys.platform=='darwin':
    source=next((parent for parent in lo.parents if parent.suffix=='.app'),None)
    if source is None:raise SystemExit('A complete LibreOffice.app must be available.')
    dest=tools/'LibreOffice.app'
else:
    source=lo.parent.parent;dest=tools/'LibreOffice'
    if not (source/'program').is_dir():raise SystemExit('Cannot identify the complete LibreOffice installation from '+str(lo))
if dest.exists():shutil.rmtree(dest)
shutil.copytree(source,dest,symlinks=True)
# Debian Pandoc uses an external data directory; preserve it where applicable.
if sys.platform.startswith('linux'):
    pandoc_data=runtime.ROOT/'vendor/runtime/usr/share/pandoc'
    if not pandoc_data.exists():pandoc_data=Path('/usr/share/pandoc')
    if pandoc_data.exists():shutil.copytree(pandoc_data,tools/'pandoc-data',dirs_exist_ok=True)
# OCR models are data files: include all advertised languages, never download.
data_roots=[Path(runtime.process_env().get('TESSDATA_PREFIX','/missing')),Path(runtime.tool_path('tesseract')).parent/'tessdata',Path('/usr/share/tesseract-ocr/5/tessdata'),Path('/opt/homebrew/share/tessdata'),Path('/usr/local/share/tessdata')]
if args.tools_dir:data_roots.insert(0,args.tools_dir/'tessdata')
data_source=next((d for d in data_roots if all((d/(lang+'.traineddata')).exists() for lang in ['eng','tur','kmr','ara','fas'])),None)
if data_source is None:raise SystemExit('OCR requires eng, tur, kmr, ara and fas traineddata files in the local tessdata directory.')
shutil.copytree(data_source,tools/'tessdata',dirs_exist_ok=True)
# Preserve copyright notices for copied backends when supplied by a vendor.
if args.tools_dir and (args.tools_dir/'licenses').exists():shutil.copytree(args.tools_dir/'licenses',tools/'licenses',dirs_exist_ok=True)
cmd=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir','--name','Donusturucu','--paths',str(BASE),'--paths',str(BASE/'vendor/python'),'--hidden-import','pypdf','--collect-all','pypdf','--distpath',str(work/'dist'),'--workpath',str(work/'pyinstaller'),'--specpath',str(work)]
cmd += ['--add-data',str(dest)+os.pathsep+'tools/'+dest.name,'--add-data',str(BASE/'KULLANIM.txt')+os.pathsep+'.']
cmd += ['--add-data',str(tools/'tessdata')+os.pathsep+'tools/tessdata','--add-data',str(BASE/'packaging/ocr-smoke.png')+os.pathsep+'.']
for language in ['ara','fas']:cmd += ['--add-data',str(BASE/('packaging/ocr-smoke-'+language+'.png'))+os.pathsep+'.']
if (tools/'pandoc-data').exists():cmd += ['--add-data',str(tools/'pandoc-data')+os.pathsep+'tools/pandoc-data']
if (tools/'licenses').exists():cmd += ['--add-data',str(tools/'licenses')+os.pathsep+'tools/licenses']
if sys.platform=='win32':
    for dll in tools.glob('*.dll'):binaries.append((dll,'tools'))
for binary,target in binaries:cmd += ['--add-binary',str(binary)+os.pathsep+target]
if sys.platform=='darwin':cmd += ['--osx-bundle-identifier','org.local.Donusturucu']
for module in ['faster_whisper','ctranslate2','av','tokenizers','onnxruntime','huggingface_hub','numpy']:
    cmd += ['--collect-all',module]
cmd += ['--add-data',str(model)+os.pathsep+'asr-models/whisper-small']
cmd += ['--add-data',str(BASE/'assets/speech/english-test.mp3')+os.pathsep+'speech-test']
cmd += [str(BASE/'packaging/entry.py')]
subprocess.run(cmd,check=True)
if sys.platform=='darwin':
    app=work/'dist/Donusturucu.app';exe=app/'Contents/MacOS/Donusturucu'
else:
    app=work/'dist/Donusturucu';exe=app/('Donusturucu.exe' if sys.platform=='win32' else 'Donusturucu')
report=work/'native-self-test.json'
# Remove host PATH tool entries so the smoke test must use the bundled engines.
env=os.environ.copy();env.pop('DONUSTURUCU_TOOLS',None)
subprocess.run([str(exe),'--self-test',str(report)],check=True,env=env,timeout=180)
result=json.loads(report.read_text(encoding='utf-8'))
if not result['passed']:raise SystemExit('Native conversion test failed: '+str(result))
for name,path in result['tool_paths'].items():
    if not path or not Path(path).resolve().is_relative_to(Path(result['bundle_root']).resolve()):
        raise SystemExit('Self-test used an unbundled backend: '+name+' '+str(path))
dist=BASE/'dist';dist.mkdir(exist_ok=True)
tag='windows' if sys.platform=='win32' else 'macos' if sys.platform=='darwin' else 'linux'
name='donusturucu-1.6.1-'+tag
if sys.platform=='darwin':
    output=dist/(name+'.dmg')
    subprocess.run(['hdiutil','create','-ov','-volname','Donusturucu','-srcfolder',str(app),str(output)],check=True)
else:output=Path(shutil.make_archive(str(dist/name),'zip',root_dir=app.parent,base_dir=app.name))
shutil.copy2(report,dist/(name+'-test.json'))
print(output)
