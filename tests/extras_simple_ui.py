"""Check understandable labels and operation-specific ranges with real outputs."""
import tempfile,time
from pathlib import Path
import tkinter as tk
from donusturucu.extras import ExtraWindow,clock
from donusturucu import core
root=tk.Tk();root.withdraw();output=Path(tempfile.mkdtemp(prefix='simple-extras-'))
w=ExtraWindow(root,'tr',source='verified-matrix-linux/seeds/Video.mp4',output=output)
state={'stage':0,'failed':False,'start':time.monotonic()}
def select(action):w.menu_buttons[action].invoke();root.update_idletasks()
def snapshot():
 import gi
 gi.require_version('Gdk','3.0');gi.require_version('GdkX11','3.0')
 from gi.repository import Gdk,GdkX11
 Gdk.init([]);p=GdkX11.X11Window.foreign_new_for_display(Gdk.Display.get_default(),w.winfo_id());img=Gdk.pixbuf_get_from_window(p,0,0,w.winfo_width(),w.winfo_height());img.savev('assets/farkli-islemler-sade.png','png',[],[])
def tick():
 try:
  assert time.monotonic()-state['start']<45
  if w.detecting or w.running:root.after(120,tick);return
  if state['stage']==0:
   root.update_idletasks()
   assert w.action.get()=='Video kes'
   assert not w.listbox.winfo_ismapped();assert not w.action.winfo_ismapped();assert not w.log.winfo_ismapped()
   assert len(w.menu_buttons)==15 and all(b.winfo_ismapped() for b in w.menu_buttons.values())
   assert w.field_labels['start'].cget('text')=='Başlangıç zamanı'
   assert '∞' not in w.listbox.get(0)
   assert clock('9520.135')=='02:38:40.135'
   select('merge');assert w.listbox.winfo_ismapped() and w.merge_panel.winfo_ismapped()
   select('trim');assert not w.listbox.winfo_ismapped()
   select('add_audio');assert not w.fields['audio_start'].winfo_manager()
   assert 'girsin' in w.field_labels['start'].cget('text')
   w.use_audio_range.set(True);w.show_fields();assert w.fields['audio_start'].winfo_manager()
   select('frame');assert not w.fields['end'].winfo_manager();assert 'fotoğraf' in w.field_labels['start'].cget('text')
   select('extract_audio');w.use_range.set(False);w.show_fields();assert not w.fields['start'].winfo_manager()
   w.vars['start'].set('.1');w.vars['end'].set('.3');w.run();state['stage']=1
  elif state['stage']==1:
   files=list(output.glob('*.mp3'));assert len(files)==1
   assert core.detect(files[0]).duration>.5,'Hidden stale range must not trim whole-file extraction'
   w.use_range.set(True);w.show_fields();assert w.fields['start'].winfo_manager()
   w.run();state['stage']=2
  elif state['stage']==2:
   files=list(output.glob('*.mp3'));assert len(files)==2
   assert min(core.detect(p).duration for p in files)<.4
   select('trim');w.vars['start'].set('00:00:00.1');w.vars['end'].set('00:00:00.4');state['stage']=3
   root.after(250,tick);return
  elif state['stage']==3:
   snapshot()
   from pypdf import PdfWriter
   source=output/'Belge.pdf';writer=PdfWriter()
   for width in [200,300,400]:writer.add_blank_page(width=width,height=500)
   writer.write(source);writer.close()
   w.files=[core.detect(source)];w.ranges=[('0','')];w.display_files()
   w.use_range.set(False);w.show_fields();assert w.fields['page_count'].winfo_manager() and not w.fields['pages'].winfo_manager()
   w.vars['page_count'].set('2');w.vars['pages'].set('99');w.run();state['stage']=4
  elif state['stage']==4:
   from pypdf import PdfReader
   parts=[p for p in output.glob('*.pdf') if p.name!='Belge.pdf'];assert len(parts)==2
   assert sorted(len(PdfReader(p).pages) for p in parts)==[1,2]
   w.use_range.set(True);w.show_fields();assert w.fields['pages'].winfo_manager() and not w.fields['page_count'].winfo_manager()
   w.vars['pages'].set('3');w.vars['page_count'].set('99');w.run();state['stage']=5
  else:
   from pypdf import PdfReader
   parts=[p for p in output.glob('*.pdf') if p.name!='Belge.pdf'];assert len(parts)==3
   assert any(len(PdfReader(p).pages)==1 and float(PdfReader(p).pages[0].mediabox.width)==400 for p in parts)
   print('PASS: clear action names, ordering only for merge, contextual labels, whole-file/range extraction, formatted duration, no infinity notation',flush=True)
   w.destroy();root.destroy();return
 except Exception:
  import traceback;traceback.print_exc();state['failed']=True
  if w.runner:w.runner.cancel()
  root.destroy();return
 root.after(120,tick)
root.after(200,tick);root.mainloop()
if state['failed'] or state['stage']!=5:raise SystemExit(1)
