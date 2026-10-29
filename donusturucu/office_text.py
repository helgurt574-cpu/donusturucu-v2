"""Sunu/tablo → yapısal metin belgesi, tamamen yerel ODF ayrıştırması."""
import base64
from html import escape
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from .core import ConversionError
from .text_layout import attrs,paragraph,html_document

NS={
 'office':'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
 'text':'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
 'table':'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
 'draw':'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0',
 'presentation':'urn:oasis:names:tc:opendocument:xmlns:presentation:1.0',
 'xlink':'http://www.w3.org/1999/xlink',
 'style':'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
 'fo':'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0',
}
def q(prefix,key):return '{'+NS[prefix]+'}'+key

def inline(node):
    out=escape(node.text or '')
    for child in node:
        if child.tag==q('text','s'):out+='&nbsp;'*min(1000,int(child.get(q('text','c'),'1')))
        elif child.tag==q('text','tab'):out+='&nbsp;&nbsp;&nbsp;&nbsp;'
        elif child.tag==q('text','line-break'):out+='<br/>'
        else:out+=inline(child)
        out+=escape(child.tail or '')
    return out

class Renderer:
    def __init__(self,archive,runner,options):self.archive=archive;self.runner=runner;self.cells=0;self.options=options;self.has_text=False;self.ocr_cache={};self.directions={};self.default_direction=None
    def nodes(self,node):
        self.runner.check()
        tag=node.tag
        if tag==q('presentation','notes'):return ''
        if tag in {q('text','p'),q('text','h')}:
            tagname='h2' if tag==q('text','h') else 'p'
            # Inline frames/images are handled separately, once per paragraph.
            content=inline(node)
            if content.strip():self.has_text=True
            images=''.join(self.image(n) for n in node.iter(q('draw','image')))
            style=node.get(q('text','style-name'),'')
            return f'<{tagname}'+attrs(''.join(node.itertext()),self.directions.get(style,self.default_direction))+f'>{content}</{tagname}>'+images
        if tag==q('draw','image'):return self.image(node)
        if tag==q('text','list'):
            # ODF list-header (common in imported PPT) also needs an HTML li.
            return '<ul>'+''.join(self.nodes(c) if c.tag==q('text','list-item') else '<li>'+self.nodes(c)+'</li>' for c in node)+'</ul>'
        if tag==q('text','list-item'):return '<li>'+''.join(self.nodes(c) for c in node)+'</li>'
        if tag==q('table','table'):return self.table(node)
        return ''.join(self.nodes(c) for c in node)
    def image(self,node):
        href=node.get(q('xlink','href'),'').removeprefix('./')
        # Embedded assets only. Never fetch links from a presentation.
        if href not in self.archive.namelist():return ''
        types={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.gif':'image/gif','.svg':'image/svg+xml'}
        mime=types.get(PurePosixPath(href).suffix.lower())
        if not mime:return ''
        if self.archive.getinfo(href).file_size>30*1024*1024:raise ConversionError('document_too_large')
        raw=self.archive.read(href);recognized=''
        if self.options.ocr and mime in {'image/png','image/jpeg','image/gif'}:
            if href not in self.ocr_cache:
                from .ocr import image_text
                with tempfile.TemporaryDirectory(prefix='donustur-image-') as tmp:
                    image=Path(tmp)/('image'+PurePosixPath(href).suffix);image.write_bytes(raw)
                    self.ocr_cache[href]=image_text(self.runner,image,self.options.ocr_language)
            text=self.ocr_cache[href]
            if text:self.has_text=True;recognized=paragraph(text)
        if self.options.only_text:return recognized
        data=base64.b64encode(raw).decode('ascii')
        return recognized+f'<p><img alt="" style="max-width:100%;height:auto" src="data:{mime};base64,{data}"/></p>'
    def table(self,node):
        rows=[]
        for row in node.iter(q('table','table-row')):
            cells=[]
            for cell in row:
                if cell.tag not in {q('table','table-cell'),q('table','covered-table-cell')}:continue
                value=''.join(self.nodes(c) for c in cell)
                if not value and cell.get(q('office','value')):value=escape(cell.get(q('office','value')))
                repeat=int(cell.get(q('table','number-columns-repeated'),'1'))
                # ODS commonly encodes thousands of empty trailing cells.
                if not value:repeat=min(repeat,256)
                self.cells+=repeat
                if self.cells>500000:raise ConversionError('document_too_large')
                cells.extend([value]*repeat)
            while cells and not cells[-1]:cells.pop()
            if not cells:continue
            repeat=int(row.get(q('table','number-rows-repeated'),'1'))
            if repeat*len(cells)+self.cells>500000:raise ConversionError('document_too_large')
            self.cells+=(repeat-1)*len(cells)
            rows.extend(['<tr>'+''.join('<td>'+c+'</td>' for c in cells)+'</tr>']*repeat)
        return '<table border="1" cellspacing="0" cellpadding="5">'+''.join(rows)+'</table>'

def office_to_html(runner,info,work,options):
    suffix={'presentation':'odp','spreadsheet':'ods','document':'odt'}[info.kind]
    if info.fmt==suffix:
        canonical=info.path
    else:
        stage=work/'normalize';stage.mkdir()
        source=stage/('source.'+info.fmt);shutil.copyfile(info.path,source)
        canonical=runner._office(source,suffix,info.kind,stage)
    with zipfile.ZipFile(canonical) as archive:
        if archive.getinfo('content.xml').file_size>30*1024*1024:raise ConversionError('document_too_large')
        root=ET.fromstring(archive.read('content.xml'))
        render=Renderer(archive,runner,options);parts=[]
        style_roots=[root]
        if 'styles.xml' in archive.namelist():style_roots.append(ET.fromstring(archive.read('styles.xml')))
        parents={}
        for style_root in style_roots:
            for default in style_root.findall('.//style:default-style',NS):
                if default.get(q('style','family'))!='paragraph':continue
                props=default.find('style:paragraph-properties',NS)
                if props is not None:
                    mode=props.get(q('style','writing-mode'),'')
                    if mode in {'rl-tb','rtl'}:render.default_direction='rtl'
                    elif mode in {'lr-tb','ltr'}:render.default_direction='ltr'
            for style in style_root.findall('.//style:style',NS):
                parents[style.get(q('style','name'))]=style.get(q('style','parent-style-name'))
                props=style.find('style:paragraph-properties',NS)
                if props is not None:
                    mode=props.get(q('style','writing-mode'),props.get(q('fo','direction'),''))
                    if mode in {'rl-tb','rtl'}:render.directions[style.get(q('style','name'))]='rtl'
                    elif mode in {'lr-tb','ltr'}:render.directions[style.get(q('style','name'))]='ltr'
        for name in parents:
            parent=parents.get(name);visited=set()
            while parent and parent not in visited:
                visited.add(parent)
                if parent in render.directions:render.directions.setdefault(name,render.directions[parent]);break
                parent=parents.get(parent)
        if info.kind=='presentation':
            for page in root.findall('.//draw:page',NS):
                # draw:name is internal slide metadata, not document content.
                parts.append('<section>'+render.nodes(page)+'</section>')
        elif info.kind=='spreadsheet':
            for table in root.findall('.//office:spreadsheet/table:table',NS):
                name=table.get(q('table','name'),'')
                parts.append('<h1>'+escape(name)+'</h1>'+render.table(table))
        else:
            body=root.find('.//office:text',NS)
            if body is not None:parts.append(render.nodes(body))
        if options.only_text and not render.has_text:raise ConversionError('ocr_no_text' if options.ocr else 'no_text')
    output=work/'content.html'
    output.write_text(html_document(info.path.stem,''.join(parts),''.join(root.itertext())),encoding='utf-8')
    return output
