"""Sequential release builds, no native Windows/macOS execution claimed."""
from pathlib import Path
import json,subprocess,hashlib,datetime
b=Path(__file__).resolve().parents[1]
def sources():return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (b/'donusturucu').glob('*.py')}
initial=sources();status=b/'packaging/cross-163-status.json'
def save(stage):status.write_text(json.dumps({'stage':stage,'sources':initial,'updated':datetime.datetime.now().astimezone().isoformat()},indent=2)+'\n')
try:
 for tag,label in [('osx-64','mac-intel'),('win-64','windows')]:
  assert sources()==initial,'Sources changed; stop concurrent release build'
  save('building '+tag)
  with (b/f'packaging/build-{label}-1.6.3.log').open('w') as log:subprocess.run(['/usr/bin/python3',str(b/'packaging/build_cross_installers.py'),tag],cwd=b,stdout=log,stderr=subprocess.STDOUT,check=True)
 assert sources()==initial
 save('verifying installers')
 with (b/'packaging/verify-cross-1.6.3.log').open('w') as log:subprocess.run(['/usr/bin/python3',str(b/'packaging/verify_cross_163.py')],cwd=b,stdout=log,stderr=subprocess.STDOUT,check=True)
 assert sources()==initial
 save('verified; native execution unavailable')
except Exception as e:
 save('FAILED: '+str(e));raise
