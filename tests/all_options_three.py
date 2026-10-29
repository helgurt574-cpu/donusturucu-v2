"""Three-repeat release audit executed from the normal desktop user manager."""
from pathlib import Path
import os,sys,json,subprocess,time,fcntl
BASE=Path(__file__).resolve().parents[1];OUT=Path(os.environ.get('DONUSTURUCU_AUDIT_OUT',str(BASE/'qa-1.6.2')));OUT.mkdir(exist_ok=True)
lock=(OUT/'audit.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);lock.write(str(os.getpid()));lock.flush()
APP=Path(os.environ['DONUSTURUCU_TEST_APP_ROOT']);sys.path.insert(0,str(APP));from donusturucu import core,runtime
assert Path(core.__file__).resolve().is_relative_to(APP.resolve()),core.__file__
report={'pid':os.getpid(),'started':time.time(),'app_root':str(APP),'isolation':runtime.isolation_status(),'required_repeats':3,'phases':[]}
def save():
 pending=OUT/'audit.pending.json';pending.write_text(json.dumps(report,ensure_ascii=False,indent=2));pending.replace(OUT/'audit.json')
def phase(name,args,cwd=BASE,extra=None):
 env=os.environ.copy();env.update(extra or {});log=OUT/(name+'.log');row={'name':name,'started':time.time(),'log':str(log),'status':'running'};report['phases'].append(row);save()
 with log.open('w') as stream:
  p=subprocess.run(args,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT)
 row.update(status='pass' if p.returncode==0 else 'fail',exit_code=p.returncode,finished=time.time());save()
phase('supplement', ['/usr/bin/python3',str(BASE/'tests/options_supplement_three.py')])
phase('all-format-pairs',['/usr/bin/python3',str(BASE/'tests/full_matrix.py'),str(OUT/'matrix')],extra={'DONUSTURUCU_TEST_REPEATS':'3'})
phase('all-ui-actions',['xvfb-run','-a','/usr/bin/python3',str(BASE/'tests/extras_all_actions_three.py')])
phase('media-operations',['/usr/bin/python3',str(BASE/'tests/operations_stress.py')],extra={'DONUSTURUCU_OPERATIONS_RESULTS':str(OUT/'operations')})
for rep in range(1,4):
 phase('regression-'+str(rep),['xvfb-run','-a','/usr/bin/python3','-m','unittest','discover','-s',str(BASE/'tests'),'-p','test_*.py','-v'],cwd=Path('/tmp'))
 phase('gtk-ui-'+str(rep),['xvfb-run','-a','/usr/bin/python3',str(BASE/'tests/gui_smoke.py')])
 phase('extras-ui-'+str(rep),['xvfb-run','-a','/usr/bin/python3',str(BASE/'tests/extras_simple_ui.py')])
report.update(finished=time.time(),failures=sum(row['status']!='pass' for row in report['phases']));save();sys.exit(bool(report['failures']))
