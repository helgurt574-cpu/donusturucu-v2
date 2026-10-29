"""Opt-in local OCR; no online service or model downloads at conversion time."""
from pathlib import Path
import sys,tempfile
from . import runtime
from .core import ConversionError

def image_text(runner,image,language):
    with tempfile.TemporaryDirectory(prefix='donustur-ocr-',dir=runtime.ascii_dir()) as tmp:
        output=Path(tmp)/'recognized';image=runtime.ascii_path(image,tmp)
        runner.run(['tesseract',str(image),str(output),'-l',language,'--psm','3'],timeout=600)
        return output.with_suffix('.txt').read_text(encoding='utf-8').strip()

def page_text(runner,source,index,work,language):
    """OCR one PDF page (0-based index)."""
    raster=work/'ocr-pages'
    if sys.platform=='win32' and not runtime.is_ascii(raster):raster=runtime.ascii_dir()/'ocr-pages'
    raster.mkdir(parents=True,exist_ok=True);source=runtime.ascii_path(source,raster)
    prefix=raster/('page-'+str(index+1))
    runner.run(['pdftoppm','-f',str(index+1),'-l',str(index+1),'-r','300','-png','-singlefile',str(source),str(prefix)],timeout=600)
    image=prefix.with_suffix('.png')
    try:return image_text(runner,image,language)
    finally:image.unlink(missing_ok=True)

def meaningful(text):
    """Letters and digits only: blank pages, bullets and brackets do not count as text."""
    return sum(ch.isalnum() for ch in text)

def pdf_text(runner,source,work,language):
    from pypdf import PdfReader
    reader=PdfReader(source)
    if reader.is_encrypted:raise ConversionError('encrypted')
    parts=[];total=len(reader.pages)
    for index in range(total):
        runner.check();parts.append(page_text(runner,source,index,work,language))
        runner.progress(min(.95,(index+1)/max(1,total)))
    return '\n\n'.join(parts)
