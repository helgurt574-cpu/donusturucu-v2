from pathlib import Path
import os,sys,json
from donusturucu import core,runtime
BASE=Path(__file__).resolve().parents[1];ROOT=BASE/'qa-1.6.2'
child="""import socket,errno,json,sys
from pathlib import Path
status={}
for line in Path('/proc/self/status').read_text().splitlines():
 if line.startswith(('NoNewPrivs:','Seccomp:','CapEff:')):
  key,value=line.split(':',1);status[key]=value.strip()
for name,family in [('ipv4',socket.AF_INET),('ipv6',socket.AF_INET6)]:
 try:s=socket.socket(family,socket.SOCK_STREAM)
 except PermissionError as exc:status[name]={'blocked':True,'errno':exc.errno}
 else:s.close();raise AssertionError(name+' socket unexpectedly allowed')
s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.close();status['unix_socket_allowed']=True
Path(sys.argv[1]).write_text(json.dumps(status,indent=2))
"""
proof={'app_root':str(runtime.ROOT),'parent_profile':Path('/proc/self/attr/current').read_text().strip(),'isolation':runtime.isolation_status(),'runs':[]}
for rep in range(1,4):
 p=ROOT/('network-proof-'+str(rep)+'.json');core.Runner().run([sys.executable,'-c',child,str(p)]);j=json.loads(p.read_text());assert j['NoNewPrivs']=='1' and j['Seccomp']=='2';proof['runs'].append(j)
(ROOT/'normal-session-proof.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof,indent=2))
