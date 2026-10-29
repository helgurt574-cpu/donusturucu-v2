import tempfile,os,time,json
from pathlib import Path
from unittest.mock import patch
rootdir=Path(tempfile.mkdtemp(prefix='folder-gui-'));os.environ['XDG_CONFIG_HOME']=str(rootdir/'config')
from donusturucu.portable import Window
from donusturucu.extras import ExtraWindow
import tkinter as tk
SRT='1\n00:00:01,000 --> 00:00:02,000\nMerhaba فارسی\n\n';rows=[]
def pump(window,predicate,timeout=15):
 deadline=time.monotonic()+timeout
 while time.monotonic()<deadline:
  window.update()
  if predicate():return
  time.sleep(.02)
 raise AssertionError('GUI timeout')
def destroy(window):
 for timer in window.tk.call('after','info'):
  try:window.after_cancel(timer)
  except Exception:pass
 window.destroy()
with patch('tkinter.messagebox.showwarning'),patch('tkinter.messagebox.showinfo'),patch('tkinter.messagebox.showerror'):
 for repeat in range(1,4):
  for lang in ['tr','ku']:
   case=rootdir/f'{repeat}-{lang}';folder=case/'input';(folder/'alt').mkdir(parents=True);(folder/'a.srt').write_text(SRT);(folder/'alt/a.srt').write_text(SRT.replace('Merhaba','Silav'));(folder/'other.txt').write_text('A document.');(folder/'bad.bin').write_bytes(b'\x00bad')
   w=Window();w.lang=lang;w.translate();w.output=case/'convert'
   os.environ['DONUSTURUCU_NATIVE_DIALOGS']='0'
   with patch('tkinter.filedialog.askdirectory',return_value=str(folder)):w.choose_folder()
   pump(w,lambda:not w.detecting);assert len(w.items)==3 and w.apply_all.get();assert w.folder_add_btn['text']==w.t('add_folder')
   first=next(i for i,v in w.items.items() if v['info'].fmt=='srt');w.tree.selection_set(first);w.select();assert w.items[first]['target']=='txt';w.start();assert 'disabled' in w.apply_all_check.state();pump(w,lambda:not w.running)
   assert len(list(w.output.glob('*.txt')))==3;assert all(i['status']=='done' for i in w.items.values());destroy(w);rows.append({'ui':'portable','language':lang,'repeat':repeat,'outputs':3,'folder_and_global_settings':True})
   root=tk.Tk();root.withdraw();e=ExtraWindow(root,lang,output=case/'extras')
   os.environ['DONUSTURUCU_NATIVE_DIALOGS']='0'
   with patch('tkinter.filedialog.askdirectory',return_value=str(folder)):e.choose_folder()
   pump(root,lambda:not e.detecting);assert len(e.files)==3 and e.batch_all.get();e.menu_buttons['subtitle_text'].invoke();root.update();assert e.batch_toggle.winfo_ismapped() and e.merge_panel.winfo_ismapped();e.run();pump(root,lambda:not e.running)
   assert len(list(e.output.glob('*.txt')))==2;assert '1' in e.log.get('1.0','end');destroy(e);destroy(root);rows.append({'ui':'extras','language':lang,'repeat':repeat,'outputs':2,'incompatible_file_reported':True})
Path('qa-folder-1.6.6/gui.json').write_text(json.dumps(rows,indent=2));print('Passed',len(rows),'folder GUI flows')
