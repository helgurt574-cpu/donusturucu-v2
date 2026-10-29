"""Isolated speech worker. It only accepts a complete local model directory."""
from pathlib import Path
import argparse,json,os,sys,math

def stamp(seconds):
    if not math.isfinite(seconds) or seconds<0:raise ValueError("Invalid subtitle time")
    ms=round(seconds*1000);hours,ms=divmod(ms,3600000);minutes,ms=divmod(ms,60000);seconds,ms=divmod(ms,1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"

def cue(index,start,end,text,offset=0):
    if not math.isfinite(offset) or offset<0 or end<=start:raise ValueError("Invalid subtitle interval")
    text=" ".join(text.split())
    return f"{index}\n{stamp(start+offset)} --> {stamp(end+offset)}\n{text}\n\n"


def normalize_srt(records):
    """Keep generated cues ordered and disjoint without losing recognized text."""
    result=[]
    for item in records:
        current=dict(item)
        current['start']=round(current['start']*1000)/1000
        current['end']=round(current['end']*1000)/1000
        if current['end']<=current['start']:
            if result:result[-1]['text']+=' '+current['text']
            continue
        if result and current['start']<result[-1]['end']:
            if current['start']>result[-1]['start']:
                result[-1]['end']=current['start']
            else:
                result[-1]['text']+=' '+current['text']
                result[-1]['end']=max(result[-1]['end'],current['end'])
                continue
        result.append(current)
    return result


def gpu_busy():
    """True when another program already fills the NVIDIA GPU (games, training, rendering)."""
    import shutil,subprocess
    tool=shutil.which('nvidia-smi')
    if not tool:return False
    try:
        out=subprocess.run([tool,'--query-gpu=memory.free,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5).stdout
        free,load=[float(x) for x in out.splitlines()[0].split(',')]
        # Whisper small needs roughly 1 GB; leave headroom for the other program.
        return free<1500 or load>=85
    except (OSError,ValueError,IndexError,subprocess.TimeoutExpired):return False

def gpu_available(device='auto'):
    if device=='cpu' or os.environ.get('DONUSTURUCU_SPEECH_DEVICE','auto').lower()=='cpu':return False
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count()<=0:return False
    except Exception:return False
    if gpu_busy():
        print('SPEECH_DEVICE_SKIPPED gpu busy',flush=True);return False
    return True

def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--model',required=True);parser.add_argument('--audio',required=True);parser.add_argument('--output',required=True);parser.add_argument('--language',choices=['tr','en'],required=True)
    parser.add_argument('--format',choices=['txt','srt'],default='txt');parser.add_argument('--offset',type=float,default=0);parser.add_argument('--device',choices=['auto','cpu'],default='auto')
    args=parser.parse_args(argv)
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['HF_HUB_DISABLE_TELEMETRY']='1';os.environ['DO_NOT_TRACK']='1'
    model_dir=Path(args.model).resolve()
    for name in ['model.bin','config.json','tokenizer.json','vocabulary.txt']:
        if not (model_dir/name).is_file():raise SystemExit('Missing local speech model file: '+name)
    from faster_whisper import WhisperModel,BatchedInferencePipeline
    import wave,numpy as np
    with wave.open(args.audio,'rb') as source:
        if (source.getframerate(),source.getnchannels(),source.getsampwidth())!=(16000,1,2):raise SystemExit('Speech input must be 16 kHz mono PCM16 WAV')
        samples=np.frombuffer(source.readframes(source.getnframes()),dtype='<i2').astype(np.float32)/32768.0
    # Keep pause-separated utterances separate for subtitles; merging repeated speech can drop words.
    clips=None
    if args.format=='srt':
        from faster_whisper.vad import get_speech_timestamps,VadOptions
        spans=get_speech_timestamps(samples,VadOptions(min_silence_duration_ms=600,max_speech_duration_s=20))
        clips=[{key:value/16000 for key,value in span.items()} for span in spans]
    def run(device):
        if device=='cuda':model=WhisperModel(str(model_dir),device='cuda',compute_type='int8_float16',local_files_only=True)
        else:
            # Half the logical CPUs at most (SMT siblings add little to CTranslate2),
            # and never more than are currently idle so other programs stay smooth.
            total=os.cpu_count() or 8
            try:idle=int(total-os.getloadavg()[0]+0.5)
            except (OSError,AttributeError):idle=total
            threads=max(2,min(16,total//2,idle))
            model=WhisperModel(str(model_dir),device='cpu',compute_type='int8',cpu_threads=threads,num_workers=1,local_files_only=True)
        options={'batch_size':16 if device=='cuda' else 8}
        if clips is not None:options['clip_timestamps']=clips
        segments,info=BatchedInferencePipeline(model=model).transcribe(samples,**options,without_timestamps=args.format!='srt',language=args.language,task='transcribe',beam_size=3,temperature=0,condition_on_previous_text=False,vad_filter=True,vad_parameters={'min_silence_duration_ms':600})
        found=[]
        for segment in segments:
            text=segment.text.strip()
            if not text:continue
            start=max(0,float(segment.start));end=min(len(samples)/16000,float(segment.end))
            if end<=start:continue
            found.append({'start':start,'end':end,'text':text})
            print('out_time_us='+str(round(segment.end*1_000_000)),flush=True)
        return found
    records=None;output=Path(args.output)
    if gpu_available(args.device):
        try:
            print('SPEECH_DEVICE cuda',flush=True);records=run('cuda')
        except Exception as error:
            # Missing cuDNN/driver or too little video memory: the CPU path gives the same text.
            print('SPEECH_DEVICE_FALLBACK '+type(error).__name__+': '+str(error)[:200],flush=True)
    if records is None:
        print('SPEECH_DEVICE cpu',flush=True);records=run('cpu')
    if args.format=='srt':records=normalize_srt(records)
    with output.open('w',encoding='utf-8') as stream:
        for index,record in enumerate(records,1):
            stream.write(cue(index,record['start'],record['end'],record['text'],args.offset) if args.format=='srt' else record['text']+'\n')
    output.with_suffix('.segments.json').write_text(json.dumps({'language':args.language,'format':args.format,'source_offset':args.offset,'segments':records},ensure_ascii=False,indent=2),encoding='utf-8')
    print('SPEECH_COMPLETE',len(records),flush=True)

if __name__=='__main__':main()
