"""Local model discovery. Runtime never downloads a model or uploads audio."""
from pathlib import Path
import importlib.util,json,os,sys
from . import runtime

class SpeechUnavailable(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)

def settings():
    try:return json.loads((runtime.config_dir()/'speech.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):return {}

def resources():
    config=settings()
    candidates=[os.environ.get('DONUSTURUCU_SPEECH_MODEL'),str(runtime.ROOT/'asr-models/whisper-small'),config.get('model')]
    model=next((Path(p).expanduser().resolve() for p in candidates if p and all((Path(p)/name).is_file() for name in ['model.bin','tokenizer.json','config.json','vocabulary.txt'])),None)
    if not model:raise SpeechUnavailable('speech_model_missing')
    if getattr(sys,'frozen',False):return model,[sys.executable,'--speech-worker']
    pythons=[os.environ.get('DONUSTURUCU_SPEECH_PYTHON'),str(runtime.ROOT/('asr-env/Scripts/python.exe' if sys.platform=='win32' else 'asr-env/bin/python')),config.get('python')]
    python=next((str(Path(p).expanduser()) for p in pythons if p and Path(p).is_file()),None)
    if python is None and importlib.util.find_spec('faster_whisper'):python=sys.executable
    if not python:raise SpeechUnavailable('speech_engine_missing')
    return model,[python,str(Path(__file__).with_name('speech_worker.py'))]

def transcribe(runner,source,output,language,duration,offset=0):
    if language not in {'tr','en'}:raise SpeechUnavailable('speech_language_invalid')
    model,command=resources()
    if output.suffix.lower() not in {'.txt','.srt'}:raise SpeechUnavailable('speech_format_invalid')
    args=[*command,'--format',output.suffix[1:].lower(),'--offset',str(offset),'--model',str(model),'--audio',str(source),'--output',str(output),'--language',language]
    from .core import ConversionError,Cancelled
    try:runner.run(args,duration=duration,timeout=48*3600)
    except ConversionError as error:
        if isinstance(error,Cancelled):raise
        # A broken GPU driver can kill the worker outright; the CPU path is always available.
        output.unlink(missing_ok=True);runner.progress(0)
        runner.run([*args,'--device','cpu'],duration=duration,timeout=48*3600)
    if not output.is_file() or not output.read_text(encoding='utf-8').strip():raise SpeechUnavailable('speech_no_text')
    return output
