import os,tempfile,time
from pathlib import Path
import tkinter as tk
from donusturucu.extras import ExtraWindow,TEXT
from donusturucu import core
from pypdf import PdfWriter
root=tk.Tk();root.withdraw();folder=Path(tempfile.mkdtemp(prefix='extras-ui-'))
w=ExtraWindow(root,'tr',source='verified-matrix-linux/seeds/Video.mp4',output=folder)
state={'stage':0,'failed':False,'start':time.monotonic()}
def snapshot():
 import gi
 gi.require_version('Gdk','3.0');gi.require_version('GdkX11','3.0')
 from gi.repository import Gdk,GdkX11
 Gdk.init([]);handle=GdkX11.X11Window.foreign_new_for_display(Gdk.Display.get_default(),w.winfo_id())
 image=Gdk.pixbuf_get_from_window(handle,0,0,w.winfo_width(),w.winfo_height());image.savev('assets/farkli-islemler.png','png',[],[])
def tick():
 try:
  assert time.monotonic()-state['start']<45
  if w.detecting or w.running:root.after(100,tick);return
  if state['stage']==0:
   assert 'mute_range' in w.action_ids and 'replace_audio' in w.action_ids
   w.action.current(w.action_ids.index('add_audio'));w.use_audio_range.set(True);w.show_fields()
   assert w.fields['audio_start'].winfo_manager() and w.fields['audio_end'].winfo_manager()
   w.action.current(w.action_ids.index('merge'));w.show_fields();assert w.segment.winfo_manager()
   w.action.current(w.action_ids.index('mute_range'));w.show_fields();w.vars['start'].set('0.1');w.vars['end'].set('0.4')
   root.update_idletasks();snapshot();w.run();state['stage']=1
  elif state['stage']==1:
   assert list(folder.glob('*.mp4'))
   p=folder/'Pages.pdf';writer=PdfWriter();writer.add_blank_page(width=200,height=300);writer.write(p)
   w.files=[core.detect(p)];w.ranges=[('0','')];w.display_files()
   assert w.action_ids==['split','merge'];w.use_range.set(True);w.show_fields();assert w.fields['pages'].winfo_manager();assert not w.fields['start'].winfo_manager()
   other=ExtraWindow(root,'ku');assert other.title().startswith(TEXT['ku']['title']);other.destroy()
   print('PASS: type-specific actions, video/audio ranges, per-file merge controls, PDF controls, TR/KU, real mute operation, screenshot',flush=True)
   w.destroy();root.destroy();return
 except Exception:
  import traceback;traceback.print_exc();state['failed']=True
  if w.runner:w.runner.cancel()
  root.destroy();return
 root.after(100,tick)
root.after(300,tick);root.mainloop()
if state['failed'] or state['stage']!=1:raise SystemExit(1)
