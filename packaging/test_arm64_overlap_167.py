"""Execute packaged subtitle overlap logic under AArch64 QEMU; no native-device claim."""
from pathlib import Path
import subprocess,os
base=Path(__file__).resolve().parents[1]
root=base/'build/arm64-test/root';app=base/'build/package-arm64/usr/share/donusturucu';qemu=base/'build/arm64-test/qemu/usr/bin/qemu-aarch64'
env=os.environ.copy();env.update(PYTHONHOME=str(root/'usr'),PYTHONPATH=str(app)+':'+str(base),LD_LIBRARY_PATH=str(root/'usr/lib/aarch64-linux-gnu'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
code="import sys,unittest;sys.path.insert(0,"+repr(str(app))+ ");from donusturucu import core;assert '/package-arm64/' in core.__file__;print(core.__file__,flush=True);r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('tests.test_srt_overlap'));sys.exit(not r.wasSuccessful())"
subprocess.run([str(qemu),'-L',str(root),str(root/'usr/bin/python3.12'),'-c',code],env=env,check=True)
