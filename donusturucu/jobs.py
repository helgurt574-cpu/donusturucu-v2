"""What the Start and Preview buttons do, shared by the GTK window and the web interface.
Nothing here touches a toolkit: results are file paths, texts and numbers."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import shutil
from . import core,studio_ops as so
from .operations import Editor,Request,OperationError,actions as classic_actions

NEW={'watermark','denoise','compress','pages','pdf_rotate','edit','images_pdf','ocr_image'}

def tr(ku,a,b):return b if ku else a
def clock(s):s=int(round(s or 0));return f'{s//3600}:{s//60%60:02}:{s%60:02}' if s>=3600 else f'{s//60}:{s%60:02}'
def size(b):
    for unit,div in (('GB',1<<30),('MB',1<<20),('KB',1<<10)):
        if b>=div:return f'{b/div:.1f} {unit}' if unit!='KB' else f'{b/div:.0f} KB'
    return f'{b} B'

def tools_for(info):
    out=['convert']+so.actions(info)
    if info.kind!='image':out+=[a for a in classic_actions(info) if a not in out]
    return out

def needs_other(action,batch):return action in ('add_audio','replace_audio','add_subtitle','subtitle_restore') or (action in ('merge','images_pdf') and not batch)

def request(action,opts,files,output,other,ku):
    o=opts
    return Request(action,[str(f) for f in files],output,start=o.get('start','0') or '0',end=o.get('end',''),part=o.get('part','60') or '60',page_count=o.get('page_count','1') or '1',
        audio=str(other.path) if other else '',factor=o.get('factor',{'rotate':'90','speed':'1.5','volume':'1.5'}.get(action,'1')),audio_start=o.get('audio_start','0') or '0',audio_end=o.get('audio_end',''),
        language='ku' if ku else 'tr',speech_language=o.get('speech_language','tr'),speech_format=o.get('speech_format','txt'),subtitle_mode=o.get('subtitle_mode','burn'))

def check(source,action,opts,other,batch):
    if action=='watermark' and source.kind!='pdf' and not so.regions(opts.get('regions','')):raise OperationError('watermark_area')
    if needs_other(action,batch) and other is None:raise OperationError('second_file')

def run(runner,targets,source,action,target,opts,conv,other,output,ku,log,error_text,status=lambda s:None):
    """Runs one job over one or more files; returns (outputs, failed count)."""
    outputs=[];failed=0;st=so.Studio(runner);ed=Editor(runner);progress=runner.progress
    if action in ('merge','images_pdf') and len(targets)>1:
        if action=='images_pdf':outputs+=st.run(targets[0],action,opts,output,[t.path for t in targets[1:] if t.kind=='image'])
        else:
            done,issues=ed.execute_many(request(action,opts,[t.path for t in targets],output,other,ku),reference=source.path);outputs+=done;failed+=len(issues)
            for path,err in issues:log(f'✗ {Path(path).name}: {error_text(err)}')
        return outputs,failed
    for n,info in enumerate(targets):
        runner.check();runner.progress=lambda v,n=n:progress((n+v)/len(targets))
        status((f'{n+1}/{len(targets)} · ' if len(targets)>1 else '')+info.path.name)
        try:
            made=[]
            if action=='convert':
                if info.kind=='image':made=st.run(info,'convert_image',{**opts,'format':target},output)
                elif info.kind=='pdf' and target in so.PDF_IMAGE:made=st.run(info,'pdf_images',{**opts,'format':target},output)
                elif target in so.convert_targets(info):runner.notes.clear();made=[runner.convert(info,target,output,conv)]
                else:raise OperationError('invalid_action')
            elif action in NEW:
                if action not in so.actions(info):raise OperationError('invalid_action')
                made=st.run(info,action,opts,output,[other.path] if other else [])
            else:
                files=[info.path]+([other.path] if action=='merge' and other else [])
                made=Editor(runner).execute(request(action,opts,files,output,other,ku))
            outputs+=made;log(f'✓ {info.path.name} → '+', '.join(Path(o).name for o in made))
        except core.Cancelled:raise
        except Exception as e:
            failed+=1;log(f'✗ {info.path.name}: {error_text(e)}')
            if getattr(e,'detail',''):log(str(e.detail)[-1500:])
    runner.progress=progress
    return outputs,failed

def preview(runner,info,action,target,opts,conv,other,page,work,ku,status=lambda s:None):
    """Makes a preview in work and describes it: kind is compare, image, audio, thumbs or text;
    pictures and media are file paths."""
    t=lambda a,b:tr(ku,a,b);st=so.Studio(runner);ed=Editor(runner);dur=info.duration;p={'action':action,'kind':None,'note':None}
    req=request(action,opts,[info.path],work/'unused',other,ku) if action not in NEW and action!='convert' else None
    if info.kind in ('video','audio'):
        if action=='frame':p.update(kind='image',after=st.still(info.path,so.seconds(req.start),1400,work/'frame.png'));return p
        if action in ('remove_range','split','merge'):
            start=so.seconds(req.start or '0');end=so.seconds(req.end) if req.end.strip() else dur;caps=[];at=[]
            if action=='merge':p.update(kind='text',text=f'{info.path.name} · {clock(dur)}\n+ {other.path.name} · {clock(other.duration)}',note=t('Toplam süre ≈ ','Dirêjahiya giştî ≈ ')+clock(dur+other.duration));return p
            if action=='remove_range':at=[max(0,start-1),min(dur-0.05,end+0.05)];caps=[t('Silinen bölümden önce · ','Berî beşê · ')+clock(start),t('Sonra devam · ','Paşê · ')+clock(end)];p['note']=t('Yeni süre ≈ ','Dirêjahiya nû ≈ ')+clock(dur-(end-start))
            else:
                part=max(0.05,so.seconds(req.part));n=int(-(-(end-start)//part));p['note']=f'{n} '+t('parça oluşacak.','parçe dê çêbin.')
                for i in range(min(n,8)):s=start+i*part;at.append(s);caps.append(f'{i+1}. {clock(s)}–{clock(min(end,s+part))}')
            if info.kind=='video':p.update(kind='thumbs',thumbs=[(st.still(info.path,x,480,work/f't{i}.png'),caps[i]) for i,x in enumerate(at)])
            else:p.update(kind='text',text='\n'.join(caps))
            return p
        length=10 if action=='denoise' else 6
        if action=='denoise':start=so.seconds(opts.get('at','0') or '0')
        elif action in ('convert','compress','watermark','mute','add_subtitle'):start=min(max(0,dur*0.1),max(0,dur-length))
        else:start=so.seconds(req.start or '0') if req else 0
        if action=='trim':length=min(8,(so.seconds(req.end) if req.end.strip() else dur)-start)
        status(t('Örnek parça hazırlanıyor…','Mînak tê amadekirin…'))
        sample=st.sample(info,start,length,work);sinfo=so.detect(sample)
        if action=='trim':result=sample
        else:
            out=work/'out';out.mkdir(exist_ok=True);status(t('Önizleme işleniyor…','Pêşdîtin tê kirin…'))
            if action=='convert':result=runner.convert(sinfo,target,out,conv)
            elif action in NEW:result=st.run(sinfo,action,opts,out)[0]
            else:
                s0=so.seconds(req.start or '0');e0=so.seconds(req.end) if req.end.strip() else None
                shifted=replace(req,files=[str(sample)],output=out,start=f'{max(0,s0-start):.3f}',end='' if e0 is None or e0-start>=sinfo.duration else f'{max(0.1,e0-start):.3f}')
                result=ed.execute(shifted)[0]
        result=Path(result);p.update(original=sample,result=result)
        if action in ('convert','compress'):
            rinfo=so.detect(result) if result.suffix!='.gif' else None
            est=result.stat().st_size/max(0.5,(rinfo.duration if rinfo and rinfo.duration else sinfo.duration))*dur
            p['note']=t('Tahmini çıktı boyutu ≈ ','Mezinahiya texmînî ≈ ')+size(int(est))+t(' (şu an ',' (niha ')+size(info.path.stat().st_size)+')'
        suffix=result.suffix.lower()
        if suffix=='.png':p.update(kind='image',after=result);return p
        if suffix=='.gif':p.update(kind='image',after=result);return p
        if info.kind=='audio' or action=='denoise' or suffix[1:] in core.AUDIO:
            p.update(kind='audio',peaks_a=st.peaks(sample,120),peaks_b=st.peaks(result,120))
            if action=='denoise':p['note']=t('10 saniyelik örnek: ikisini de dinleyip karşılaştır.','Mînaka 10 çirkeyan: herduyan guhdarî bike.')
            return p
        mid=min(1.0,sinfo.duration/2);p.update(kind='compare',before=st.still(sample,mid,1400,work/'a.png'),after=st.still(result,mid,1400,work/'b.png'));return p
    if info.kind=='pdf':
        if action=='convert' and target not in so.PDF_IMAGE:
            text=Path(runner.convert(info,'txt',work/'txt',core.Options(only_text=True))).read_text(encoding='utf-8',errors='replace')
            p.update(kind='text',text=text[:1500]+('…' if len(text)>1500 else ''),note=t('Çıktıya aktarılacak metnin başı.','Destpêka nivîsê.'));return p
        if action in ('split','merge'):
            outs=ed.execute(req if action=='split' else request(action,opts,[info.path,other.path],work/'unused',other,ku))
            p.update(kind='thumbs',thumbs=[(st.render_page(o,0,360,work/'r'),f'{i+1}. '+t('dosya','dosye')) for i,o in enumerate(outs[:8])],note=f'{len(outs)} PDF');return p
        outs=st.make(info,'pdf_images' if action=='convert' else action,{**opts,'format':target},work)
        if action=='convert':p.update(kind='thumbs',thumbs=[(o,t('Sayfa ','Rûpel ')+str(i+1)) for i,o in enumerate(outs[:8])],note=f'{len(outs)} '+t('resim oluşacak.','wêne dê çêbin.'));return p
        result=outs[0];n=len(st.reader(result).pages)
        if action in ('watermark','compress'):
            p.update(kind='compare',before=st.render_page(info.path,page,1100,work/'r0'),after=st.render_page(result,min(page,n-1),1100,work/'r1'))
            p['note']=t('Yeni boyut: ','Mezinahiya nû: ')+size(result.stat().st_size)+t(' (önce ',' (berê ')+size(info.path.stat().st_size)+')' if action=='compress' else t('Bu sayfada önce/sonra. Diğer sayfalara sayfa oklarıyla geçebilirsin.','Berê/paşê li vê rûpelê.')
            return p
        p.update(kind='thumbs',thumbs=[(st.render_page(result,i,360,work/'r'),t('Sayfa ','Rûpel ')+str(i+1)) for i in range(min(10,n))],note=t('Sonuç: ','Encam: ')+f'{n} '+t('sayfa','rûpel'));return p
    if info.kind=='image':
        outs=st.make(info,'convert_image' if action=='convert' else action,{**opts,'format':target},work,[other.path] if other else []);result=Path(outs[0])
        if result.suffix=='.pdf':
            n=len(st.reader(result).pages);p.update(kind='thumbs',thumbs=[(st.render_page(result,i,360,work/'r'),t('Sayfa ','Rûpel ')+str(i+1)) for i in range(min(8,n))],note=t('Boyut: ','Mezinahî: ')+size(result.stat().st_size));return p
        if result.suffix=='.txt' or action=='ocr_image':
            p.update(kind='text',text=result.read_text(encoding='utf-8',errors='replace')[:1500] if result.suffix=='.txt' else t('Metin dosyası oluşacak.','Pelê nivîsê dê çêbibe.'));return p
        after=st.still_png(result,work,'after');before=st.still_png(info.path,work,'before');w,h=so.image_size(after);bw,bh=so.image_size(before)
        p['note']=t('Boyut: ','Mezinahî: ')+size(result.stat().st_size)+t(' (önce ',' (berê ')+size(info.path.stat().st_size)+f') · {w}×{h}'
        same=bh and h and abs(w/h-bw/bh)<0.02
        p.update(kind='compare' if action=='watermark' or same else 'image',before=before,after=after);return p
    text=Path(runner.convert(info,'txt',work/'txt',core.Options(only_text=True))).read_text(encoding='utf-8',errors='replace') if info.fmt not in ('txt','srt') else info.path.read_text(encoding='utf-8',errors='replace')
    p.update(kind='text',text=text[:1500]+('…' if len(text)>1500 else ''));return p
