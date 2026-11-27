#!/bin/bash
# Intel Mac (x86_64) kurulum paketi: yayımlanmış Apple Silicon .pkg'yi açar, mimariye bağlı
# parçaları (conda paketleri, wheel'ler, micromamba, FFmpeg, LibreOffice) x86_64 karşılıklarıyla
# değiştirir ve paketi yeniden kurar. Uygulama kodu, Whisper modeli ve OCR dil verileri aynen kalır.
# Yalnızca derleme sırasında internet gerekir; macOS'ta (GitHub macos-15-intel) çalıştırılır.
#
#   packaging/build_macos_intel.sh <Apple-Silicon.pkg> <çıktı.pkg>
set -euo pipefail
BASE_PKG="$1"; OUT="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${WORK:-$RUNNER_TEMP/intel}"
LO_VERSION=26.8.1.1
LO_URL="https://downloadarchive.documentfoundation.org/libreoffice/old/$LO_VERSION/mac/x86_64/LibreOffice_${LO_VERSION}_MacOS_x86-64.dmg"
# Apple Silicon paketindeki Python ve araç sürümleri
CONDA_SPECS=(python=3.13.18 tk tesseract=5.5.3 poppler=26.10.0 pandoc=3.13 cairo pip)
export CONDA_OVERRIDE_OSX=13.0

rm -rf "$WORK"; mkdir -p "$WORK"
pkgutil --expand-full "$BASE_PKG" "$WORK/expanded"
ROOT="$WORK/expanded/Donusturucu.pkg/Payload"
APP="$ROOT/Applications/Donusturucu.app/Contents/Resources/app"
[ -f "$APP/launch.py" ] || { echo "Uygulama bulunamadı: $APP"; exit 1; }
VERSION=$(/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" "$ROOT/Applications/Donusturucu.app/Contents/Info.plist")
echo "Dönüştürücü $VERSION"

# --- micromamba (osx-64) ---
mkdir -p "$WORK/mm"
gh release download -R mamba-org/micromamba-releases -p 'micromamba-osx-64' -p 'micromamba-osx-64.sha256' -D "$WORK/mm"
(cd "$WORK/mm" && [ "$(shasum -a 256 micromamba-osx-64 | cut -d' ' -f1)" = "$(cut -d' ' -f1 micromamba-osx-64.sha256)" ])
install -m 755 "$WORK/mm/micromamba-osx-64" "$APP/micromamba"
"$APP/micromamba" --version

# --- conda paketleri (osx-64, en düşük macOS 13) ---
"$APP/micromamba" create --no-rc --yes --dry-run --json --platform osx-64 \
  --root-prefix "$WORK/mmroot" --prefix "$WORK/solve" -c conda-forge --override-channels \
  "${CONDA_SPECS[@]}" > "$WORK/solve.json"
rm -rf "$APP/packages"; mkdir -p "$APP/packages"
python3 - "$WORK/solve.json" "$APP/packages" <<'PY'
import hashlib,json,sys,urllib.request
from pathlib import Path
plan=json.load(open(sys.argv[1]));dest=Path(sys.argv[2])
assert plan.get('success'),plan
fetch=plan['actions']['FETCH'];link=plan['actions']['LINK']
assert all(x['subdir'] in ('osx-64','noarch') for x in fetch),'yanlış mimari'
for x in fetch:
    target=dest/x['fn']
    with urllib.request.urlopen(x['url'],timeout=300) as r:data=r.read()
    if hashlib.sha256(data).hexdigest()!=x['sha256']:raise SystemExit('SHA-256 uyuşmuyor: '+x['url'])
    target.write_bytes(data);print(x['subdir'],x['fn'],flush=True)
names={x['fn'] for x in fetch};order=[x.get('fn') for x in link if x.get('fn') in names]
if set(order)!=names:order=[x['fn'] for x in fetch]
(dest/'explicit.txt').write_text('@EXPLICIT\n'+''.join(f+'\n' for f in order))
PY

# --- wheel'ler: arm64 olanların x86_64 karşılıkları (aynı sürümler) ---
for w in "$APP"/wheels/*arm64*.whl; do
  name=$(basename "$w" | cut -d- -f1); ver=$(basename "$w" | cut -d- -f2)
  rm "$w"
  python3 -m pip download --quiet --no-deps --only-binary=:all: --dest "$APP/wheels" \
    --platform macosx_13_0_x86_64 --python-version 3.13 --implementation cp "$name==$ver"
done
ls "$APP/wheels"
if ls "$APP"/wheels/*arm64*.whl >/dev/null 2>&1; then echo 'arm64 wheel kaldı'; exit 1; fi

# --- FFmpeg (martin-riedl.de statik derleme, yayıncının sağlama toplamıyla) ---
python3 "$HERE/fetch_ffmpeg.py" --platform macos-x64 --dest "$WORK/ffmpeg"
install -m 755 "$WORK/ffmpeg/ffmpeg" "$WORK/ffmpeg/ffprobe" "$APP/tools/"
cp "$WORK/ffmpeg/licenses/ffmpeg/SOURCE.txt" "$APP/licenses/ffmpeg/SOURCE.txt"

# --- LibreOffice (x86_64, Apple Silicon paketindekiyle aynı sürüm) ---
curl -fsSL -o "$WORK/lo.dmg" "$LO_URL"
[ "$(shasum -a 256 "$WORK/lo.dmg" | cut -d' ' -f1)" = "$(curl -fsSL "$LO_URL.sha256" | cut -d' ' -f1)" ]
hdiutil attach -nobrowse -readonly -mountpoint "$WORK/lo" "$WORK/lo.dmg" >/dev/null
rm -rf "$APP/tools/LibreOffice.app"
ditto "$WORK/lo/LibreOffice.app" "$APP/tools/LibreOffice.app"
hdiutil detach "$WORK/lo" >/dev/null

sed -i '' 's/PLATFORM="osx-arm64"/PLATFORM="osx-64"/' "$APP/setup-runtime.sh"
grep -q 'PLATFORM="osx-64"' "$APP/setup-runtime.sh"

# --- denetim: paketteki her Mach-O dosyası x86_64 olmalı ---
bad=0
while IFS= read -r -d '' f; do
  case "$(file -b "$f")" in
    *Mach-O*) archs=$(lipo -archs "$f" 2>/dev/null || true)
      case " $archs " in *" x86_64 "*) ;; *) echo "x86_64 değil ($archs): ${f#$APP/}"; bad=1;; esac;;
  esac
done < <(find "$ROOT/Applications" -type f -size +1k \( -perm -u+x -o -name '*.dylib' -o -name '*.so' \) -print0)
[ $bad -eq 0 ]

# --- paket ---
SCRIPTS="$WORK/scripts"; mkdir -p "$SCRIPTS"
sed 's/(osx-arm64)/(osx-64)/' "$WORK/expanded/Donusturucu.pkg/Scripts/postinstall" > "$SCRIPTS/postinstall"
chmod 755 "$SCRIPTS/postinstall"
find "$ROOT" -name .DS_Store -delete
pkgbuild --root "$ROOT" --scripts "$SCRIPTS" --identifier org.local.donusturucu.x86_64 \
  --version "$VERSION" --install-location / "$WORK/Donusturucu.pkg"
cat > "$WORK/Distribution" <<XML
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2"><title>Dönüştürücü $VERSION</title><options customize="never" require-scripts="false" hostArchitectures="x86_64" rootVolumeOnly="true"/><allowed-os-versions><os-version min="13.0"/></allowed-os-versions><choices-outline><line choice="default"><line choice="app"/></line></choices-outline><choice id="default"/><choice id="app" visible="false"><pkg-ref id="org.local.donusturucu.x86_64"/></choice><pkg-ref id="org.local.donusturucu.x86_64" version="$VERSION" onConclusion="none">Donusturucu.pkg</pkg-ref></installer-gui-script>
XML
productbuild --distribution "$WORK/Distribution" --package-path "$WORK" "$OUT"
ls -la "$OUT"
