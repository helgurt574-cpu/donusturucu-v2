#!/usr/bin/env python3
"""Lay out downloaded Android dependencies the way build_apk.py expects.

    python3 android/prepare_inputs.py --downloads DIR --tessdata DIR

DIR holds the artifacts fetched once at build time (all from public repositories):
pdfbox-android.aar, bcprov/bcpkix/bcutil.jar, kotlin.jar, tesseract.aar
(Tesseract4Android 4.8.0), sherpa.aar (sherpa-onnx 2.0.1), ffmpeg.aar and
ytdl-library.aar (youtubedl-android 0.18.1) and whisper-small.tar.bz2 (sherpa-onnx model).
"""
from pathlib import Path
import argparse,os,shutil,tarfile,zipfile

ROOT=Path(__file__).resolve().parent
ABIS=['arm64-v8a','armeabi-v7a','x86_64']

def classes(aar,dest):
    with zipfile.ZipFile(aar) as z:dest.write_bytes(z.read('classes.jar'))

def jni(aar,abi,dest):
    with zipfile.ZipFile(aar) as z:
        for name in z.namelist():
            if name.startswith(f'jni/{abi}/') and name.endswith('.so'):
                (dest/Path(name).name).write_bytes(z.read(name))

def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--downloads',type=Path,required=True);p.add_argument('--tessdata',type=Path,required=True)
    a=p.parse_args();d=a.downloads
    cache=ROOT/'cache';cache.mkdir(exist_ok=True)
    classes(d/'pdfbox-android.aar',cache/'pdfbox.jar');classes(d/'tesseract.aar',cache/'tesseract.jar');classes(d/'sherpa.aar',cache/'sherpa.jar')
    for name in ['bcprov.jar','bcpkix.jar','bcutil.jar','kotlin.jar']:shutil.copy2(d/name,cache/name)
    for abi in ABIS:
        lib=ROOT/'native/lib'/abi
        if lib.exists():shutil.rmtree(lib)
        lib.mkdir(parents=True)
        for aar in ['ffmpeg.aar','tesseract.aar','sherpa.aar']:jni(d/aar,abi,lib)
        with zipfile.ZipFile(d/'ytdl-library.aar') as z:(cache/f'python-{abi}.zip').write_bytes(z.read(f'jni/{abi}/libpython.zip.so'))
    assets=ROOT/'assets'
    for sub in ['com','ocr','speech']:
        if (assets/sub).exists():shutil.rmtree(assets/sub)
    with zipfile.ZipFile(d/'pdfbox-android.aar') as z:
        for name in z.namelist():
            if name.startswith('assets/') and not name.endswith('/'):
                target=assets/name[len('assets/'):];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))
    tess=assets/'ocr/tessdata';tess.mkdir(parents=True)
    for lang in ['eng','tur','kmr','ara','fas']:shutil.copy2(a.tessdata/f'{lang}.traineddata',tess)
    speech=assets/'speech';speech.mkdir(parents=True)
    wanted={'small-encoder.int8.onnx','small-decoder.int8.onnx','small-tokens.txt'}
    with tarfile.open(d/'whisper-small.tar.bz2') as t:
        for m in t:
            if Path(m.name).name in wanted and m.isfile():(speech/Path(m.name).name).write_bytes(t.extractfile(m).read())
    missing=wanted-{f.name for f in speech.iterdir()}
    if missing:raise SystemExit(f'model files missing: {missing}')
    print('READY',{abi:len(list((ROOT/'native/lib'/abi).iterdir())) for abi in ABIS},flush=True)

if __name__=='__main__':main()
