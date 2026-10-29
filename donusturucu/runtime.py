"""Discover bundled or locally installed backends without downloading anything."""
from pathlib import Path
import os
import functools
import tempfile
import shutil
import signal
import subprocess
import sys

ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))
# The source package's portable Pandoc is Linux/amd64 only.
if sys.platform.startswith('linux') and (ROOT/'vendor/bin/pandoc').exists():
    os.environ['PATH']=str(ROOT/'vendor/bin')+os.pathsep+os.environ.get('PATH','')
if (ROOT/'vendor/python').is_dir():sys.path.insert(0,str(ROOT/'vendor/python'))

def tool_path(name):
    if name=='pypdf':
        try:import pypdf;return 'pypdf'
        except ImportError:return None
    suffix='.exe' if sys.platform=='win32' else ''
    names=['soffice.com','soffice.exe'] if name=='libreoffice' and sys.platform=='win32' else ['libreoffice','soffice'] if name=='libreoffice' else [name+suffix]
    roots=[Path(os.environ['DONUSTURUCU_TOOLS'])] if os.environ.get('DONUSTURUCU_TOOLS') else []
    roots += ([ROOT/'vendor/ocr/usr/bin'] if sys.platform.startswith('linux') else [])
    roots += [ROOT/'tools',ROOT/'vendor/tools',Path(sys.executable).resolve().parent/'tools']
    for root in roots:
        candidates=[]
        for exe in names:
            candidates += [root/exe,root/'bin'/exe,root/name/'bin'/exe,root/name/exe]
            if name=='libreoffice':candidates += [root/'LibreOffice/program'/exe,root/'LibreOffice.app/Contents/MacOS'/exe]
        for p in candidates:
            if p.is_file():return str(p)
    for exe in names:
        found=shutil.which(exe)
        if found:return found
    if name=='libreoffice':
        paths=[Path('/Applications/LibreOffice.app/Contents/MacOS/soffice'),Path.home()/'Applications/LibreOffice.app/Contents/MacOS/soffice']
        if sys.platform=='win32':
            paths=[]
            for key in ('PROGRAMFILES','PROGRAMFILES(X86)','LOCALAPPDATA'):
                if os.environ.get(key):
                    paths += [Path(os.environ[key])/'LibreOffice/program/soffice.com',Path(os.environ[key])/'LibreOffice/program/soffice.exe']
        for path in paths:
            if path.is_file():return str(path)
    if sys.platform=='darwin':
        for directory in ['/opt/homebrew/bin','/usr/local/bin']:
            p=Path(directory)/name
            if p.is_file():return str(p)
    return None

def available(name):return bool(tool_path(name))

BACKGROUND_NICE=10

def popen_options():
    # Heavy work runs below normal priority: full speed on an idle machine,
    # but games, browsers and other jobs keep their share of CPU.
    if sys.platform=='win32':
        return {'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS}
    return {'start_new_session':True}

def lower_priority(pid):
    """Renice a freshly started worker; its encoder/office children inherit it."""
    if sys.platform=='win32' or os.environ.get('DONUSTURUCU_PRIORITY')=='normal':return
    try:os.setpriority(os.PRIO_PROCESS,pid,BACKGROUND_NICE)
    except (OSError,AttributeError):pass

def free_cpus():
    """Logical CPUs not already busy with other programs (at least two)."""
    total=os.cpu_count() or 4
    try:busy=os.getloadavg()[0]
    except (OSError,AttributeError):busy=0
    return max(2,min(total,int(total-busy+0.5)))

def terminate_tree(proc,force=False):
    if proc.poll() is not None:return
    if sys.platform=='win32':
        # taskkill is local, and /T includes the office/encoder subprocesses.
        subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        try:os.killpg(proc.pid,signal.SIGKILL if force else signal.SIGTERM)
        except ProcessLookupError:pass

def is_ascii(path):return all(ord(ch)<128 for ch in str(path))

@functools.lru_cache(maxsize=1)
def ascii_dir():
    """A writable folder whose path is plain ASCII. Windows builds of Tesseract and Poppler read
    paths in the old ANSI code page, so C:\\Users\\efrın\\... reaches them as 'efrin' and fails."""
    if sys.platform!='win32':return Path(tempfile.gettempdir())
    candidates=[os.environ.get('TEMP'),os.environ.get('TMP'),
        str(Path(os.environ.get('ProgramData','C:\\ProgramData'))/'Donusturucu'),
        str(Path(os.environ.get('PUBLIC','C:\\Users\\Public'))/'Donusturucu'),
        os.environ.get('SystemDrive','C:')+'\\DonusturucuTemp']
    for candidate in candidates:
        if not candidate or not is_ascii(candidate):continue
        try:
            folder=Path(candidate);folder.mkdir(parents=True,exist_ok=True)
            probe=folder/'.yazma-denemesi';probe.write_text('ok');probe.unlink();return folder
        except OSError:continue
    return Path(tempfile.gettempdir())

def ascii_path(path,folder):
    """Copy a file to an ASCII path when a Windows tool could not open it where it is."""
    path=Path(path)
    if sys.platform!='win32' or is_ascii(path):return path
    target=Path(folder)/('girdi'+path.suffix.lower());shutil.copyfile(path,target);return target

@functools.lru_cache(maxsize=1)
def tessdata_dir():
    source=next((d for d in [ROOT/'tools/tessdata',ROOT/'vendor/ocr/usr/share/tesseract-ocr/5/tessdata'] if d.is_dir()),None)
    if source is None or sys.platform!='win32' or is_ascii(source):return source
    target=ascii_dir()/'tessdata';target.mkdir(parents=True,exist_ok=True)
    for f in source.iterdir():
        dest=target/f.name
        if f.is_file() and (not dest.exists() or dest.stat().st_size!=f.stat().st_size):shutil.copyfile(f,dest)
    return target

def process_env():
    env=os.environ.copy()
    env.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1",DO_NOT_TRACK="1")
    if (ROOT/'tools/pandoc-data').exists():env['pandoc_datadir']=str(ROOT/'tools/pandoc-data')
    data=tessdata_dir()
    if data:env['TESSDATA_PREFIX']=str(data)
    return env

def resolve_command(args):
    exe=tool_path(args[0])
    if not exe:exe=shutil.which(args[0])
    return [exe or args[0],*args[1:]]

def _isolation_command(executable,args):
    return [executable,'--unshare-net','--bind','/','/','--dev-bind','/dev','/dev','--proc','/proc','--die-with-parent','--',*args]

@functools.lru_cache(maxsize=4)
def _isolation_probe(executable):
    # Probe in the same AppArmor/session context as the actual conversion.
    # Ubuntu can expose bwrap while denying its network namespace setup.
    try:
        result=subprocess.run(_isolation_command(executable,['/bin/true']),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=process_env(),timeout=5)
        return result.returncode==0,result.stdout.decode('utf-8',errors='replace').strip()
    except (OSError,subprocess.TimeoutExpired) as exc:
        return False,str(exc)

def _seccomp_command(args):
    python='/usr/bin/python3' if getattr(sys,'frozen',False) else sys.executable
    return [python,str(Path(__file__).with_name('offline_exec.py')),*args]

@functools.lru_cache(maxsize=1)
def _seccomp_probe():
    try:
        result=subprocess.run(_seccomp_command(['--probe']),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=process_env(),timeout=5)
        return result.returncode==0,result.stdout.decode('utf-8',errors='replace').strip()
    except (OSError,subprocess.TimeoutExpired) as exc:return False,str(exc)

def isolation_status():
    if not sys.platform.startswith('linux'):return {'enabled':False,'provider':'local-tools','reason':'non-linux'}
    executable=tool_path('bwrap');enabled,reason=_isolation_probe(executable) if executable else (False,'bwrap unavailable')
    if enabled:return {'enabled':True,'provider':'bwrap','reason':''}
    fallback,failure=_seccomp_probe()
    return {'enabled':fallback,'provider':'seccomp' if fallback else 'unavailable','reason':reason,'fallback_reason':failure}

def isolate(args):
    args=resolve_command(args)
    if not sys.platform.startswith('linux'):return args
    executable=tool_path('bwrap')
    if executable and _isolation_probe(executable)[0]:return _isolation_command(executable,args)
    if _seccomp_probe()[0]:return _seccomp_command(args)
    # Never silently run without the Linux network restriction.
    raise RuntimeError('Local offline isolation unavailable: '+_seccomp_probe()[1])

def config_dir():
    if sys.platform=='win32':return Path(os.environ.get('APPDATA',Path.home()/'AppData/Roaming'))/'Donusturucu'
    if sys.platform=='darwin':return Path.home()/'Library/Application Support/Donusturucu'
    return Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'donusturucu'
