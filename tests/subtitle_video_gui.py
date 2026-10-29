"""Drive the extras window: transcribe-free subtitle add (burned and soft) with log output."""
import subprocess,tempfile,time
from pathlib import Path
import tkinter as tk
from donusturucu.extras import ExtraWindow
root_dir=Path(tempfile.mkdtemp(prefix='subtitle-gui-'));out=root_dir/"çıktı, 'test'";video=root_dir/'video.mp4';srt=root_dir/'alt yazı.srt'
subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=320x240:r=24:d=2','-f','lavfi','-i','sine=d=2','-shortest','-c:v','libx264','-c:a','aac',str(video)],check=True)
srt.write_text('1\n00:00:00,200 --> 00:00:01,500\nMerhaba — Silav!\n\n',encoding='utf-8')
root=tk.Tk();root.withdraw();w=ExtraWindow(root,'tr',source=str(video),output=out,theme_name='dark')
state={'stage':0,'start':time.monotonic(),'failed':False}
def tick():
    try:
        assert time.monotonic()-state['start']<120
        if w.detecting or w.running:root.after(150,tick);return
        if state['stage']==0:
            assert 'add_subtitle' in w.action_ids
            w.menu_buttons['add_subtitle'].invoke();root.update_idletasks()
            assert w.fields['audio'].winfo_manager() and w.fields['subtitle_mode'].winfo_manager()
            assert w.field_labels['audio'].cget('text')==w.t('subtitle_file')
            assert w.log_placeholder
            w.vars['audio'].set(str(srt));w.vars['subtitle_mode'].set(w.t('subtitle_burn'));w.run();state['stage']=1
        elif state['stage']==1:
            assert len(list(out.glob('*.mp4')))==1,list(out.iterdir())
            w.vars['subtitle_mode'].set(w.t('subtitle_soft'));w.run();state['stage']=2
        else:
            files=sorted(out.glob('*.mp4'));assert len(files)==2
            kinds=[subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_type','-of','csv=p=0',str(f)],capture_output=True,text=True).stdout.split() for f in files]
            assert ['video','audio'] in kinds and ['video','audio','subtitle'] in kinds,kinds
            log=w.log.get('1.0','end');assert 'Altyazıyı videoya ekle' in log and 'Süre' in log and '→' in log,log
            print('PASS: subtitle action visible, burned + soft outputs, readable log',flush=True);root.destroy();return
        root.after(150,tick)
    except Exception:
        import traceback;traceback.print_exc();state['failed']=True;root.destroy()
root.after(300,tick);root.mainloop()
raise SystemExit(1 if state['failed'] else 0)
