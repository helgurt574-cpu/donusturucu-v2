from pathlib import Path
import subprocess,json,tempfile
from PIL import Image
r=Path(__file__).resolve().parents[1]/'pdf-page-results';source=r/'after-device';root=r/'independent-office';root.mkdir(exist_ok=True);rows=[]
for path in sorted(source.rglob('*')):
 if path.suffix not in {'.docx','.odt'}:continue
 row={'input':str(path)}
 try:
  out=root/path.parent.name;out.mkdir(exist_ok=True)
  with tempfile.TemporaryDirectory(prefix='qa-page-lo-') as profile:subprocess.run(['libreoffice','-env:UserInstallation='+Path(profile).as_uri(),'--headless','--convert-to','pdf','--outdir',str(out),str(path)],check=True,capture_output=True,timeout=60)
  pdf=out/(path.stem+'.pdf');info=subprocess.check_output(['pdfinfo',str(pdf)]).decode();assert any(l.split(':',1)[-1].strip()=='2' for l in info.splitlines() if l.startswith('Pages:')),info
  subprocess.run(['pdftoppm','-r','72','-png',str(pdf),str(out/'page')],check=True,capture_output=True,timeout=30);pngs=sorted(out.glob('page-*.png'));assert len(pngs)==2
  colors=[]
  for png in pngs:
   im=Image.open(png).convert('RGB');hist=im.getcolors(im.width*im.height);red=sum(n for n,(rr,g,b) in hist if rr>200 and g<50 and b<50);blue=sum(n for n,(rr,g,b) in hist if b>200 and rr<50 and g<50);colors.append((red,blue))
  assert colors[0][0]>500 and colors[0][1]<100 and colors[1][1]>500 and colors[1][0]<100,colors
  row.update(pass_=True,pages=2,page_color_pixels=colors)
 except Exception as e:row.update(pass_=False,error=str(e))
 rows.append(row)
d={'cases':len(rows),'failures':sum(not x['pass_'] for x in rows),'rows':rows};(r/'independent-office-report.json').write_text(json.dumps(d,indent=2)+'\n');print(d['cases'],d['failures']);assert d['cases']==6 and d['failures']==0,d
