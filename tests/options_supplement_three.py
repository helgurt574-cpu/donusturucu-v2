from pathlib import Path
import os,sys,json,time,hashlib,subprocess,concurrent.futures
BASE=Path(__file__).resolve().parents[1];APP=Path(os.environ['DONUSTURUCU_TEST_APP_ROOT']);sys.path.insert(0,str(APP));sys.path.append(str(BASE/'tests'))
from donusturucu import core,runtime
from donusturucu.operations import Editor,Request
from test_conversion import odf
from pypdf import PdfReader,PdfWriter
import cairo
ROOT=Path(os.environ.get('DONUSTURUCU_AUDIT_OUT',str(BASE/'qa-1.6.2')))/'supplement';ROOT.mkdir(parents=True,exist_ok=True);seeds=ROOT/'seeds';seeds.mkdir(exist_ok=True);rows=[]
def save():
 report={'app_root':str(APP),'isolation':runtime.isolation_status(),'cases':len(rows),'failures':sum(not r['pass'] for r in rows),'rows':rows};p=ROOT/'report.pending.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2));p.replace(ROOT/'report.json')
def case(option,rep,fn):
 row={'option':option,'repeat':rep,'started':time.time()};folder=ROOT/'outputs'/(option.replace(':','-').replace('/','-'))/str(rep);folder.mkdir(parents=True,exist_ok=True)
 try:row.update(fn(folder) or {});row['pass']=True
 except Exception as e:row.update({'pass':False,'error':str(e),'detail':getattr(e,'detail','')})
 row['seconds']=round(time.time()-row.pop('started'),2);rows.append(row);save();print(option,rep,row['pass'],row.get('error',''),flush=True)
def validate(p,word='Silav'):
 info=core.detect(p)
 if info.kind in {'video','audio'}:subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','null','-'],check=True,capture_output=True,timeout=90)
 else:
  txt=p if info.fmt=='txt' else core.Runner().convert(info,'txt',p.parent/'verify')
  assert word.lower() in txt.read_text(encoding='utf-8-sig').lower(),txt.read_text(encoding='utf-8-sig')[:250]
 return {'output':str(p),'bytes':p.stat().st_size}
# The actual file in the reported failure is read only. Three whole-file attempts.
user=Path('/media/gabar/NESIBE/00/calisss/harita/Android Platformunda Harita Uygulaması - Bitirme Projeleri.mp4')
for label,source,lang,word in [('reported-user-video',user,'tr',None),('speech-tr',BASE/'assets/speech/turkish-test.wav','tr','merhaba'),('speech-en',BASE/'assets/speech/english-test.mp3','en','repeat that')]:
 if not source.is_file():raise RuntimeError('Missing authorized test input: '+str(source))
 digest=hashlib.file_digest(source.open('rb'),'sha256').hexdigest()
 for rep in range(1,4):
  def speak(out,source=source,lang=lang,word=word):
   p=Editor().execute(Request('transcribe',[source],out,speech_language=lang))[0];text=p.read_text();assert text.strip();assert word is None or word in text.lower(),text;return {'output':str(p),'text':text,'source_unchanged':hashlib.file_digest(source.open('rb'),'sha256').hexdigest()==digest}
  case(label,rep,speak)
 assert hashlib.file_digest(source.open('rb'),'sha256').hexdigest()==digest
# Every video quality and height choice, independently checked on an HD source.
hd=seeds/'hd.mp4';subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=s=1920x1080:r=10:d=0.4','-f','lavfi','-i','sine=d=0.4','-c:v','libx264','-preset','ultrafast','-c:a','aac','-shortest','-y',str(hd)],check=True)
for quality in ['original','small','balanced','high']:
 for rep in range(1,4):case('quality:'+quality,rep,lambda out,q=quality:validate(core.Runner().convert(core.detect(hd),'mp4',out,core.Options(quality=q))))
for resolution in ['original','1080','720','480']:
 for rep in range(1,4):
  def height(out,resolution=resolution):
   p=core.Runner().convert(core.detect(hd),'mp4',out,core.Options(quality='balanced',resolution=resolution));assert core.detect(p).height==(1080 if resolution=='original' else int(resolution));return validate(p)
  case('height:'+resolution,rep,height)
# All text-only export destinations for each document family.
doc=seeds/'document.odt';odf(doc,'document','<text:p>Silav cîhan! Merhaba dünya.</text:p>')
slide=seeds/'presentation.odp';odf(slide,'presentation','<draw:page><draw:frame><draw:text-box><text:p>Silav cîhan!</text:p></draw:text-box></draw:frame></draw:page>')
sheet=seeds/'sheet.ods';odf(sheet,'spreadsheet','<table:table table:name="Silav"><table:table-row><table:table-cell office:value-type="string"><text:p>Silav cîhan!</text:p></table:table-cell></table:table-row></table:table>')
pdf=core.Runner().convert(core.detect(doc),'pdf',seeds)
for source in [doc,slide,sheet,pdf]:
 for target in sorted(core.DOC|core.TEXT_EXPORT):
  for rep in range(1,4):case('text-only:'+source.suffix[1:]+':'+target,rep,lambda out,s=source,t=target:validate(core.Runner().convert(core.detect(s),t,out,core.Options(only_text=True))))
# Raster-only PDF: one real scan per OCR language selector; every text export too.
def scan(image,name):
 p=seeds/(name+'.pdf');im=cairo.ImageSurface.create_from_png(str(image));surface=cairo.PDFSurface(str(p),700,200);ctx=cairo.Context(surface);ctx.scale(700/im.get_width(),200/im.get_height());ctx.set_source_surface(im,0,0);ctx.paint();surface.finish();return p
eng=scan(BASE/'packaging/ocr-smoke.png','scan-eng');ara=scan(BASE/'packaging/ocr-smoke-ara.png','scan-ara');fas=scan(BASE/'packaging/ocr-smoke-fas.png','scan-fas')
for language in ['tur+eng','kmr+eng','eng','ara+eng','fas+eng','ara+fas+eng','tur+kmr+eng']:
 source,word=(fas,'سلام') if language=='fas+eng' else (ara,'مرحبا') if language.startswith('ara') else (eng,'OFFLINE')
 for rep in range(1,4):case('ocr-language:'+language,rep,lambda out,s=source,w=word,l=language:validate(core.Runner().convert(core.detect(s),'txt',out,core.Options(only_text=True,ocr=True,ocr_language=l)),w))
for target in sorted(core.DOC|core.TEXT_EXPORT):
 for rep in range(1,4):case('ocr-output:'+target,rep,lambda out,t=target:validate(core.Runner().convert(core.detect(eng),t,out,core.Options(only_text=True,ocr=True,ocr_language='eng')),'OFFLINE'))
# Every document page operation, whole-document and explicit page groups.
writer=PdfWriter();[writer.add_blank_page(width=300+i,height=400) for i in range(5)];multi=seeds/'five-pages.pdf';writer.write(multi);writer.close()
for source in [doc,slide,sheet,pdf,multi]:
 for action in ['split','merge']:
  for rep in range(1,4):
   def pages(out,s=source,a=action,rep=rep):
    count=5 if s==multi else 1;files=[s,s] if a=='merge' else [s];products=Editor().execute(Request(a,files,out,page_count=str(rep)));total=sum(len(PdfReader(p).pages) for p in products);assert total==count*(2 if a=='merge' else 1),(s,a,total);return {'outputs':list(map(str,products)),'pages':total}
   case('pages:'+source.name+':'+action,rep,pages)
for rep in range(1,4):
 def groups(out,rep=rep):
  groups=['1-2;3,5','1,3,5;2,4','5;1-4'][rep-1];products=Editor().execute(Request('split',[multi],out,pages=groups));assert len(products)==2;return {'outputs':list(map(str,products))}
 case('page-groups',rep,groups)
# All explicit rotation angles/speed and gain choices are executed three times.
for action,values in [('rotate',['90','180','270']),('speed',['0.5','1','1.5','2']),('volume',['0','0.5','1','2','3'])]:
 for factor in values:
  for rep in range(1,4):
   def change(out,a=action,f=factor):
    source=BASE/'assets/speech/turkish-test.wav' if a=='volume' else hd;p=Editor().execute(Request(a,[source],out,start='0',end='.3',factor=f))[0];return validate(p)
   case(action+':'+factor,rep,change)
assert all(r['pass'] for r in rows),str(sum(not r['pass'] for r in rows))+' supplement failures'
print('SUPPLEMENT PASSED',len(rows),flush=True)
