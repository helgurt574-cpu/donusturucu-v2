"""Preserve logical Unicode order; declare paragraph direction explicitly."""
from html import escape
from pathlib import Path
import unicodedata

def direction(text,default='ltr'):
    for char in text:
        bidi=unicodedata.bidirectional(char)
        if bidi in {'R','AL'}:return 'rtl'
        if bidi=='L':return 'ltr'
    return default

def has_rtl(text):return any(unicodedata.bidirectional(c) in {'R','AL'} for c in text)

def attrs(text,explicit=None):
    value=explicit or direction(text)
    return f' dir="{value}" style="direction:{value};text-align:{"right" if value=="rtl" else "left"}"'

def paragraph(text):
    return '<p'+attrs(text)+'>'+escape(text).replace('\n','<br/>')+'</p>'

def html_document(title,body,plain=''):
    return '<!DOCTYPE html><html dir="'+direction(plain)+'"><head><meta charset="utf-8"/><title>'+escape(title)+'</title><style>body{font-family:"DejaVu Sans",Arial,sans-serif}p{white-space:pre-wrap}section{page-break-before:always}section:first-child{page-break-before:auto}td{vertical-align:top}img{max-width:100%}</style></head><body>'+body+'</body></html>'

def text_to_html(text,path,title=''):
    body=''.join(paragraph(line) for line in text.splitlines())
    Path(path).write_text(html_document(title,body,text),encoding='utf-8')
    return Path(path)

def read_text(path):
    data=Path(path).read_bytes()
    encoding='utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'
    return data.decode(encoding)

def fb2_to_html(source,path):
    """Import FB2 tables as well as paragraphs (Pandoc's reader drops tables)."""
    import xml.etree.ElementTree as ET
    root=ET.parse(source).getroot()
    ns='{http://www.gribuser.ru/xml/fictionbook/2.0}'
    tags={'p':'p','title':'h2','subtitle':'h3','section':'section',
          'table':'table','tr':'tr','td':'td','th':'th','strong':'strong',
          'emphasis':'em','strikethrough':'s','code':'code',
          'cite':'blockquote','poem':'div','stanza':'div','v':'p',
          'text-author':'p','epigraph':'blockquote','sup':'sup','sub':'sub'}
    binaries={n.get('id'):n for n in root.findall(ns+'binary')}
    def render(node):
        name=node.tag.rsplit('}',1)[-1]
        if name in {'binary','description'}:return ''
        if name=='empty-line':return '<br/>'
        if name=='image':
            href=node.get('{http://www.w3.org/1999/xlink}href','')
            binary=binaries.get(href[1:]) if href.startswith('#') else None
            if binary is None:return ''
            mime=binary.get('content-type','')
            if mime not in {'image/png','image/jpeg','image/gif'}:return ''
            import base64
            try:
                data=base64.b64encode(binary.text or '',validate=False)
                if len(data)>30*1024*1024:return ''
            except ValueError:return ''
            return '<img alt="" src="data:'+mime+';base64,'+base64.b64encode(data).decode()+'"/>'
        body=escape(node.text or '')+''.join(render(c)+escape(c.tail or '') for c in node)
        tag=tags.get(name)
        if not tag:return body
        extra=attrs(''.join(node.itertext())) if tag in {'p','td','th','h2','h3'} else ''
        for key in ('colspan','rowspan'):
            value=node.get(key,'')
            if tag in {'td','th'} and value.isdigit():extra+=f' {key}="{int(value)}"'
        return '<'+tag+extra+'>'+body+'</'+tag+'>'
    bodies=root.findall(ns+'body')
    plain='\n'.join(''.join(b.itertext()) for b in bodies)
    Path(path).write_text(html_document(Path(source).stem,''.join(render(b) for b in bodies),plain),encoding='utf-8')
    return Path(path)

def fix_epub_direction(path):
    """LibreOffice's EPUB exporter drops paragraph bidi flags; restore them.
    Preserve logical text, asset bytes, ZIP member order and mimetype storage.
    """
    import zipfile
    import xml.etree.ElementTree as ET
    path=Path(path);changed={};first_direction=None
    xhtml='{http://www.w3.org/1999/xhtml}'
    with zipfile.ZipFile(path) as archive:
        for item in archive.infolist():
            if not item.filename.endswith(('.xhtml','.html')) or Path(item.filename).name in {'toc.xhtml','nav.xhtml'}:continue
            try:root=ET.fromstring(archive.read(item))
            except ET.ParseError:continue
            body=root.find(xhtml+'body')
            if body is None:continue
            plain=''.join(body.itertext())
            if not has_rtl(plain):continue
            base=direction(plain)
            if first_direction is None:first_direction=base
            root.set('dir',base);body.set('dir',base);body.set('style',body.get('style','')+';direction:'+base)
            for element in body.iter():
                if element.tag.rsplit('}',1)[-1] in {'p','h1','h2','h3','li','td'}:
                    value=direction(''.join(element.itertext()),base)
                    element.set('dir',value);element.set('style',element.get('style','')+';direction:'+value+';text-align:'+('right' if value=='rtl' else 'left'))
            changed[item.filename]=ET.tostring(root,encoding='utf-8',xml_declaration=True)
        if not changed:return
        for item in archive.infolist():
            if not item.filename.endswith('.opf'):continue
            root=ET.fromstring(archive.read(item));spine=root.find('{http://www.idpf.org/2007/opf}spine')
            if spine is not None:spine.set('page-progression-direction',first_direction or 'rtl')
            changed[item.filename]=ET.tostring(root,encoding='utf-8',xml_declaration=True)
        tmp=path.with_suffix('.fixed.epub')
        with zipfile.ZipFile(tmp,'w') as output:
            for item in archive.infolist():output.writestr(item,changed.get(item.filename,archive.read(item)))
    tmp.replace(path)

def ensure_html_direction(path):
    """Restore bidi lost by an intermediate converter without changing text."""
    from html.parser import HTMLParser
    from html import unescape
    class Parser(HTMLParser):
        def __init__(self):super().__init__(convert_charrefs=False);self.out=[];self.blocks=[]
        def handle_starttag(self,tag,attributes):
            index=len(self.out);self.out.append(self.get_starttag_text())
            if tag in {'p','h1','h2','h3','h4','h5','h6','li','td'}:self.blocks.append([tag,index,attributes,[]])
        def handle_endtag(self,tag):
            for i in range(len(self.blocks)-1,-1,-1):
                block=self.blocks[i]
                if block[0]!=tag:continue
                self.blocks.pop(i);attributes=dict(block[2]);text=''.join(block[3])
                if has_rtl(text) and 'dir' not in attributes:
                    value=direction(text);attributes['dir']=value
                    attributes['style']=attributes.get('style','')+';direction:'+value+';text-align:'+('right' if value=='rtl' else 'left')
                    self.out[block[1]]='<'+tag+''.join(' '+k+('="'+escape(v,quote=True)+'"' if v is not None else '') for k,v in attributes.items())+'>'
                break
            self.out.append('</'+tag+'>')
        def handle_startendtag(self,tag,attributes):self.out.append(self.get_starttag_text())
        def handle_data(self,data):
            self.out.append(data)
            for block in self.blocks:block[3].append(data)
        def reference(self,value):
            self.out.append(value)
            for block in self.blocks:block[3].append(unescape(value))
        def handle_entityref(self,name):self.reference('&'+name+';')
        def handle_charref(self,name):self.reference('&#'+name+';')
        def handle_decl(self,value):self.out.append('<!'+value+'>')
        def handle_comment(self,value):self.out.append('<!--'+value+'-->')
        def handle_pi(self,value):self.out.append('<?'+value+'>')
    path=Path(path);parser=Parser();parser.feed(path.read_text(encoding='utf-8'));parser.close()
    path.write_text(''.join(parser.out),encoding='utf-8')
