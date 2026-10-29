"""Prepare a self-contained FFmpeg (ffmpeg + ffprobe) for a desktop package.

Run once while building a package (needs internet); the finished app never downloads.
Every archive is checked against the checksum its publisher posts next to it.

  python3 packaging/fetch_ffmpeg.py --platform linux-x64   --dest build/ffmpeg-linux-x64
  python3 packaging/fetch_ffmpeg.py --platform windows-x64 --dest tools
  python3 packaging/fetch_ffmpeg.py --platform macos-arm64 --dest tools

The Linux deb puts the result in /usr/share/donusturucu/vendor/tools; Windows/macOS
pass the folder to packaging/build_native.py --tools-dir. Android ships its own
FFmpeg inside the APK (android/native) and is not handled here.
"""
from pathlib import Path
import argparse,hashlib,io,shutil,sys,tarfile,tempfile,urllib.request,zipfile

BTBN='https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/'
# Static GPL builds that include libass (burned-in subtitles), libx264 and libmp3lame.
SOURCES={
 'linux-x64':{'kind':'btbn','archive':'ffmpeg-n9.0-latest-linux64-gpl-9.0.tar.xz'},
 'linux-arm64':{'kind':'btbn','archive':'ffmpeg-n9.0-latest-linuxarm64-gpl-9.0.tar.xz'},
 'windows-x64':{'kind':'btbn','archive':'ffmpeg-n9.0-latest-win64-gpl-9.0.zip'},
 'macos-arm64':{'kind':'riedl','base':'https://ffmpeg.martin-riedl.de/download/macos/arm64/1789931890_9.0.2/'},
 'macos-x64':{'kind':'riedl','base':'https://ffmpeg.martin-riedl.de/download/macos/amd64/1789931006_9.0.2/'},
}

def fetch(url):
    request=urllib.request.Request(url,headers={'User-Agent':'donusturucu-packaging'})
    with urllib.request.urlopen(request,timeout=120) as response:return response.read()

def verified(url,expected):
    data=fetch(url);digest=hashlib.sha256(data).hexdigest()
    if digest!=expected.lower():raise SystemExit(f'Checksum mismatch for {url}: {digest} != {expected}')
    return data

def checksum(listing,name):
    for line in listing.splitlines():
        parts=line.split()
        if len(parts)==2 and parts[1].lstrip('*')==name:return parts[0]
    raise SystemExit('No published checksum for '+name)

def extract(data,name,members,dest):
    found={}
    if name.endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for info in archive.infolist():
                base=Path(info.filename).name
                if base in members and not info.is_dir():found[base]=archive.read(info)
    else:
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:*') as archive:
            for info in archive.getmembers():
                base=Path(info.name).name
                if base in members and info.isfile():found[base]=archive.extractfile(info).read()
    missing=set(members)-set(found)
    if missing:raise SystemExit(f'{name} does not contain {sorted(missing)}')
    for base,content in found.items():
        target=dest/base;target.write_bytes(content);target.chmod(0o755)
    return found

def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--platform',required=True,choices=sorted(SOURCES));parser.add_argument('--dest',required=True,type=Path)
    args=parser.parse_args();source=SOURCES[args.platform];args.dest.mkdir(parents=True,exist_ok=True)
    exe='.exe' if args.platform.startswith('windows') else ''
    if source['kind']=='btbn':
        name=source['archive'];listing=fetch(BTBN+'checksums.sha256').decode()
        data=verified(BTBN+name,checksum(listing,name))
        extract(data,name,['ffmpeg'+exe,'ffprobe'+exe],args.dest)
        license_text=None
        with tempfile.TemporaryDirectory() as tmp:
            try:extract(data,name,['LICENSE.txt'],Path(tmp));license_text=(Path(tmp)/'LICENSE.txt').read_bytes()
            except SystemExit:pass
        origin=BTBN+name
    else:
        for tool in ('ffmpeg','ffprobe'):
            url=source['base']+tool+'.zip'
            data=verified(url,checksum(fetch(url+'.sha256').decode(),tool+'.zip'))
            extract(data,tool+'.zip',[tool],args.dest)
        license_text=None;origin=source['base']
    licenses=args.dest/'licenses'/'ffmpeg';licenses.mkdir(parents=True,exist_ok=True)
    if license_text:(licenses/'LICENSE.txt').write_bytes(license_text)
    (licenses/'SOURCE.txt').write_text(f'FFmpeg static GPL build for {args.platform}\nDownloaded from: {origin}\nFFmpeg source: https://github.com/FFmpeg/FFmpeg\n',encoding='utf-8')
    print('FFmpeg ready in',args.dest.resolve())

if __name__=='__main__':main()
