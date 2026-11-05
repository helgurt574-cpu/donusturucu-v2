"""Tools added with the new interface: watermark removal, sound cleaning, shrinking,
PDF page tools, pictures, and the short samples used by previews. Everything runs
locally with FFmpeg, pdftoppm and pypdf; originals are never changed."""
from __future__ import annotations
from pathlib import Path
import json,math,shutil,struct,tempfile
from . import core,runtime
from .operations import Editor,OperationError,seconds

IMAGE_FORMATS=['jpg','png','webp','bmp','pdf']
PDF_IMAGE=['png','jpg']

# ---------------------------------------------------------------- detection
def detect_image(path):
    """Still pictures, which the converter itself leaves out."""
    path=Path(path).expanduser().resolve()
    with path.open('rb') as f:head=f.read(32)
    fmt=None
    if head.startswith(b'\x89PNG'):fmt='png'
    elif head[:3]==b'\xff\xd8\xff':fmt='jpg'
    elif head[:4]==b'RIFF' and head[8:12]==b'WEBP':fmt='webp'
    elif head[:2]==b'BM':fmt='bmp'
    elif head[:4] in (b'II*\x00',b'MM\x00*'):fmt='tiff'
    elif head[4:12] in (b'ftypheic',b'ftypheix',b'ftypmif1',b'ftypavif'):fmt='heic' if b'avif' not in head[4:12] else 'avif'
    if not fmt:return None
    w,h=image_size(path)
    return core.FileInfo(path,'image',fmt,0,False,w,h)

def detect(path):
    try:
        info=core.detect(path)
    except core.ConversionError as error:
        if error.code!='unsupported':raise
        info=detect_image(path)
        if info is None:raise
    return info

def probe(path):
    p=core._capture(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_format','-show_streams','-of','json',str(path)],timeout=60)
    if p.returncode:raise OperationError('invalid_media')
    return json.loads(p.stdout)

def image_size(path):
    try:
        s=next(s for s in probe(path)['streams'] if s.get('codec_type')=='video')
        return int(s.get('width',0)),int(s.get('height',0))
    except Exception:return 0,0

def shown_size(info):
    """Width and height as players show them: phone videos store portrait as turned landscape."""
    w,h=info.width,info.height
    try:
        for s in probe(info.path)['streams']:
            if s.get('codec_type')!='video':continue
            rot=0
            for side in s.get('side_data_list',[]) or []:
                if 'rotation' in side:rot=int(side['rotation'])
            rot=rot or int(s.get('tags',{}).get('rotate',0) or 0)
            if abs(rot)%180==90:w,h=h,w
            break
    except Exception:pass
    return w,h

def actions(info):
    """New tools offered for a file (the classic ones come from operations.actions)."""
    if info.kind=='video':return ['watermark']+(['denoise'] if info.has_audio else [])+['compress']
    if info.kind=='audio':return ['denoise']
    if info.kind=='pdf':return ['watermark','compress','pages','pdf_rotate']
    if info.kind=='image':return ['watermark','edit','images_pdf','ocr_image']
    return []

def convert_targets(info):
    if info.kind=='image':return list(IMAGE_FORMATS)
    targets=core.targets(info)
    if info.kind=='pdf':targets=targets+PDF_IMAGE
    return targets

# ---------------------------------------------------------------- filters
def regions(text):
    out=[]
    for part in (text or '').split(';'):
        v=part.strip().split(',')
        if len(v)!=4:continue
        try:r=[max(0.0,min(1.0,float(x))) for x in v]
        except ValueError:continue
        if r[2]>0.002 and r[3]>0.002:out.append(r)
    return out

def region_text(items):return ';'.join(','.join(f'{x:.5f}' for x in r) for r in items)

def logo_filter(items,width,height,mode):
    """delogo needs a border around the area, so the frame is widened by repeating its edges first."""
    if not items:raise OperationError('watermark_area')
    if width<8 or height<8:raise OperationError('invalid_media')
    blur=mode=='blur';parts=[] if blur else ['pad=iw+4:ih+4:2:2,fillborders=left=2:right=2:top=2:bottom=2:mode=smear']
    graph=''
    for i,r in enumerate(items):
        x=int(math.floor(r[0]*width));y=int(math.floor(r[1]*height));w=int(math.ceil(r[2]*width));h=int(math.ceil(r[3]*height))
        x=max(0,min(width-4,x));y=max(0,min(height-4,y));w=max(4,min(width-x,w));h=max(4,min(height-y,h))
        if blur:
            radius=max(1,min(min(w,h)//2-1,24));chroma=max(0,min(min(w,h)//4-1,12))
            src='' if i==0 else f'[v{i}]'
            graph+=(';' if i else '')+f'{src}split[m{i}][c{i}];[c{i}]crop={w}:{h}:{x}:{y},boxblur=luma_radius={radius}:luma_power=3:chroma_radius={chroma}:chroma_power=3[b{i}];[m{i}][b{i}]overlay={x}:{y}'
            if i<len(items)-1:graph+=f'[v{i+1}]'
        else:parts.append(f'delogo=x={x+2}:y={y+2}:w={w}:h={h}')
    if blur:return graph
    parts.append('crop=iw-4:ih-4:2:2');return ','.join(parts)

def clean_chain(opts):
    level=int(opts.get('level','2'));f=[]
    if opts.get('hum','1')=='1':f+=[f'highpass=f={100 if level==3 else 80}','bandreject=f=100:width_type=h:w=10']
    if opts.get('clicks','1')=='1':
        f.append('adeclick=w=55:o=75:t='+('4' if level==1 else '1.5' if level==3 else '2.5'))
        if level>1:f.append('adeclip')
    if opts.get('hiss','1')=='1':f.append('afftdn=nr='+('10' if level==1 else '28' if level==3 else '18')+':nf='+('-30' if level==3 else '-40')+':tn=1')
    if opts.get('voice','0')=='1':f+=['lowpass=f=9000','dynaudnorm=f=150:g=15']
    if opts.get('loud','1')=='1':f.append('loudnorm=I=-16:TP=-1.5:LRA=11')
    if not f:raise OperationError('clean_nothing')
    return ','.join(f)

# ---------------------------------------------------------------- engine
SLUGS={'watermark':'filigransiz','denoise':'temiz','compress':'kucuk','pages':'sayfalar','pdf_rotate':'donduruldu','edit':'duzenlendi','images_pdf':'fotograflar','ocr_image':'metin','convert_image':'donusturuldu','pdf_images':'sayfa'}

class Studio:
    def __init__(self,runner=None):
        self.runner=runner or core.Runner();self.editor=Editor(self.runner)
    def ff(self,args,duration=0):self.editor.ff(args,duration)
    def inp(self,path):return ['-protocol_whitelist','file,pipe','-i',str(path)]

    # -- publish
    def publish(self,products,source,action,output):
        output=Path(output).expanduser().resolve();output.mkdir(parents=True,exist_ok=True);published=[]
        try:
            for number,product in enumerate(products,1):
                self.runner.check()
                if not product.is_file() or not product.stat().st_size:raise OperationError('empty_result')
                stem=Path(source).stem+'-'+SLUGS.get(action,action)+(f'-{number:03}' if len(products)>1 else '')
                for collision in range(10000):
                    dest=output/(stem+(f' ({collision})' if collision else '')+product.suffix)
                    try:
                        with dest.open('xb') as dst:
                            published.append(dest)
                            with product.open('rb') as src:shutil.copyfileobj(src,dst)
                        break
                    except FileExistsError:continue
                else:raise OperationError('name_conflict')
        except BaseException:
            for p in published:p.unlink(missing_ok=True)
            raise
        return published

    def run(self,info,action,opts,output,others=()):
        """Runs one new tool and publishes the result next to the others in output."""
        output=Path(output).expanduser().resolve();output.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.studio-',dir=output) as tmp:
            products=self.make(info,action,opts,Path(tmp),others)
            return self.publish(products,info.path,action,output)

    def make(self,info,action,opts,work,others=()):
        k=info.kind
        if action=='watermark':
            if k=='pdf':return [self.pdf_watermark(info.path,opts,work)]
            if k=='image':return [self.image_watermark(info,opts,work)]
            return [self.video_watermark(info,opts,work)]
        if action=='denoise':return self.denoise(info,opts,work)
        if action=='compress':return [self.pdf_compress(info.path,int(opts.get('level','2')),work)] if k=='pdf' else [self.video_compress(info,opts,work)]
        if action=='pages':return [self.pdf_pages(info.path,opts.get('spec','1'),opts.get('keep','1')!='0',work)]
        if action=='pdf_rotate':return [self.pdf_rotate(info.path,int(opts.get('angle','90')),opts.get('spec',''),work)]
        if action=='edit':return [self.image_convert(info,keep_ext(info),opts,work)]
        if action=='convert_image':return [self.image_convert(info,opts.get('format','png'),opts,work)]
        if action=='pdf_images':return self.pdf_to_images(info.path,opts.get('format','png'),int(opts.get('dpi','150')),work)
        if action=='images_pdf':return [self.images_pdf([info.path,*[Path(p) for p in others]],work)]
        if action=='ocr_image':return [self.image_ocr(info,opts,work)]
        raise OperationError('invalid_action')

    # -- video and sound
    def video_watermark(self,info,opts,work):
        w,h=shown_size(info);out=work/'clean.mp4'
        self.ff([*self.inp(info.path),'-map','0:v:0','-map','0:a?','-vf',logo_filter(regions(opts.get('regions','')),w,h,opts.get('mode','fill')),'-c:v','libx264','-preset','fast','-crf',crf(opts),'-pix_fmt','yuv420p','-c:a','aac','-sn','-dn',str(out)],info.duration)
        return out
    def denoise(self,info,opts,work):
        if not info.has_audio:raise OperationError('no_audio')
        chain=clean_chain(opts)
        if info.kind=='audio':
            out=work/'clean.wav';self.ff([*self.inp(info.path),'-map','0:a:0','-vn','-af',chain,'-c:a','pcm_s16le','-ar','48000',str(out)],info.duration)
            return self.editor.keep_audio_format([out],info,work)
        out=work/'clean.mp4';base=[*self.inp(info.path),'-map','0:v:0','-map','0:a:0','-af',chain,'-c:a','aac','-b:a','192k','-ar','48000','-sn','-dn']
        try:self.ff([*base,'-c:v','copy',str(out)],info.duration)
        except core.Cancelled:raise
        except core.ConversionError:
            # Some pictures cannot travel in MP4 untouched; encode them then.
            self.ff([*base,'-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p',str(out)],info.duration)
        return [out]
    def video_compress(self,info,opts,work):
        level=int(opts.get('level','2'));limit=int(opts.get('height','0') or 0);out=work/'small.mp4'
        scale='null' if limit<=0 else f"scale=w='if(gt(iw,ih),-2,min(iw,{limit}))':h='if(gt(iw,ih),min(ih,{limit}),-2)'"
        self.ff([*self.inp(info.path),'-map','0:v:0','-map','0:a?','-vf',scale,'-c:v','libx264','-preset','faster','-crf',{1:'23',3:'31'}.get(level,'27'),'-pix_fmt','yuv420p','-c:a','aac','-b:a',{1:'128k',3:'64k'}.get(level,'96k'),'-movflags','+faststart','-sn','-dn',str(out)],info.duration)
        return out

    # -- pictures
    def image_filter(self,opts):
        f=[];angle=int(opts.get('angle','0') or 0);scale=int(opts.get('scale','100') or 100)
        if scale!=100:f.append(f'scale=trunc(iw*{scale}/100/2)*2:trunc(ih*{scale}/100/2)*2:flags=lanczos')
        if angle==90:f.append('transpose=1')
        elif angle==270:f.append('transpose=2')
        elif angle==180:f.append('hflip,vflip')
        if opts.get('flip','0')=='1':f.append('hflip')
        if opts.get('gray','0')=='1':f.append('hue=s=0')
        return ','.join(f) or 'null'
    def still_png(self,path,work,name='picture',vf='null'):
        out=work/(name+'.png');self.ff([*self.inp(path),'-frames:v','1','-vf',vf,str(out)]);return out
    def image_convert(self,info,fmt,opts,work):
        fmt=fmt.lower();vf=self.image_filter(opts);q={'1':95,'3':70}.get(opts.get('q','2'),85)
        if fmt=='pdf':return self.images_pdf([self.still_png(info.path,work,'page',vf)],work)
        out=work/('picture.'+fmt);args=[*self.inp(info.path),'-frames:v','1','-vf',vf]
        if fmt=='jpg':args+=['-q:v',str(max(2,min(31,round((100-q)/6)+2))),'-pix_fmt','yuvj444p']
        elif fmt=='webp':args+=['-c:v','libwebp','-quality',str(q)]
        elif fmt=='bmp':args+=['-pix_fmt','bgr24']
        self.ff([*args,str(out)]);return out
    def image_watermark(self,info,opts,work):
        upright=self.still_png(info.path,work,'upright');w,h=image_size(upright)
        out=work/'clean.png';self.ff([*self.inp(upright),'-frames:v','1','-vf',logo_filter(regions(opts.get('regions','')),w,h,opts.get('mode','fill')),str(out)])
        ext=keep_ext(info)
        if ext=='png':return out
        final=work/'final';final.mkdir(exist_ok=True)
        return self.image_convert(core.FileInfo(out,'image','png',0,False,w,h),ext,{'q':'1'},final)
    def images_pdf(self,pictures,work):
        """Each picture becomes one A4-wide page (written directly, no extra libraries)."""
        pages=[]
        for n,picture in enumerate(pictures):
            self.runner.check();jpg=work/f'p{n}.jpg'
            self.ff([*self.inp(picture),'-frames:v','1','-vf',"scale='min(2400,iw)':-2,format=yuvj420p",'-q:v','3',str(jpg)])
            w,h=image_size(jpg)
            if not w:raise OperationError('invalid_media')
            pages.append((jpg.read_bytes(),w,h))
        out=work/'pictures.pdf';write_image_pdf(pages,out);return out
    def image_ocr(self,info,opts,work):
        from . import ocr
        png=self.still_png(info.path,work,'ocr')
        text=ocr.image_text(self.runner,png,opts.get('lang','tur+eng'))
        if not text.strip():raise OperationError('no_text')
        txt=work/(info.path.stem+'.txt');txt.write_text(text+'\n',encoding='utf-8')
        target=opts.get('format','txt').lower()
        if target=='txt':return txt
        return self.runner.convert(core.detect(txt),target,work/'converted')

    # -- PDF pages
    def reader(self,path):
        from pypdf import PdfReader
        r=PdfReader(str(path))
        if r.is_encrypted:
            try:r.decrypt('')
            except Exception:raise core.ConversionError('encrypted')
        return r
    def pdf_pages(self,path,spec,keep,work):
        from pypdf import PdfWriter
        r=self.reader(path);n=len(r.pages);chosen=parse_pages(spec,n);w=PdfWriter()
        if keep:
            for i in chosen:w.add_page(r.pages[i])
        else:
            drop=set(chosen)
            if len(drop)>=n:raise OperationError('page_range')
            for i in range(n):
                if i not in drop:w.add_page(r.pages[i])
        out=work/'pages.pdf'
        with out.open('wb') as f:w.write(f)
        return out
    def pdf_rotate(self,path,angle,spec,work):
        from pypdf import PdfWriter
        r=self.reader(path);n=len(r.pages);chosen=set(parse_pages(spec,n)) if spec.strip() else set(range(n));w=PdfWriter()
        for i,page in enumerate(r.pages):
            if i in chosen:page.rotate(angle)
            w.add_page(page)
        out=work/'rotated.pdf'
        with out.open('wb') as f:w.write(f)
        return out
    def pdf_to_images(self,path,fmt,dpi,work):
        folder=work/'pages';folder.mkdir();src=runtime.ascii_path(path,work)
        self.runner.run(['pdftoppm','-r',str(dpi),'-png' if fmt=='png' else '-jpeg',*(['-jpegopt','quality=92'] if fmt=='jpg' else []),str(src),str(folder/'page')],timeout=1800)
        out=sorted(folder.iterdir())
        if not out:raise OperationError('empty_result')
        return out
    def pdf_compress(self,path,level,work):
        """Large pictures inside the PDF are made smaller JPEGs; text stays text."""
        from pypdf import PdfWriter
        from pypdf.generic import NameObject,NumberObject
        max_side={1:2400,3:1100}.get(level,1600);quality={1:3,3:9}.get(level,5)
        w=PdfWriter(clone_from=str(path));seen=set()
        def shrink(resources,depth=0):
            if resources is None or depth>4:return
            xobjects=resources.get('/XObject')
            if xobjects is None:return
            xobjects=xobjects.get_object()
            for name in list(xobjects.keys()):
                self.runner.check()
                x=xobjects[name].get_object()
                if id(x) in seen:continue
                seen.add(id(x))
                if x.get('/Subtype')=='/Form':shrink(x.get('/Resources'),depth+1);continue
                if x.get('/Subtype')!='/Image' or '/SMask' in x or '/Mask' in x or x.get('/ImageMask'):continue
                if int(x.get('/BitsPerComponent',8))!=8:continue
                raw=x._data or b''
                if len(raw)<60000:continue
                filters=x.get('/Filter');filters=[filters] if not isinstance(filters,list) else list(filters)
                filters=[str(f) for f in filters]
                width,height=int(x['/Width']),int(x['/Height']);space=str(x.get('/ColorSpace',''))
                src=work/f'img{len(seen)}';out=work/f'img{len(seen)}.jpg'
                if filters==['/DCTDecode']:src=src.with_suffix('.jpg');src.write_bytes(raw);inp=self.inp(src)
                elif space in ('/DeviceRGB','/DeviceGray') and all(f in ('/FlateDecode','/LZWDecode','/RunLengthDecode') for f in filters):
                    try:pixels=x.get_data()
                    except Exception:continue
                    channels=3 if space=='/DeviceRGB' else 1
                    if len(pixels)<width*height*channels:continue
                    src=src.with_suffix('.raw');src.write_bytes(pixels[:width*height*channels])
                    inp=['-f','rawvideo','-pix_fmt','rgb24' if channels==3 else 'gray','-s',f'{width}x{height}',*self.inp(src)]
                else:continue
                scale=f"scale='min({max_side},iw)':'min({max_side},ih)':force_original_aspect_ratio=decrease"
                try:self.ff([*inp,'-frames:v','1','-vf',scale,'-q:v',str(quality),str(out)])
                except core.Cancelled:raise
                except Exception:continue
                data=out.read_bytes()
                if len(data)>=len(raw)*0.9:continue
                nw,nh=image_size(out)
                if not nw:continue
                x._data=data;x[NameObject('/Filter')]=NameObject('/DCTDecode')
                if '/DecodeParms' in x:del x['/DecodeParms']
                x[NameObject('/Width')]=NumberObject(nw);x[NameObject('/Height')]=NumberObject(nh)
                if space not in ('/DeviceRGB','/DeviceGray'):x[NameObject('/ColorSpace')]=NameObject('/DeviceRGB')
        for page in w.pages:shrink(page.get('/Resources'))
        for page in w.pages:
            try:page.compress_content_streams()
            except Exception:pass
        try:w.compress_identical_objects()
        except Exception:pass
        out=work/'compressed.pdf'
        with out.open('wb') as f:w.write(f)
        if out.stat().st_size>=Path(path).stat().st_size:shutil.copyfile(path,out)
        return out

    def pdf_watermark(self,path,opts,work):
        from . import pdf_watermark
        def colour(page,region):
            try:
                return ring_colour(self.render_page(path,page,500,work/'ring',ppm=True),region)
            except Exception:return (1.0,1.0,1.0)
        out,removed=pdf_watermark.clean(path,work/'clean.pdf',opts.get('auto','1')=='1',opts.get('repeated','0')=='1',opts.get('keyword',''),regions(opts.get('regions','')),colour,self.runner.check)
        if not removed:raise OperationError('watermark_none')
        return out

    # -- preview helpers
    def still(self,path,at,max_width,out):
        self.ff(['-ss',f'{max(0,at):.3f}',*self.inp(path),'-frames:v','1','-vf',f"scale='min({max_width},iw)':-2",str(out)]);return out
    def sample(self,info,start,length,work):
        start=max(0.0,min(start,max(0.0,info.duration-0.2)));length=max(0.5,min(length,info.duration-start))
        if info.kind=='video':
            out=work/'sample.mp4';self.ff(['-ss',f'{start:.3f}',*self.inp(info.path),'-t',f'{length:.3f}','-map','0:v:0','-map','0:a:0?','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-sn','-dn',str(out)],length)
        else:
            out=work/'sample.wav';self.ff(['-ss',f'{start:.3f}',*self.inp(info.path),'-t',f'{length:.3f}','-map','0:a:0','-vn','-c:a','pcm_s16le','-ar','48000','-ac','2',str(out)],length)
        return out
    def peaks(self,path,bars=90):
        raw=Path(tempfile.mkdtemp(prefix='donustur-wave-'))/'wave.raw'
        try:
            self.ff([*self.inp(path),'-vn','-ac','1','-ar','2000','-f','s16le',str(raw)])
            data=raw.read_bytes();count=len(data)//2
            if count<bars:return []
            values=struct.unpack('<%dh'%count,data[:count*2]);out=[]
            for b in range(bars):
                part=values[count*b//bars:count*(b+1)//bars];out.append(math.sqrt(sum(v*v for v in part)/max(1,len(part))))
            top=max(out) or 1;return [(v/top)**0.7 for v in out]
        finally:shutil.rmtree(raw.parent,ignore_errors=True)
    def render_page(self,path,index,width,folder,ppm=False):
        folder.mkdir(parents=True,exist_ok=True);src=runtime.ascii_path(path,folder);prefix=folder/f'page{index}-{width}'
        self.runner.run(['pdftoppm','-f',str(index+1),'-l',str(index+1),'-scale-to-x',str(width),'-scale-to-y','-1',*([] if ppm else ['-png']),'-singlefile',str(src),str(prefix)],timeout=300)
        return prefix.with_suffix('.ppm' if ppm else '.png')

def crf(opts):return {'high':'18','small':'28'}.get(opts.get('quality',''),'20')
def keep_ext(info):return 'jpg' if info.fmt=='jpg' else 'webp' if info.fmt=='webp' else 'png'

def parse_pages(spec,count):
    out=[]
    for part in spec.replace(' ',',').replace(';',',').split(','):
        part=part.strip()
        if not part:continue
        try:
            if '-' in part:
                a,b=part.split('-',1);a=int(a) if a.strip() else 1;b=int(b) if b.strip() else count
            else:a=b=int(part)
        except ValueError:raise OperationError('page_range')
        if not (1<=a<=count and 1<=b<=count):raise OperationError('page_range')
        out+=list(range(a-1,b)) if a<=b else list(range(a-1,b-2,-1))
    if not out:raise OperationError('page_range')
    return out

def read_ppm(path):
    data=Path(path).read_bytes();fields=[];i=0
    while len(fields)<4:
        while data[i:i+1].isspace():i+=1
        if data[i:i+1]==b'#':
            while data[i:i+1] not in (b'\n',b''):i+=1
            continue
        j=i
        while not data[j:j+1].isspace():j+=1
        fields.append(data[i:j]);i=j
    if fields[0]!=b'P6':raise ValueError('not P6')
    return int(fields[1]),int(fields[2]),data[i+1:]

def ring_colour(ppm,r):
    """Median colour of a thin ring just outside a marked area of a rendered page."""
    W,H,px=read_ppm(ppm)
    x0,y0=int(r[0]*W)-3,int(r[1]*H)-3;x1,y1=int((r[0]+r[2])*W)+3,int((r[1]+r[3])*H)+3;rs,gs,bs=[],[],[]
    def add(x,y):
        if 0<=x<W and 0<=y<H:
            i=(y*W+x)*3;rs.append(px[i]);gs.append(px[i+1]);bs.append(px[i+2])
    for x in range(x0,x1+1):add(x,y0);add(x,y1)
    for y in range(y0,y1+1):add(x0,y);add(x1,y)
    if not rs:return (1.0,1.0,1.0)
    m=len(rs)//2;return (sorted(rs)[m]/255,sorted(gs)[m]/255,sorted(bs)[m]/255)

def write_image_pdf(pages,out):
    """Minimal PDF: one JPEG (DCTDecode) per page, 595 pt wide."""
    objs=[None,None];kids=[]
    def add(b):objs.append(b);return len(objs)
    for data,w,h in pages:
        pw=595.0;ph=max(1.0,min(14400.0,pw*h/w))
        img=add(b'<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length %d >>\nstream\n'%(w,h,len(data))+data+b'\nendstream')
        content=f'q {pw:.2f} 0 0 {ph:.2f} 0 0 cm /Im0 Do Q'.encode()
        c=add(b'<< /Length %d >>\nstream\n'%len(content)+content+b'\nendstream')
        kids.append(add(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {pw:.2f} {ph:.2f}] /Resources << /XObject << /Im0 {img} 0 R >> >> /Contents {c} 0 R >>'.encode()))
    objs[0]=b'<< /Type /Catalog /Pages 2 0 R >>'
    objs[1]=f'<< /Type /Pages /Kids [{" ".join(f"{k} 0 R" for k in kids)}] /Count {len(kids)} >>'.encode()
    buf=bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n');offsets=[]
    for i,o in enumerate(objs,1):offsets.append(len(buf));buf+=f'{i} 0 obj\n'.encode()+o+b'\nendobj\n'
    xref=len(buf);buf+=f'xref\n0 {len(objs)+1}\n0000000000 65535 f \n'.encode()+''.join(f'{o:010d} 00000 n \n' for o in offsets).encode()
    buf+=f'trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    Path(out).write_bytes(bytes(buf))
