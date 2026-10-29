"""Fail the audit unless each planned finite option has three successful runs."""
from pathlib import Path
import os,sys,json,collections
BASE=Path(__file__).resolve().parents[1];ROOT=Path(os.environ.get('DONUSTURUCU_AUDIT_OUT',str(BASE/'qa-1.6.2')));sys.path.insert(0,os.environ.get('DONUSTURUCU_TEST_APP_ROOT',str(BASE)))
from donusturucu import core
matrix=json.loads((ROOT/'matrix/report.json').read_text());supp=json.loads((ROOT/'supplement/report.json').read_text());ui=json.loads((ROOT/'ui-all-actions/report.json').read_text());ops=json.loads((ROOT/'operations/report.json').read_text());audit=json.loads((ROOT/'audit.json').read_text())
resolutions=json.loads((ROOT/'resolved-phases.json').read_text()) if (ROOT/'resolved-phases.json').exists() else {}
errors=[];coverage={}
pairs=collections.defaultdict(set)
for row in matrix['cases']:
 if row['status']!='pass':errors.append({'category':'matrix','row':row});continue
 if row.get('repetition',0)>0:pairs[(row['group'],Path(row['source']).suffix,row['target'])].add(row['repetition'])
for group in ['document','spreadsheet','presentation','audio','video']:
 for source in (ROOT/'matrix/sources'/group).iterdir():
  if not source.is_file():continue
  for target in core.targets(core.detect(source)):
   key=(group,source.suffix,target);coverage['conversion:'+':'.join(key)]=len(pairs[key])
for category,rows,keys in [('settings',supp['rows'],['option']),('ui',ui['rows'],['kind','action'])]:
 options=collections.defaultdict(set)
 for row in rows:
  if not row['pass']:errors.append({'category':category,'row':row})
  else:options[tuple(row[k] for k in keys)].add(row['repeat'])
 for key,reps in options.items():coverage[category+':'+':'.join(key)]=len(reps)
options=collections.Counter((row['source'],row['action']) for row in ops['rows'] if row['status']=='pass')
for (source,action),count in options.items():coverage['media:'+Path(source).name+':'+action]=count
errors.extend({'category':'coverage','option':key,'successful_repeats':count} for key,count in coverage.items() if count<3)
errors.extend({'category':'phase','row':row} for row in audit['phases'] if row['status']!='pass' and resolutions.get(row['name'],{}).get('status')!='pass')
if ops['failures']:errors.append({'category':'operations','failures':ops['failures']})
report={'required_successful_repeats':3,'covered_options':len(coverage),'minimum_successful_repeats':min(coverage.values()),'conversion_cases':len(matrix['cases']),'supplement_cases':supp['cases'],'gui_action_cases':ui['cases'],'media_operation_cases':ops['cases'],'failures':len(errors),'resolved_harness_phases':resolutions,'coverage':coverage,'errors':errors}
(ROOT/'coverage-three.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['coverage','errors']},indent=2));assert not errors,errors[:8]
