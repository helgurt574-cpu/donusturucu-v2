"""Invoke each visible editing action through the real Tk UI three times."""
from pathlib import Path
import os,sys,time,json,subprocess,hashlib,gc
gc.disable()
APP=Path(os.environ['DONUSTURUCU_TEST_APP_ROOT']);sys.path.insert(0,str(APP));BASE=Path(__file__).resolve().parents[1]
from donusturucu import core
from donusturucu.operations import actions
from donusturucu.extras import ExtraWindow
from tkinter import messagebox
import tkinter as tk
from pypdf import PdfWriter,PdfReader
OUT=Path(os.environ.get('DONUSTURUCU_AUDIT_OUT',str(BASE/'qa-1.6.2')))/'ui-all-actions';OUT.mkdir(parents=True,exist_ok=True);seeds=OUT/'seeds';seeds.mkdir(exist_ok=True)
audio=BASE/'assets/speech/english-test.mp3';video=seeds/'spoken.mp4'
subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=s=176x144:r=10:d=6','-stream_loop','-1','-i',str(audio),'-t','6','-c:v','libx264','-c:a','aac','-y',str(video)],check=True)
pdf=seeds/'pages.pdf';writer=PdfWriter();[writer.add_blank_page(width=300+i,height=400) for i in range(5)];writer.write(pdf);writer.close()
originals={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [audio,video,pdf]};root=tk.Tk();root.withdraw();rows=[];errors=[];retained=[]
messagebox.showerror=lambda title,detail,**kwargs:errors.append(str(detail));messagebox.showwarning=lambda title,detail,**kwargs:errors.append(str(detail))
def save():
 p=OUT/'report.pending.json';p.write_text(json.dumps({'cases':len(rows),'failures':sum(not r['pass'] for r in rows),'app_root':str(APP),'rows':rows},ensure_ascii=False,indent=2));p.replace(OUT/'report.json')
def wait(w,limit=180):
 begin=time.monotonic()
 while w.running or w.detecting:
  root.update();time.sleep(.02)
  if time.monotonic()-begin>limit:
   if w.runner:w.runner.cancel()
   raise TimeoutError('UI action timeout')
 root.update()
for source in [video,audio,pdf]:
 for action in actions(core.detect(source)):
  for rep in range(1,4):
   row={'kind':core.detect(source).kind,'action':action,'repeat':rep,'language':'ku' if rep==2 else 'tr'};w=None;errors.clear()
   try:
    folder=OUT/'outputs'/row['kind']/action/str(rep);folder.mkdir(parents=True,exist_ok=True)
    w=ExtraWindow(root,row['language'],source=str(source),output=folder);wait(w);assert not errors,errors
    assert action in w.menu_buttons;w.menu_buttons[action].invoke();root.update();assert w.current_action()==action
    if action=='merge':w.add_paths([str(source)]);wait(w);assert len(w.files)==2;w.menu_buttons[action].invoke()
    w.use_range.set(rep!=1);w.use_audio_range.set(rep==3);w.show_fields()
    values={'start':'.25','end':'1.75','part':'.6','pages':'1-2;4,5','page_count':'2','factor':'90' if action=='rotate' else '1.5','audio':str(audio),'audio_start':'.1','audio_end':'1.2','speech_language':'English'}
    if action=='transcribe':values.update(start='0',end='')
    if action=='split' and source==pdf:w.use_range.set(rep==2);w.show_fields()
    for key,value in values.items():w.vars[key].set(value)
    w.run_button.invoke();wait(w);assert not errors,errors;assert w.status.cget('text')==w.t('done'),w.status.cget('text')
    files=[p for p in folder.iterdir() if p.is_file()];assert files,'No GUI output'
    for p in files:
     if source==pdf:assert len(PdfReader(p).pages)>0
     elif action=='transcribe':assert 'repeat that' in p.read_text().lower(),p.read_text()
     else:subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','null','-'],check=True,capture_output=True,timeout=60)
    row.update({'pass':True,'outputs':list(map(str,files))})
   except Exception as e:row.update({'pass':False,'error':str(e),'dialogs':list(errors)})
   finally:
    if w is not None:
     if w.runner:w.runner.cancel()
     for timer in w.tk.call('after','info'):
      try:w.after_cancel(timer)
      except tk.TclError:pass
     retained.append(w);w.destroy();root.update()
   rows.append(row);save();print(row['kind'],action,rep,row['pass'],row.get('error',''),flush=True)
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in originals.items());root.destroy();assert all(r['pass'] for r in rows)
