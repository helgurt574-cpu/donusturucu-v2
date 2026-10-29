from pathlib import Path
import subprocess,tarfile,hashlib,json
b=Path(__file__).resolve().parents[1];out=b/'qa-user-video-20261028-2';reports={}
for abi in ['amd64','arm64']:
 p=b/f'dist/donusturucu_1.6.7_{abi}.deb';sources={};native=0
 proc=subprocess.Popen(['dpkg-deb','--fsys-tarfile',str(p)],stdout=subprocess.PIPE)
 with tarfile.open(fileobj=proc.stdout,mode='r|') as archive:
  for m in archive:
   assert not any(x in m.name for x in ['release.p12','signing/password','private-key'])
   if not m.isfile():continue
   if '/donusturucu/donusturucu/' in m.name and m.name.endswith('.py'):
    rel=m.name.split('/donusturucu/donusturucu/')[1];data=archive.extractfile(m).read();assert data==(b/'donusturucu'/rel).read_bytes();sources[rel]=hashlib.sha256(data).hexdigest()
   elif '/site-packages/' in m.name:
    head=archive.extractfile(m).read(20)
    if head[:4]==b'\x7fELF':assert int.from_bytes(head[18:20],'little')==({'amd64':62,'arm64':183}[abi]),m.name;native+=1
 assert proc.wait()==0 and len(sources)==15
 control=subprocess.check_output(['dpkg-deb','-f',str(p)],text=True);assert 'Version: 1.6.7' in control and f'Architecture: {abi}' in control and 'libseccomp2' in control
 sha=hashlib.sha256(p.read_bytes()).hexdigest();Path(str(p)+'.sha256').write_text(sha+'  '+p.name+'\n');reports[abi]={'path':str(p),'sha256':sha,'sources':sources,'native_elfs':native,'physical_arm_tested':False if abi=='arm64' else None}
 old=b/f'dist/kur-1.6.6-{abi}.sh';script=old.read_text().replace('1.6.6','1.6.7');new=b/f'dist/kur-1.6.7-{abi}.sh';new.write_text(script);new.chmod(0o755);subprocess.run(['bash','-n',str(new)],check=True)
(out/'linux-package-verification.json').write_text(json.dumps(reports,indent=2)+'\n');print('Linux packages verified',flush=True)
