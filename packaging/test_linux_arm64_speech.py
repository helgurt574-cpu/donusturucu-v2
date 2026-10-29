"""Run with the isolated ARM64 Python under qemu-aarch64, not host Python."""
import hashlib,json,os,platform,sys,time
from pathlib import Path
base=Path(__file__).resolve().parents[1];out=base/'build/arm64-test';start=time.monotonic()
assert platform.machine()=='aarch64',platform.machine()
import numpy,ctranslate2,av,onnxruntime,tokenizers,faster_whisper
report={'architecture':platform.machine(),'python':platform.python_version(),'emulated':True,'imports':{m.__name__:m.__version__ for m in [numpy,ctranslate2,av,onnxruntime,tokenizers,faster_whisper]}}
(out/'imports.json').write_text(json.dumps(report,indent=2))
model=faster_whisper.WhisperModel(str(base/'build/package-arm64/usr/share/donusturucu/asr-models/whisper-small'),device='cpu',compute_type='int8',cpu_threads=2,num_workers=1,local_files_only=True)
source=base/'assets/speech/english-test.mp3';before=hashlib.sha256(source.read_bytes()).hexdigest();frames=[]
with av.open(str(source),mode='r') as container:
 resampler=av.AudioResampler(format='s16',layout='mono',rate=16000)
 for frame in container.decode(audio=0):
  for converted in resampler.resample(frame):frames.append(converted.to_ndarray().reshape(-1))
 for converted in resampler.resample(None):frames.append(converted.to_ndarray().reshape(-1))
samples=numpy.concatenate(frames).astype(numpy.float32)/32768.0
pipeline=faster_whisper.BatchedInferencePipeline(model=model)
segments,info=pipeline.transcribe(samples,batch_size=1,language='en',beam_size=3,temperature=0,vad_filter=True,vad_parameters={'min_silence_duration_ms':600},condition_on_previous_text=False)
text='\n'.join(s.text.strip() for s in segments);assert 'could you repeat that' in text.lower(),text;assert hashlib.sha256(source.read_bytes()).hexdigest()==before
report.update({'english_speech_passed':True,'text':text,'elapsed_seconds':round(time.monotonic()-start,2)});(out/'speech-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
