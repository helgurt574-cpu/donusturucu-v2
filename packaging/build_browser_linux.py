from pathlib import Path
import shutil,subprocess,os,json,hashlib,zipfile
b=Path(__file__).resolve().parents[1];root=b/'build/browser-linux-1.6.7.1';root.mkdir(exist_ok=True)
source=b/'build/installed-1.6.3/usr/share/donusturucu'
for name in ['donusturucu','vendor','asr-env','asr-models']:
 dst=root/name
 if dst.exists():shutil.rmtree(dst)
 shutil.copytree((b if name=='donusturucu' else source)/name,dst,symlinks=True,ignore=shutil.ignore_patterns('__pycache__'))
web=root/'browser-ui';web.mkdir(exist_ok=True)
for name in ['index.html','server.py']:shutil.copy2(b/'browser-ui'/name,web/name)
py=root/'python';(py/'bin').mkdir(parents=True,exist_ok=True);(py/'lib').mkdir(exist_ok=True);shutil.copy2('/usr/bin/python3.12',py/'bin/python3.12')
shutil.copytree('/usr/lib/python3.12',py/'lib/python3.12',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','test','tests','idlelib','tkinter','ensurepip','turtledemo'))
# Avoid hardcoded Ubuntu /usr/bin/python3.12 in the bundled speech environment.
p=root/'asr-env/bin/python';p.unlink(missing_ok=True);p.symlink_to('../../python/bin/python3.12')
launcher='''#!/usr/bin/env bash
set -euo pipefail
base="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "$(uname -m)" in x86_64|amd64) ;; *) echo 'Bu paket Intel/AMD64 Linux içindir.'; exit 1;; esac
export PYTHONHOME="$base/python"
export PYTHONPATH="$base/asr-env/lib/python3.12/site-packages:$base/vendor/python"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
cd "$base"
exec "$base/python/bin/python3.12" "$base/browser-ui/server.py" "$@"
'''
(root/'baslat.sh').write_text(launcher);(root/'baslat.sh').chmod(0o755)
(root/'KULLANIM.txt').write_text('Dönüştürücü HTML1.6.7.1 — Intel/AMD64 Linux, güncel Kali için hazırlanmıştır. Gerçek Kali üzerinde henüz test edilmedi. Ubuntu24.04 üzerinde test edildi.\n\nZIP içindeki klasörü tamamen çıkar. Terminali klasörde açıp: bash baslat.sh\nTarayıcı otomatik açılmazsa terminaldeki127.0.0.1 adresini kopyala. Terminal açık kalmalı. Bitince çıktı bağlantılarından dosyalarını indir; ardından terminalde Ctrl+C. index.html tek başına dönüşüm yapmaz; yerel motor gerekir.\nPython3.12, konuşma modeli/motoru, Pandoc, OCR dil dosyaları ve PDF okuyucu pakettedir. Sistem glibc uyumu ve native araç bağımlılıkları gerekir. FFmpeg/LibreOffice/Poppler mevcut sistemden kullanılır; eksik araçlar arayüzde gösterilir. Eksikse ilk kurulum internet gerektirebilir: sudo apt install ffmpeg libreoffice-writer libreoffice-calc libreoffice-impress poppler-utils file libseccomp2 libexpat1 zlib1g libtesseract5 liblept5 liblua5.4-0 libyaml-0-2 libgmp10 libffi8\nDönüştürme sırasında internet gerekmez; sunucu yalnız127.0.0.1 üzerinde dinler. Orijinaller değiştirilmez. Çıktıları indirmeden sunucuyu kapatma. Programdan çıkınca geçici çalışma dosyaları silinir.\nTürkçe/Kurmancî arayüz; listede çoklu seçme ve toplu dönüştürme. Klasör ekle alt klasörleri de alır. Seçilen işlem bütün uygun seçili dosyalara sırayla uygulanır; uyumsuz veya hatalı dosyalar raporlanır. Birleştirmede liste sırası kullanılır. Belgeler yeniden akabilir; OCR ve konuşma tanımada hata olabilir. Masaüstü1.6.7 motoru kullanılır. Bu Linux paketi Windows/macOS çalıştırılabilir paketi değildir.\n')
(root/'python/LICENSE.txt').write_text(Path('/usr/lib/python3.12/LICENSE.txt').read_text())
print(root,flush=True)
