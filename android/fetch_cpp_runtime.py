from pathlib import Path
import io,urllib.request,zipfile,concurrent.futures
class Remote(io.RawIOBase):
 def __init__(self,url,size):self.url=url;self.size=size;self.pos=0
 def seekable(self):return True
 def readable(self):return True
 def tell(self):return self.pos
 def seek(self,offset,whence=0):self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset;return self.pos
 def read(self,size=-1):
  if size<0:size=self.size-self.pos
  if not size:return b''
  req=urllib.request.Request(self.url,headers={'Range':f'bytes={self.pos}-{min(self.pos+size,self.size)-1}'})
  with urllib.request.urlopen(req,timeout=45) as r:
   if r.status!=206:raise RuntimeError('Range response required')
   b=r.read()
  self.pos+=len(b);return b

def fetch(pair):
 abi,size=pair;url='https://raw.githubusercontent.com/yausername/youtubedl-android/master/library/src/main/jniLibs/'+abi+'/libpython.zip.so'
 with zipfile.ZipFile(Remote(url,size)) as z:
  matches=[n for n in z.namelist() if 'libc++_shared' in n];print(abi,matches,flush=True)
  for name in matches:
   out=Path(__file__).resolve().parent/'native/lib'/abi/'libc++_shared.so';out.write_bytes(z.read(name));print('SAVED',out,out.stat().st_size,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(fetch,[('arm64-v8a',14305904),('x86_64',14302766)]))
