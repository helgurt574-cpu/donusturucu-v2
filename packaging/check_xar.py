"""Validate unsigned XAR TOC and trim libarchive's unreferenced final buffer bytes."""
from pathlib import Path
import struct,zlib,hashlib,xml.etree.ElementTree as ET

def normalize(path):
 path=Path(path)
 with path.open('r+b') as f:
  magic,header,version,compressed,uncompressed,algorithm=struct.unpack('>IHHQQI',f.read(28))
  assert magic==0x78617221 and version==1 and algorithm==1
  f.seek(header);toc=f.read(compressed);xml=zlib.decompress(toc);assert len(xml)==uncompressed
  root=ET.fromstring(xml);checksum=root.find('toc/checksum');assert checksum.get('style')=='sha1'
  offset=int(checksum.findtext('offset'));size=int(checksum.findtext('size'));assert size==20
  heap=header+compressed;f.seek(heap+offset);assert f.read(size)==hashlib.sha1(toc).digest()
  end=max([offset+size]+[int(data.findtext('offset'))+int(data.findtext('length')) for data in root.findall('.//data')])
  assert path.stat().st_size>=heap+end
  if path.stat().st_size>heap+end:f.truncate(heap+end)
 return path
if __name__=='__main__':
 import sys
 for path in sys.argv[1:]:normalize(path);print('VALID',path)
