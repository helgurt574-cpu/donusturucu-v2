import tempfile,os,time,json
from pathlib import Path
from unittest.mock import patch,MagicMock
base=Path(tempfile.mkdtemp(prefix='folder-gtk-'));os.environ['XDG_CONFIG_HOME']=str(base/'config')
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gio
from donusturucu.app import App,Window
app=App([]);app.set_application_id('org.local.donusturucu.folderqa');app.set_flags(Gio.ApplicationFlags.NON_UNIQUE);app.register(None);rows=[]
def pump(predicate):
 deadline=time.monotonic()+25
 while time.monotonic()<deadline:
  while Gtk.events_pending():Gtk.main_iteration_do(False)
  if predicate():return
  time.sleep(.02)
 raise AssertionError('GTK timeout')
for repeat in range(1,4):
 for lang in ['tr','ku']:
  folder=base/f'{repeat}-{lang}'/'input';(folder/'alt').mkdir(parents=True)
  for name in ['a.srt','alt/a.srt']: (folder/name).write_text('1\n00:00:01,000 --> 00:00:02,000\nMerhaba فارسی\n')
  (folder/'b.txt').write_text('Text');(folder/'bad.bin').write_bytes(b'\x00bad')
  w=Window(app,[]);w.lang=lang;w.retranslate();w.output=folder.parent/'output';w.dialog=lambda *a:None;dialog=MagicMock();dialog.run.return_value=Gtk.ResponseType.OK;dialog.get_filename.return_value=str(folder)
  with patch('donusturucu.app.Gtk.FileChooserDialog',return_value=dialog):w.choose_folder()
  pump(lambda:not w.detecting and w.current is not None);assert len(w.items)==3 and w.apply_all.get_active();w.start();pump(lambda:not w.running)
  assert len(list(w.output.glob('*.txt')))==3;assert all(row[5]=='done' for row in w.model);rows.append({'repeat':repeat,'language':lang,'outputs':3,'folder_and_global_settings':True});w.destroy()
Path('qa-folder-1.6.6/gtk-gui.json').write_text(json.dumps(rows,indent=2));print('Passed6 GTK folder GUI flows')
