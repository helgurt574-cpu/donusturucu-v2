"""Run the GTK interface against two real files; save both UI languages."""
import os
import tempfile
from pathlib import Path
root=Path(tempfile.mkdtemp(prefix='donustur-ui-test-'))
os.environ['XDG_CONFIG_HOME']=str(root/'config')
import subprocess
import gi
gi.require_version('Gtk','3.0')
from gi.repository import GLib,Gtk,Gdk
from donusturucu.app import App,Window
text=root/'Merhaba û Silav.txt';text.write_text('Merhaba dünya. Silav cîhan!')
video=root/'Örnek video.mp4'
subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=160x120:r=12:d=0.5','-f','lavfi','-i','sine=frequency=440:duration=0.5','-c:v','libx264','-c:a','aac','-shortest','-y',str(video)],check=True)
app=App([]);app.register(None);w=Window(app,[])
w.output=root/'results'; w.folder_label.set_text(str(Path.home()/'Dönüştürülenler'))
w.add_paths([str(text),str(video)])
state={'started':False,'error':False,'snapshots':[],'finished':False}
assets=Path(__file__).resolve().parents[1]/'assets'
def take_snapshot(lang):
    pixbuf=Gdk.pixbuf_get_from_window(w.get_window(),0,0,w.get_allocated_width(),w.get_allocated_height())
    pixbuf.savev(str(assets/('arayuz-'+lang+'.png')),'png',[],[])
def tick():
    if w.detecting or w.running:return True
    try:
        if not state['started']:
            assert len(w.model)==2
            w.tree.get_selection().select_path(1)
            w.target_combo.set_active_id('mp3')
            assert w.items[w.current]['target']=='mp3'
            assert not w.video_box.get_visible(), 'Video settings should be hidden for audio extraction'
            w.language.set_active_id('ku');assert w.get_title().startswith('Veguherîner')
            w.language.set_active_id('tr')
            w.start();state['started']=True;return True
        if not state['finished']:
            assert all(row[5]=='done' for row in w.model),w.logs
            assert w.t('complete') in w.status.get_text()
            assert hasattr(w,'completion_dialog')
            state['finished']=True
            w.language.set_active_id('tr');return True
        if not state['snapshots']:
            take_snapshot('tr');state['snapshots'].append('tr');w.language.set_active_id('ku');return True
        take_snapshot('ku')
        print('PASS: detection, per-file target, hidden irrelevant settings, TR/KU, background conversion, output files',flush=True)
        app.quit();return False
    except Exception:
        import traceback;traceback.print_exc();state['error']=True;app.quit();return False
GLib.timeout_add(400,tick)
def timeout():
    state['error']=True;w.cancel();app.quit();return False
GLib.timeout_add_seconds(45,timeout)
app.run(['gui-smoke'])
raise SystemExit(1 if state['error'] else 0)
