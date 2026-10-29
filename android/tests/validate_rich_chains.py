from pathlib import Path
import subprocess,tempfile,json
from PIL import Image
root=Path(__file__).resolve().parents[1]/'rich-chain-results';device=root/'device';out=root/'independent-office';out.mkdir(exist_ok=True);rows=[]
for source in sorted(device.rglob('*')):
 if source.suffix not in {'.docx','.odt'}:continue
 row={'source':str(source)}
 try:
  dest=out/source.parent.name;dest.mkdir(exist_ok=True)
  with tempfile.TemporaryDirectory(prefix='chain-lo-') as profile:
   p=subprocess.run(['libreoffice','-env:UserInstallation='+Path(profile).as_uri(),'--headless','--convert-to','pdf','--outdir',str(dest),str(source)],capture_output=True,text=True,timeout=60);assert p.returncode==0,p.stderr
  pdf=dest/(source.stem+'.pdf');assert pdf.is_file()
  text=subprocess.check_output(['pdftotext',str(pdf),'-']).decode();assert 'Merhaba' in text and 'Silav' in text,text
  assert all(ch in text for ch in 'مرحبا'),repr(text)
  subprocess.run(['pdftoppm','-f','1','-singlefile','-r','90','-png',str(pdf),str(dest/'preview')],capture_output=True,check=True,timeout=30)
  im=Image.open(dest/'preview.png').convert('RGB');hist=im.getcolors(im.width*im.height);red=sum(n for n,(r,g,b) in hist if r>220 and g<50 and b<50);blue=sum(n for n,(r,g,b) in hist if b>220 and r<50 and g<50);assert red>200 and blue>200,(red,blue)
  row.update(pass_=True,red_pixels=red,blue_pixels=blue,latin_text=True,arabic_letters=True)
 except Exception as e:row.update(pass_=False,error=str(e))
 rows.append(row)
report={'cases':len(rows),'failures':sum(not r['pass_'] for r in rows),'rows':rows};(root/'independent-office-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(report['cases'],report['failures']);assert not report['failures'],[r for r in rows if not r['pass_']]
