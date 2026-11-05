"""Plain odc cpio reader/writer that never links entries by inode (the old archive's short
inode numbers collide)."""
import gzip,os,stat,sys
from pathlib import Path
def extract(archive,dest):
    dest=Path(dest);f=gzip.open(archive,'rb');n=0
    while True:
        h=f.read(76)
        if len(h)<76 or h[:6]!=b'070707':raise SystemExit('bad header')
        mode=int(h[18:24],8);mtime=int(h[48:59],8);namesize=int(h[59:65],8);size=int(h[65:76],8)
        name=f.read(namesize)[:-1].decode('utf-8','surrogateescape')
        if name=='TRAILER!!!':break
        data=f.read(size);p=dest/name.lstrip('./') if name not in ('.','./') else dest
        assert dest.resolve() in [p.resolve(),*p.resolve().parents] or p==dest
        kind=stat.S_IFMT(mode)
        if kind==stat.S_IFDIR:p.mkdir(parents=True,exist_ok=True);os.chmod(p,(mode&0o7777)|0o700)
        elif kind==stat.S_IFLNK:p.parent.mkdir(parents=True,exist_ok=True);os.symlink(data.decode('utf-8','surrogateescape'),p)
        elif kind==stat.S_IFREG:
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);os.chmod(p,mode&0o7777);os.utime(p,(mtime,mtime))
        n+=1
    print('extracted',n)
def pack(src,archive):
    src=Path(src);names=['.']+sorted(str(p.relative_to(src)) for p in src.rglob('*'))
    with open(archive,'wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',compresslevel=6,mtime=0) as out:
        for ino,name in enumerate(names,1):
            p=src if name=='.' else src/name;st=os.lstat(p);kind=stat.S_IFMT(st.st_mode)
            data=os.readlink(p).encode('utf-8','surrogateescape') if kind==stat.S_IFLNK else p.read_bytes() if kind==stat.S_IFREG else b''
            nm=name.encode('utf-8','surrogateescape')+b'\0'
            hdr=b'070707'+b''.join(f'{v:0{w}o}'.encode() for v,w in [(0,6),(ino%0o777777,6),(st.st_mode,6),(0,6),(0,6),(1,6),(0,6),(int(st.st_mtime),11),(len(nm),6),(len(data),11)])
            out.write(hdr+nm+data)
        nm=b'TRAILER!!!\0';out.write(b'070707'+b''.join(f'{v:0{w}o}'.encode() for v,w in [(0,6),(0,6),(0,6),(0,6),(0,6),(1,6),(0,6),(0,11),(len(nm),6),(0,11)])+nm)
    print('packed',len(names))
if __name__=='__main__':{'extract':extract,'pack':pack}[sys.argv[1]](*sys.argv[2:])
