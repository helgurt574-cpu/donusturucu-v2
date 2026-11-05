"""Entry for offline cross-assembled installers (not a frozen executable)."""
from pathlib import Path
import os,sys,runpy,traceback,json,datetime
# Guard direct launches against inherited Python configuration.
os.environ.pop('PYTHONHOME',None)
os.environ.pop('PYTHONPATH',None)
ROOT=Path(__file__).resolve().parent
runtime=Path(os.environ.get('DONUSTURUCU_RUNTIME') or ROOT/'runtime')
paths=[runtime/'Library/bin',runtime/'Scripts',runtime] if sys.platform=='win32' else [runtime/'bin']
os.environ['PATH']=os.pathsep.join(map(str,paths))+os.pathsep+os.environ.get('PATH','')
os.environ['PYTHONPATH']=str(ROOT)
os.environ['PYTHONNOUSERSITE']='1'
os.environ['DONUSTURUCU_TOOLS']=str(paths[0])
os.environ['DONUSTURUCU_SPEECH_PYTHON']=sys.executable
os.environ['TESSDATA_PREFIX']=str(ROOT/'tools/tessdata')
os.environ.setdefault('PYTHONUTF8','1')
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
_DLL_HANDLES=[]
if sys.platform=='win32':
 for folder in paths:
  if folder.is_dir():_DLL_HANDLES.append(os.add_dll_directory(str(folder)))
 for folder in [runtime/'Library/lib/tcl8.6',runtime/'Library/lib/tk8.6']:
  if folder.is_dir():os.environ['TCL_LIBRARY' if folder.name.startswith('tcl') else 'TK_LIBRARY']=str(folder)
sys.path.insert(0,str(ROOT))
def start():
 if '--startup-test' in sys.argv:
  import tkinter as tk
  window=tk.Tk();window.withdraw();window.update();window.destroy()
  from donusturucu.portable import Window
  from donusturucu import webapp,jobs,studio_ops
  print('STARTUP_OK',sys.version,flush=True)
 elif '--self-test' in sys.argv:
  from donusturucu import selftest
  args=sys.argv[sys.argv.index('--self-test')+1:]
  raise SystemExit(selftest.main(args[:1]))
 elif '--tk' in sys.argv:
  sys.argv.remove('--tk')
  from donusturucu.portable import main
  main()
 else:
  # New interface: a local page in an app window (same design as Android and Linux).
  from donusturucu.webapp import main
  main()
try:start()
except Exception:
 message=traceback.format_exc();print(message,file=sys.stderr,flush=True)
 try:
  (ROOT/'startup-error.txt').write_text(message,encoding='utf-8')
  if sys.platform=='win32':
   import ctypes
   ctypes.windll.user32.MessageBoxW(None,'Dönüştürücü açılamadı. Hata kaydı:\n'+str(ROOT/'startup-error.txt')+'\n\n'+message[-1200:],'Dönüştürücü — Açılış hatası',16)
 except Exception:pass
 raise SystemExit(1)
