"""Offline editing operations. Originals are read only; all outputs are new files."""
from __future__ import annotations
from dataclasses import dataclass,replace
from pathlib import Path
from fractions import Fraction
import json,math,os,shutil,tempfile
from . import core

SUBTITLE_TYPES={'.srt','.ass','.ssa','.vtt'}

def runtime_fonts():
    folder=core.runtime.ROOT/'assets/fonts'
    return folder if (folder/'DejaVuSans.ttf').is_file() else None

class OperationError(ValueError):pass

def seconds(value):
    try:
        parts=str(value).strip().replace(',','.').split(':')
        if not 1<=len(parts)<=3:raise ValueError()
        numbers=[float(x) for x in parts]
        if any(not math.isfinite(x) or x<0 for x in numbers):raise ValueError()
        if len(parts)>1 and (any(x>=60 for x in numbers[1:]) or any(not x.is_integer() for x in numbers[:-1])):raise ValueError()
        return sum(x*60**i for i,x in enumerate(reversed(numbers)))
    except (ValueError,TypeError):raise OperationError('invalid_time')

def actions(info):
    if info.kind=='video':
        available=['trim','remove_range','split','merge','mute_range','mute','extract_audio','add_audio','replace_audio','frame','gif','rotate','speed','transcribe','add_subtitle']
        return available if info.has_audio else [a for a in available if a not in {'mute_range','mute','extract_audio','replace_audio','transcribe'}]
    if info.kind=='audio':return ['trim','remove_range','split','merge','mute_range','volume','speed','fade_in','fade_out','transcribe']
    if info.fmt=='srt':return ['subtitle_text']
    if info.fmt=='txt':return ['split','merge','subtitle_restore']
    return ['split','merge']

@dataclass
class Request:
    action:str
    files:list
    output:Path
    start:str='0'
    end:str=''
    part:str='60'
    pages:str=''
    page_count:str='1'
    audio:str=''
    factor:str='1'
    segments:list|None=None
    audio_start:str='0'
    audio_end:str=''
    language:str='tr'
    speech_language:str='tr'
    speech_format:str='txt'
    subtitle_mode:str='burn'

class Editor:
    def __init__(self,runner=None):self.runner=runner or core.Runner()
    def probe(self,path):
        p=core._capture(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_format','-show_streams','-of','json',str(path)])
        if p.returncode:raise OperationError('invalid_media')
        return json.loads(p.stdout)
    def duration(self,path):
        try:value=float(self.probe(path)['format']['duration'])
        except (ValueError,KeyError):raise OperationError('unknown_duration')
        if not math.isfinite(value) or value<=0:raise OperationError('unknown_duration')
        return value
    def interval(self,request,duration):
        start=seconds(request.start);end=seconds(request.end) if request.end.strip() else duration
        if start>=end or end>duration+0.05:raise OperationError('invalid_range')
        return start,min(end,duration)
    def ff(self,args,duration=0):
        args=list(args)
        if '-c:v' in args and args[args.index('-c:v')+1]=='libx264':
            pad='pad=ceil(iw/2)*2:ceil(ih/2)*2'
            if '-vf' in args:
                i=args.index('-vf')+1;args[i]+=','+pad
            else:args[-1:-1]=['-vf',pad]
        self.runner.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin',*args,'-progress','pipe:1','-y'],duration=duration)
    def input(self,path):return ['-protocol_whitelist','file,pipe','-i',str(path)]
    def keep_audio_format(self,products,info,work):
        """Audio edits are made in WAV; hand the result back in the format the user gave (MP3 in → MP3 out)."""
        if info.fmt not in core.AUDIO or info.fmt=='wav':return products
        kept=[]
        for n,product in enumerate(products):
            if product.suffix.lower()!='.wav':kept.append(product);continue
            self.runner.check();kept.append(self.runner.convert(core.detect(product),info.fmt,work/f'format-{n}'))
        return kept
    def subtitle_file(self,path,folder):
        """Copy a subtitle as UTF-8 into a folder whose path is safe inside an FFmpeg filter."""
        path=Path(path) if path else None
        if not path or not path.is_file() or path.suffix.lower() not in SUBTITLE_TYPES:raise OperationError('choose_subtitle')
        raw=path.read_bytes()
        for encoding in ('utf-8-sig','utf-16','cp1254','cp1256','latin-1'):
            try:
                text=raw.decode(encoding)
                if encoding=='utf-16' and not raw.startswith((b'\xff\xfe',b'\xfe\xff')):continue
                break
            except UnicodeDecodeError:continue
        text=text.replace('\r\n','\n').replace('\r','\n')
        # FFmpeg tolerates loosely formatted files; only reject ones with no timed cues at all.
        timed='-->' in text if path.suffix.lower() in {'.srt','.vtt'} else 'Dialogue:' in text
        if not timed:raise OperationError('choose_subtitle')
        staged=Path(folder)/('subtitle'+path.suffix.lower());staged.write_text(text,encoding='utf-8')
        return staged
    def add_subtitle(self,r,source,info,out,duration):
        safe=Path(tempfile.mkdtemp(prefix='donustur-sub-'))
        try:
            staged=self.subtitle_file(r.audio,safe)
            if r.subtitle_mode=='soft':
                base=[*self.input(source),*self.input(staged),'-map','0:v:0','-map','0:a?','-map','1:0','-c:s','mov_text','-metadata:s:s:0','handler_name=Subtitle','-disposition:s:0','default']
                try:self.ff([*base,'-c:v','copy','-c:a','copy',str(out)],duration)
                except core.ConversionError:
                    # Some source codecs (e.g. DTS audio) cannot live in MP4; re-encode only then.
                    out.unlink(missing_ok=True)
                    self.ff([*base,'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',str(out)],duration)
            else:
                # Inside quotes FFmpeg keeps spaces/commas; ':' still needs an escape (Windows drives).
                name=staged.as_posix().replace(':','\\:')
                # Bundled fonts: static FFmpeg builds cannot always read the system font configuration.
                fonts=runtime_fonts();extra=''
                if fonts:
                    staged_fonts=safe/'fonts';shutil.copytree(fonts,staged_fonts)
                    extra=":fontsdir='"+staged_fonts.as_posix().replace(':','\\:')+"'"
                    if staged.suffix in {'.srt','.vtt'}:extra+=":force_style='FontName=DejaVu Sans'"
                self.ff([*self.input(source),'-map','0:v:0','-map','0:a?','-vf',f"subtitles=filename='{name}':charenc=UTF-8{extra}",
                    '-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-sn',str(out)],duration)
        finally:shutil.rmtree(safe,ignore_errors=True)
    def clip(self,path,out,start=0,end=None,video=True,shape=None):
        duration=(end-start) if end is not None else self.duration(path)
        # Video must reach the cadence filter before output seeking: input
        # seeking can discard a VFR frame still visible at the cut point.
        info=core.detect(path);late_seek=video or info.fmt in {'mpegts','mpeg'}
        args=([*self.input(path)] if late_seek else ['-ss',str(start),*self.input(path)])
        if shape and not info.has_audio:args+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
        if late_seek:args+=['-ss',str(start)]
        args+=['-t',str(duration),'-map','0:v:0','-map',('0:a:0' if info.has_audio else '1:a:0')] if shape else ['-t',str(duration),'-map','0:v:0','-map','0:a:0?'] if video else ['-t',str(duration),'-map','0:a:0','-vn']
        if video:
            stream=next(s for s in self.probe(path)['streams'] if s['codec_type']=='video')
            try:
                cadence=Fraction(stream.get('avg_frame_rate','25'));assert 0<cadence<=240
            except (ValueError,ZeroDivisionError,AssertionError):cadence=Fraction(25)
            # Hold the final displayed frame through an audio-led container tail.
            filt=f'fps={cadence},tpad=stop_mode=clone:stop_duration={duration},pad=ceil(iw/2)*2:ceil(ih/2)*2'
            if shape:
                w,h,fps=shape;filt=f'fps={fps},tpad=stop_mode=clone:stop_duration={duration},scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1'
            args+=['-vf',filt,'-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p','-c:a','aac']
            if shape:args+=['-ar','48000','-ac','2']
        else:args+=['-c:a','pcm_s16le','-ar','48000','-ac','2']
        args+=['-sn','-dn',str(out)];self.ff(args,duration)
        expected='video' if video else 'audio'
        if not any(s.get('codec_type')==expected for s in self.probe(out).get('streams',[])):raise OperationError('range_too_short')
    def concat(self,files,out,work):
        manifest=work/'join.txt'
        # Only generated filenames in our own staging directory enter the list.
        manifest.write_text(''.join("file '"+p.name+"'\n" for p in files),encoding='utf-8')
        self.ff(['-f','concat','-safe','1',*self.input(manifest),'-c','copy',str(out)])
    def pdf(self,info,work):
        if info.kind=='pdf':return info.path
        return self.runner.convert(info,'pdf',work)
    def document(self,r,infos,work):
        from pypdf import PdfReader,PdfWriter
        docs=[]
        for n,info in enumerate(infos):
            self.runner.check();folder=work/f'doc{n}';folder.mkdir()
            reader=PdfReader(self.pdf(info,folder))
            if reader.is_encrypted:raise OperationError('encrypted')
            docs.append(reader)
        outputs=[]
        if r.action=='merge':
            writer=PdfWriter()
            for reader in docs:
                for page in reader.pages:self.runner.check();writer.add_page(page)
            out=work/'merged.pdf';writer.write(out);writer.close();outputs=[out]
        else:
            reader=docs[0];total=len(reader.pages);groups=[]
            if r.pages.strip():
                try:
                    for item in r.pages.split(';'):
                        indices=[]
                        for span in item.split(','):
                            limits=[int(x.strip()) for x in span.split('-')]
                            if len(limits)==1:limits*=2
                            if len(limits)!=2 or not 1<=limits[0]<=limits[1]<=total:raise ValueError()
                            indices.extend(range(limits[0]-1,limits[1]))
                        groups.append(indices)
                except ValueError:raise OperationError('invalid_pages')
            else:
                try:count=int(r.page_count);assert count>0
                except (ValueError,AssertionError):raise OperationError('invalid_pages')
                groups=[range(n,min(n+count,total)) for n in range(0,total,count)]
            for n,indices in enumerate(groups,1):
                writer=PdfWriter()
                for i in indices:self.runner.check();writer.add_page(reader.pages[i])
                out=work/f'part-{n:03}.pdf';writer.write(out);writer.close();outputs.append(out)
        return outputs
    def media(self,r,infos,work):
        source=infos[0].path;video=infos[0].kind=='video';duration=self.duration(source)
        ext='mp4' if video else 'wav';out=work/('result.'+ext)
        if r.action in {'trim','remove_range','mute_range','split','extract_audio','add_audio','replace_audio','volume','speed','gif','rotate','fade_in','fade_out','transcribe'}:start,end=self.interval(r,duration)
        if r.action=='transcribe':
            from . import speech
            speech.resources()
            if r.speech_format not in {'txt','srt'}:raise OperationError('speech_format_invalid')
            audio=work/'speech.wav';out=work/('speech.'+r.speech_format)
            progress=self.runner.progress
            try:
                self.runner.progress=lambda f:progress(f*.05)
                self.ff([*self.input(source),'-ss',str(start),'-t',str(end-start),'-map','0:a:0','-vn','-ac','1','-ar','16000','-c:a','pcm_s16le',str(audio)],end-start)
                self.runner.progress=lambda f:progress(.05+.95*f)
                return [speech.transcribe(self.runner,audio,out,r.speech_language,end-start,offset=start if r.speech_format=='srt' else 0)]
            finally:self.runner.progress=progress
        if r.action=='add_subtitle':
            self.add_subtitle(r,source,infos[0],out,duration);return [out]
        if r.action=='trim':self.clip(source,out,start,end,video)
        elif r.action in {'split','remove_range','merge'}:
            if r.action=='split':
                length=seconds(r.part)
                if length<0.05:raise OperationError('invalid_time')
                count=max(1,math.ceil((end-start)/length-1e-9))
                if count>1000:raise OperationError('too_many_parts')
                ranges=[(source,start+n*length,min(start+(n+1)*length,end)) for n in range(count)]
            elif r.action=='remove_range':
                ranges=[(source,0,start)] if start>0 else []
                if end<duration:ranges.append((source,end,duration))
                if not ranges:raise OperationError('empty_result')
            else:
                ranges=[]
                for n,i in enumerate(infos):
                    pair=r.segments[n] if r.segments and n<len(r.segments) else ('0','')
                    a,b=self.interval(Request('trim',[i.path],work,start=pair[0],end=pair[1]),self.duration(i.path))
                    ranges.append((i.path,a,b))
            shape=None
            if video and r.action in {'merge','remove_range'}:
                stream=next(s for s in self.probe(source)['streams'] if s['codec_type']=='video')
                try:fps=float(Fraction(stream.get('avg_frame_rate','25')));assert 0<fps<=240
                except (ValueError,ZeroDivisionError,AssertionError):fps=25
                shape=((infos[0].width+1)//2*2,(infos[0].height+1)//2*2,fps)
            clips=[]
            for n,(path,a,b) in enumerate(ranges):
                self.runner.check();part=work/f'piece-{n:03}.{ext}';self.clip(path,part,a,b,video,shape);clips.append(part)
            if r.action=='split':return clips
            self.concat(clips,out,work)
        elif r.action=='extract_audio':
            if not infos[0].has_audio:raise OperationError('no_audio')
            out=work/'audio.mp3';clip=work/'selected.wav';self.clip(source,clip,start,end,False)
            produced=self.runner.convert(core.detect(clip),'mp3',work/'audio');shutil.copyfile(produced,out)
        elif r.action in {'gif','rotate'}:
            selected=work/'selected.mp4';self.clip(source,selected,start,end,True)
            if r.action=='gif':
                out=work/'animation.gif';product=self.runner.convert(core.detect(selected),'gif',work/'gif');shutil.copyfile(product,out)
            else:
                rotation={'90':'transpose=1','180':'hflip,vflip','270':'transpose=2'}.get(r.factor)
                if not rotation:raise OperationError('invalid_factor')
                self.ff([*self.input(selected),'-vf',rotation,'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','copy',str(out)],end-start)
        elif r.action=='speed' and video:
            try:factor=float(str(r.factor).replace(',','.'));assert math.isfinite(factor) and .5<=factor<=2
            except (ValueError,AssertionError):raise OperationError('invalid_factor')
            parts=[]
            if start>0:
                before=work/'before.mp4';self.clip(source,before,0,start,True);parts.append(before)
            middle=work/'middle.mp4';self.clip(source,middle,start,end,True)
            changed=work/'changed.mp4';args=[*self.input(middle),'-vf',f'setpts=(PTS-STARTPTS)/{factor}','-c:v','libx264','-crf','18','-pix_fmt','yuv420p']
            if infos[0].has_audio:args+=['-af',f'atempo={factor}','-c:a','aac']
            self.ff([*args,'-t',str((end-start)/factor),str(changed)],(end-start)/factor);parts.append(changed)
            if end<duration:
                after=work/'after.mp4';self.clip(source,after,end,duration,True);parts.append(after)
            self.concat(parts,out,work)
        elif r.action=='frame':
            position=seconds(r.start)
            if position>=duration:raise OperationError('invalid_range')
            out=work/'frame.png';self.ff([*self.input(source),'-ss',str(position),'-frames:v','1',str(out)])
            if not out.exists():raise OperationError('range_too_short')
        elif r.action=='mute':
            self.ff([*self.input(source),'-map','0:v:0','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(out)],duration)
        elif r.action in {'add_audio','replace_audio'}:
            audio=Path(r.audio)
            if not audio.is_file() or core.detect(audio).kind!='audio':raise OperationError('choose_audio')
            audio_duration=self.duration(audio)
            a,b=self.interval(Request('trim',[audio],work,start=r.audio_start,end=r.audio_end),audio_duration)
            delay=round(start*1000)
            take=min(b-a,end-start)
            filt=f'[1:a]atrim=start={a}:end={a+take},asetpts=PTS-STARTPTS,adelay={delay}:all=1,apad[new];'
            if infos[0].has_audio:
                if r.action=='replace_audio':filt+=f"[0:a]volume=0:enable='between(t,{start},{end})'[base];";base='base'
                else:base='0:a'
                filt+=f'[{base}][new]amix=inputs=2:duration=first:normalize=0[a]'
            else:filt+='[new]anull[a]'
            self.ff([*self.input(source),*self.input(audio),'-filter_complex',filt,'-map','0:v:0','-map','[a]','-t',str(duration),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','aac',str(out)],duration)
        else:
            if not infos[0].has_audio:raise OperationError('no_audio')
            if r.action=='mute_range':filt=f"volume=0:enable='between(t,{start},{end})'"
            elif r.action in {'fade_in','fade_out'}:
                direction='in' if r.action=='fade_in' else 'out'
                filt=f"afade=t={direction}:st={start}:d={end-start}:enable='between(t,{start},{end})'"
            else:
                try:factor=float(str(r.factor).replace(',','.'));assert math.isfinite(factor)
                except (ValueError,AssertionError):raise OperationError('invalid_factor')
                if r.action=='volume':
                    if not 0<=factor<=3:raise OperationError('invalid_factor')
                    filt=f"volume={factor}:enable='between(t,{start},{end})'"
                elif r.action=='speed':
                    if not .5<=factor<=2:raise OperationError('invalid_factor')
                    mid=work/'speed-mid.wav'
                    self.ff(['-ss',str(start),'-t',str(end-start),*self.input(source),'-vn','-af',f'atempo={factor}','-c:a','pcm_s16le','-ar','48000','-ac','2',str(mid)],end-start)
                    parts=[]
                    if start>0:
                        before=work/'speed-before.wav';self.clip(source,before,0,start,False);parts.append(before)
                    parts.append(mid)
                    if end<duration:
                        after=work/'speed-after.wav';self.clip(source,after,end,duration,False);parts.append(after)
                    self.concat(parts,out,work);return [out]
                else:raise OperationError('invalid_action')
            args=[*self.input(source),'-af',filt]
            if video:args+=['-map','0:v:0','-map','0:a:0','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','aac']
            else:args+=['-vn','-c:a','pcm_s16le']
            self.ff([*args,str(out)],duration)
        return [out]
    def execute_many(self,r,reference=None):
        if not r.files:raise OperationError('choose_file')
        if r.action=='merge':
            selected=[];issues=[];indices=[];kind=None
            if reference:
                info=core.detect(reference);kind=info.kind if info.kind in {'audio','video'} else 'document'
            for index,path in enumerate(r.files):
                self.runner.check()
                try:
                    info=core.detect(path);candidate=info.kind if info.kind in {'audio','video'} else 'document'
                    if 'merge' not in actions(info):raise OperationError('invalid_action')
                    if kind is None:kind=candidate
                    if candidate!=kind:raise OperationError('same_kind')
                    selected.append(path);indices.append(index)
                except core.Cancelled:raise
                except Exception as error:issues.append((Path(path),error))
            try:return self.execute(replace(r,files=selected,segments=[r.segments[i] for i in indices] if r.segments else None)),issues
            except core.Cancelled:raise
            except Exception as error:issues.append((Path(reference or r.files[0]),error));return [],issues
        outputs=[];issues=[];progress=self.runner.progress
        try:
            for index,path in enumerate(r.files):
                self.runner.check()
                self.runner.progress=lambda value,i=index:progress((i+value)/len(r.files))
                try:outputs.extend(self.execute(replace(r,files=[path])))
                except core.Cancelled:raise
                except Exception as error:issues.append((Path(path),error))
                progress((index+1)/len(r.files))
        finally:self.runner.progress=progress
        return outputs,issues

    def execute(self,r):
        if not r.files:raise OperationError('choose_file')
        infos=[core.detect(p) for p in r.files]
        if r.action not in actions(infos[0]):raise OperationError('invalid_action')
        if r.action=='merge':
            if len(infos)<2:raise OperationError('need_two')
            kinds={i.kind if i.kind in {'audio','video'} else 'document' for i in infos}
            if len(kinds)!=1:raise OperationError('same_kind')
        else:infos=infos[:1]
        output=Path(r.output).expanduser().resolve();output.mkdir(parents=True,exist_ok=True)
        published=[]
        with tempfile.TemporaryDirectory(prefix='.islem-',dir=output) as tmp:
            work=Path(tmp)
            if r.action in {'subtitle_text','subtitle_restore'}:
                from . import subtitles
                product=work/('result.txt' if r.action=='subtitle_text' else 'result.srt')
                if r.action=='subtitle_text':content=subtitles.export_text(infos[0].path)
                else:
                    if not r.audio:raise OperationError('subtitle_original_required')
                    content=subtitles.translated_srt(infos[0].path,Path(r.audio))
                product.write_text(content,encoding='utf-8');products=[product]
            else:
                products=self.media(r,infos,work) if infos[0].kind in {'video','audio'} else self.document(r,infos,work)
                if infos[0].kind=='audio':products=self.keep_audio_format(products,infos[0],work)
            try:
                for number,product in enumerate(products,1):
                    self.runner.check()
                    if not product.is_file() or not product.stat().st_size:raise OperationError('empty_result')
                    names={'tr':{'trim':'kesit','remove_range':'aralik-cikarildi','split':'parca','merge':'birlesik','mute_range':'aralik-sessiz','mute':'sessiz','extract_audio':'ses','add_audio':'ses-eklendi','replace_audio':'ses-degisti','frame':'kare','gif':'animasyon','rotate':'donduruldu','speed':'hiz','volume':'ses-duzeyi','fade_in':'ses-yukselme','fade_out':'ses-azalma','transcribe':'konusma-metni','add_subtitle':'altyazili'},'ku':{'trim':'beş','remove_range':'navber-rakirî','split':'parçe','merge':'yekbûyî','mute_range':'navber-bêdeng','mute':'bêdeng','extract_audio':'deng','add_audio':'deng-zêdekirî','replace_audio':'deng-guhertî','frame':'çarçove','gif':'anîmasyon','rotate':'zivirandî','speed':'lez','volume':'asta-dengê','fade_in':'deng-bilind','fade_out':'deng-kêm','transcribe':'axaftin-nivîs','add_subtitle':'bi-binnivîs'}}
                    name={'subtitle_text':'altyazi-metin','subtitle_restore':'cevrilmis-altyazi'}.get(r.action) or names.get(r.language,names['tr'])[r.action]
                    stem=infos[0].path.stem+'-'+name+(f'-{number:03}' if len(products)>1 else '')
                    for collision in range(10000):
                        dest=output/(stem+(f' ({collision})' if collision else '')+product.suffix)
                        try:
                            with dest.open('xb') as dst:
                                published.append(dest)
                                with product.open('rb') as src:shutil.copyfileobj(src,dst)
                            break
                        except FileExistsError:continue
                    else:raise OperationError('name_conflict')
                self.runner.check()
            except BaseException:
                for p in published:p.unlink(missing_ok=True)
                raise
        return published
