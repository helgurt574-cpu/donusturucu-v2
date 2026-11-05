"""Removes watermarks from PDF pages without turning them into pictures (same rules as Android).
Automatic: watermark annotations, content marked as a watermark artifact or optional-content
layer, and see-through text drawn at an angle. With a word: every text block or form holding
it. Optionally pictures/forms repeated on most pages. Marked areas are covered with the
colour around them."""
from __future__ import annotations
import math
from pathlib import Path

def normal(text):return ''.join(ch for ch in (text or '').lower().replace('İ','i').replace('I','ı') if not ch.isspace())

def _num(x):
    try:return float(x)
    except Exception:return 0.0

def _turned(operands):
    a,b=_num(operands[0]),_num(operands[1]);deg=abs(math.degrees(math.atan2(b,a)))%180
    if deg>90:deg=180-deg
    return 10<deg<80

class _Cleaner:
    def __init__(self,writer,auto,word,repeated,check):
        self.w=writer;self.auto=auto;self.word=word;self.repeated=repeated;self.check=check;self.removed=0;self.forms=set();self.maps={}

    def decode(self,operands,res,font):
        from pypdf.generic import ByteStringObject,TextStringObject,ArrayObject,DictionaryObject,NameObject
        decoder=None
        if res is not None and font is not None:
            key=(id(res),str(font))
            if key not in self.maps:
                try:
                    from pypdf._cmap import build_char_map
                    holder=DictionaryObject({NameObject('/Resources'):res})
                    _,_,encoding,cmap,_=build_char_map(str(font),200.0,holder)
                    self.maps[key]=(encoding,cmap)
                except Exception:self.maps[key]=None
            decoder=self.maps[key]
        def one(s):
            raw=s.original_bytes if hasattr(s,'original_bytes') else bytes(s)
            if decoder is None:return raw.decode('latin-1')
            encoding,cmap=decoder
            try:
                text=raw.decode(encoding,'surrogatepass') if isinstance(encoding,str) else ''.join(encoding.get(b,chr(b)) if isinstance(encoding.get(b,''),str) else chr(b) for b in raw)
                return ''.join(cmap.get(ch,ch) if isinstance(cmap.get(ch,ch),str) else ch for ch in text)
            except Exception:return raw.decode('latin-1')
        out=[]
        for o in operands:
            if isinstance(o,(ByteStringObject,TextStringObject)):out.append(one(o))
            elif isinstance(o,ArrayObject):out.extend(one(x) for x in o if isinstance(x,(ByteStringObject,TextStringObject)))
        return ''.join(out)

    def marked(self,operands,res):
        from pypdf.generic import DictionaryObject,NameObject
        if not operands:return False
        tag=operands[0];props=operands[1] if len(operands)>1 else None
        if isinstance(tag,NameObject) and 'watermark' in str(tag).lower():return True
        d=None
        if isinstance(props,DictionaryObject):d=props
        elif isinstance(props,NameObject) and res is not None and '/Properties' in res:
            try:d=res['/Properties'].get_object()[props].get_object()
            except Exception:d=None
        if d is None:return False
        if str(d.get('/Subtype',''))=='/Watermark':return True
        name=str(d.get('/Name','')).lower()
        return 'watermark' in name or 'filigran' in name

    def xobject_key(self,res,name):
        try:
            ref=res['/XObject'].get_object().raw_get(name)
            return (ref.idnum,ref.generation) if hasattr(ref,'idnum') else id(ref)
        except Exception:return None

    def drop_xobject(self,res,name,depth):
        from pypdf.generic import ContentStream
        key=self.xobject_key(res,name)
        if key is None:return False
        if key in self.repeated:return True
        try:x=res['/XObject'].get_object()[name].get_object()
        except Exception:return False
        if x.get('/Subtype')!='/Form':return False
        if self.auto:
            oc=x.get('/OC')
            if oc is not None and 'watermark' in str(oc.get_object().get('/Name','')).lower():return True
            piece=x.get('/PieceInfo')
            if piece is not None:
                compound=piece.get_object().get('/ADBE_CompoundType')
                if compound is not None and str(compound.get_object().get('/Private',''))=='/Watermark':return True
        if depth<4 and key not in self.forms:
            self.forms.add(key);self.check()
            inner=x.get('/Resources');inner=inner.get_object() if inner is not None else res
            try:cs=ContentStream(x,self.w)
            except Exception:return False
            ops=list(cs.operations);kept=self.filter(ops,inner,depth+1)
            if ops and not kept:return True
            if len(kept)!=len(ops):cs.operations=kept;x.set_data(cs.get_data())
        return False

    def filter(self,ops,res,depth=0):
        out=[];marked=[];hidden=0;states=[];state={'font':None,'faint':False,'turned':False}
        block=None;text=[];block_turned=False
        for operands,op in ops:
            name=op.decode('latin-1') if isinstance(op,bytes) else str(op)
            unit=(operands,op)
            if name in ('BDC','BMC'):
                drop=self.auto and name=='BDC' and self.marked(operands,res);marked.append(drop)
                if drop:hidden+=1;self.removed+=1
                if hidden:continue
            elif name=='EMC':
                drop=marked.pop() if marked else False;inside=hidden>0
                if drop:hidden-=1
                if inside:continue
            if hidden:continue
            if name=='q':states.append(dict(state))
            elif name=='Q':
                if states:state=states.pop()
            elif name=='cm' and len(operands)==6:state['turned']=state['turned'] or _turned(operands)
            elif name=='gs' and operands and res is not None and '/ExtGState' in res:
                try:
                    g=res['/ExtGState'].get_object()[operands[0]].get_object()
                    if '/ca' in g:state['faint']=_num(g['/ca'])<0.95
                except Exception:pass
            elif name=='Tf' and len(operands)==2:state['font']=operands[0]
            if name=='BT':block=[];text=[];block_turned=False
            if block is not None:
                block.append(unit)
                if name=='Tm' and len(operands)==6:block_turned=block_turned or _turned(operands)
                if name in ('Tj',"'",'"','TJ'):text.append(self.decode(operands,res,state['font']))
                if name=='ET':
                    t=normal(''.join(text))
                    drop=(self.word and self.word in t) or (self.auto and t and (block_turned or state['turned']) and state['faint'])
                    if drop:self.removed+=1
                    else:out.extend(block)
                    block=None
                continue
            if name=='Do' and operands and res is not None and '/XObject' in res and self.drop_xobject(res,operands[0],depth):
                self.removed+=1;continue
            out.append(unit)
        if block:out.extend(block)
        return out

def _repeated(writer):
    from pypdf.generic import ContentStream
    seen={};pages=len(writer.pages)
    for index,page in enumerate(writer.pages):
        res=page.get('/Resources');res=res.get_object() if res is not None else None
        content=page.get_contents()
        if res is None or content is None or '/XObject' not in res:continue
        for operands,op in ContentStream(content,writer).operations:
            if op==b'Do' and operands:
                try:ref=res['/XObject'].get_object().raw_get(operands[0])
                except Exception:continue
                key=(ref.idnum,ref.generation) if hasattr(ref,'idnum') else id(ref)
                seen.setdefault(key,set()).add(index)
    need=max(2,math.ceil(pages*0.6))
    return {k for k,v in seen.items() if pages>=2 and len(v)>=need}

def _cover_ops(page,r,colour):
    from pypdf.generic import FloatObject
    box=page.cropbox;llx,lly=float(box.left),float(box.bottom);W,H=float(box.width),float(box.height);rot=(int(page.get('/Rotate',0) or 0)%360+360)%360
    if rot==90:x,y,w,h=llx+r[1]*W,lly+r[0]*H,r[3]*W,r[2]*H
    elif rot==180:x,y,w,h=llx+(1-r[0]-r[2])*W,lly+r[1]*H,r[2]*W,r[3]*H
    elif rot==270:x,y,w,h=llx+W-(r[1]+r[3])*W,lly+H-(r[0]+r[2])*H,r[3]*W,r[2]*H
    else:x,y,w,h=llx+r[0]*W,lly+(1-r[1]-r[3])*H,r[2]*W,r[3]*H
    f=lambda v:FloatObject(round(v,4))
    return [([],b'q'),([f(c) for c in colour],b'rg'),([f(x),f(y),f(w),f(h)],b're'),([],b'f'),([],b'Q')]

def clean(source,out,auto,repeated,keyword,regions,colour,check=lambda:None):
    """Returns (output path, number of removed or covered items)."""
    from pypdf import PdfWriter
    from pypdf.generic import ContentStream,ArrayObject,NameObject
    w=PdfWriter(clone_from=str(source))
    if getattr(w,'is_encrypted',False):
        try:w.decrypt('')
        except Exception:pass
    cleaner=_Cleaner(w,auto,normal(keyword),_repeated(w) if repeated else set(),check)
    for index,page in enumerate(w.pages):
        check()
        if auto and '/Annots' in page:
            annots=page['/Annots'].get_object();kept=ArrayObject()
            for a in annots:
                if str(a.get_object().get('/Subtype',''))=='/Watermark':cleaner.removed+=1
                else:kept.append(a)
            if len(kept)!=len(annots):page[NameObject('/Annots')]=kept
        res=page.get('/Resources');res=res.get_object() if res is not None else None
        content=page.get_contents()
        if content is None:continue
        cs=ContentStream(content,w);ops=list(cs.operations);kept=cleaner.filter(ops,res)
        cover=[]
        for r in regions:cover+=_cover_ops(page,r,colour(index,r))
        if len(kept)!=len(ops) or cover:
            cs.operations=([([],b'q')]+kept+[([],b'Q')]+cover) if cover else kept
            page.replace_contents(cs)
    removed=cleaner.removed+len(regions)*len(w.pages)
    out=Path(out)
    with out.open('wb') as f:w.write(f)
    return out,removed
