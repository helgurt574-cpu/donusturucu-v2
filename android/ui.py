from pathlib import Path
import subprocess,sys,xml.etree.ElementTree as ET,re
ROOT=Path(__file__).resolve().parent
ADB=[str(ROOT/'sdk/platform-tools/adb'),'-P','5038','-s','emulator-5580']
def state():
 subprocess.run(ADB+['shell','uiautomator','dump','/sdcard/window.xml'],stdout=subprocess.DEVNULL,check=True)
 raw=subprocess.check_output(ADB+['exec-out','cat','/sdcard/window.xml']);(ROOT/'window.xml').write_bytes(raw);return ET.fromstring(raw)
if len(sys.argv)>1 and sys.argv[1]=='tap':
 label=sys.argv[2];nodes=[n for n in state().iter('node') if n.get('text')==label or n.get('content-desc')==label]
 if not nodes:raise SystemExit('NOT FOUND: '+label)
 node=nodes[0];x1,y1,x2,y2=map(int,re.findall(r'\d+',node.get('bounds')));subprocess.run(ADB+['shell','input','tap',str((x1+x2)//2),str((y1+y2)//2)],check=True)
else:
 for n in state().iter('node'):
  if n.get('text') or n.get('content-desc'):print(n.get('text') or n.get('content-desc'),n.get('bounds'),n.get('class'))
