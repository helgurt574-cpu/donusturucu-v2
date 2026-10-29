from pathlib import Path
import subprocess,zipfile,shutil
r=Path(__file__).resolve().parent;a=r.parent;b=r/'build';b.mkdir(exist_ok=True);classes=b/'classes';classes.mkdir(exist_ok=True);jar=a/'toolroot/usr/share/java/com.android.android-23.jar'
def run(args):subprocess.run(list(map(str,args)),check=True)
run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-source','8','-target','8','-bootclasspath',jar,'-d',classes,*r.joinpath('src').rglob('*.java')])
run([a/'build-tools/aapt2','link','-o',b/'resources.apk','-I',jar,'--manifest',r/'AndroidManifest.xml','-A',r/'assets'])
with zipfile.ZipFile(b/'classes.jar','w') as z:
 for p in classes.rglob('*.class'):z.write(p,str(p.relative_to(classes)))
dex=b/'dex';dex.mkdir(exist_ok=True);run(['java','-cp',a/'cache/r8.jar','com.android.tools.r8.D8','--min-api','28','--lib',jar,'--output',dex,b/'classes.jar'])
with zipfile.ZipFile(b/'resources.apk') as src,zipfile.ZipFile(b/'unsigned.apk','w',zipfile.ZIP_DEFLATED) as dst:
 for n in src.namelist():dst.writestr(n,src.read(n))
 dst.write(dex/'classes.dex','classes.dex')
signer=a/'toolroot/usr/share/java/apksigner-31.0.2.jar'
run(['java','-cp',signer,'com.android.apksigner.ApkSignerTool','sign','--ks',a/'signing/release.p12','--ks-pass','file:'+str(a/'signing/password.txt'),'--ks-key-alias','donusturucu','--out',b/'diagnostic.apk',b/'unsigned.apk'])
run(['java','-cp',signer,'com.android.apksigner.ApkSignerTool','verify',b/'diagnostic.apk'])
