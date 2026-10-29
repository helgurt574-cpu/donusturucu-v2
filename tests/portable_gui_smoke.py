import os,tempfile
from pathlib import Path
root=Path(tempfile.mkdtemp(prefix='donustur-portable-ui-'))
os.environ['XDG_CONFIG_HOME']=str(root/'config')
from test_conversion import odf
from donusturucu.portable import Window
source=root/'Örnek sunu.odp'
odf(source,'presentation','<draw:page draw:name="Silav"><draw:frame><draw:text-box><text:p>Merhaba dünya. Silav cîhan!</text:p></draw:text-box></draw:frame></draw:page>')
w=Window();w.output=root/'out';w.path_label.configure(text=str(Path.home()/'Dönüştürülenler'))
w.add_paths([str(source)]);stage={'started':False,'shot':False,'done':False,'error':None}
assets=Path(__file__).resolve().parents[1]/'assets'
def screenshot(name):
    import gi
    gi.require_version('Gdk','3.0');gi.require_version('GdkX11','3.0')
    from gi.repository import Gdk,GdkX11
    Gdk.init([])
    handle=GdkX11.X11Window.foreign_new_for_display(Gdk.Display.get_default(),w.winfo_id())
    image=Gdk.pixbuf_get_from_window(handle,0,0,w.winfo_width(),w.winfo_height())
    image.savev(str(assets/name),'png',[],[])
def tick():
    try:
        if w.detecting:w.after(150,tick);return
        if not stage['started']:
            assert len(w.items)==1
            assert len(w.target['values'])==14,w.target['values']
            w.target.set('DOCX');w.only_text.set(True);w.use_ocr.set(True);w.ocr_lang.set('English');w.update_options()
            assert next(iter(w.items.values()))['options'].only_text
            assert next(iter(w.items.values()))['options'].ocr
            w.language.set('Kurmancî');w.change_language();assert w.title().startswith('Veguherîner')
            w.language.set('Türkçe');w.change_language()
            w.start();assert 'disabled' not in w.stop_btn.state()
            stage['started']=True;w.after(250,tick);return
        if not stage['shot']:
            screenshot('arayuz-portable-calisiyor.png');stage['shot']=True
        if w.running:w.after(150,tick);return
        assert all(i['status']=='done' for i in w.items.values()),w.logs
        assert w.t('complete') in w.status.cget('text')
        assert hasattr(w,'completion_dialog')
        assert next(iter(w.items.values()))['result'].suffix=='.docx'
        screenshot('arayuz-portable-tr.png')
        stage['done']=True
        print('PASS: portable UI, 14 presentation formats, TR/KU, DOCX conversion, readable active stop state',flush=True)
        w.destroy()
    except Exception as e:
        import traceback;traceback.print_exc();stage['error']=str(e);w.cancel();w.destroy()
w.after(180,tick)
w.after(35000,lambda:(w.cancel(),w.destroy()))
w.mainloop()
if stage['error'] or not stage['done']:raise SystemExit(1)
