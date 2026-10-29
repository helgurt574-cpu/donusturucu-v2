from pathlib import Path
import subprocess,json,tempfile
from PIL import Image
r=Path(__file__).resolve().parents[1]/'blank-page-results';source=r/'device';root=r/'independent-office';root.mkdir(exist_ok=True);rows=[]
for path in sorted(source.rglob('*')):
 if path.suffix not in {'.docx','.odt'}:continue
 row={'input':str(path)}
 try:
  out=root/path.parent.name;out.mkdir(exist_ok=True)
  with tempfile.TemporaryDirectory(prefix='qa-blank-lo-') as profile:subprocess.run(['libreoffice','-env:UserInstallation='+Path(profile).as_uri(),'--headless','--convert-to','pdf','--outdir',str(out),str(path)],check=True,capture_output=True,timeout=60)
  pdf=out/(path.stem+'.pdf');info=subprocess.check_output(['pdfinfo',str(pdf)]).decode();assert any(l.split(':',1)[-1].strip()=='3' for l in info.splitlines() if l.startswith('Pages:')),info
  subprocess.run(['pdftoppm','-r','60','-png',str(pdf),str(out/'page')],check=True,capture_output=True,timeout=30);pngs=sorted(out.glob('page-*.png'));assert len(pngs)==3
  expect=['red','white','blue'] if 'blank-middle' in path.parent.name else ['white','red','white'];checks=[]
  for png,color in zip(pngs,expect):
   im=Image.open(png).convert('RGB');hist=im.getcolors(im.width*im.height);nonwhite=sum(n for n,(rr,g,b) in hist if min(rr,g,b)<245);red=sum(n for n,(rr,g,b) in hist if rr>200 and g<50 and b<50);blue=sum(n for n,(rr,g,b) in hist if b>200 and rr<50 and g<50)
   assert (nonwhite<20 if color=='white' else red>500 and blue<100 if color=='red' else blue>500 and red<100),(png,color,nonwhite,red,blue);checks.append({'expected':color,'nonwhite_pixels':nonwhite,'red_pixels':red,'blue_pixels':blue})
  row.update(pass_=True,pages=3,pixel_checks=checks)
 except Exception as e:row.update(pass_=False,error=str(e))
 rows.append(row)
d={'cases':len(rows),'failures':sum(not x['pass_'] for x in rows),'rows':rows};(r/'independent-office-report.json').write_text(json.dumps(d,indent=2)+'\n');print(d['cases'],d['failures']);assert d['cases']==12 and d['failures']==0,d
