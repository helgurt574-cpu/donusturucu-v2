#!/bin/bash
# Build the local Python runtime from the bundled, hash-checked packages (no internet).
#   setup-runtime.sh APP_DIR TARGET_RUNTIME_DIR
# Used by the .pkg postinstall (as root, into the app) and, if that failed, by the
# launcher on first start (as the user, into ~/Library/Application Support).
APP="$1"; RT="$2"; PLATFORM="@PLATFORM@"
unset PYTHONHOME PYTHONPATH
export PYTHONNOUSERSITE=1 PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 CONDA_OVERRIDE_OSX=13.0
WORK="$(dirname "$RT")"; mkdir -p "$WORK" || exit 1
echo "== $(date) yerel motor hazırlanıyor: $RT ($PLATFORM)"
SPEC="$WORK/offline-explicit.txt"
{ echo '@EXPLICIT'; grep -v '^@' "$APP/packages/explicit.txt" | sed "s|^|file://$APP/packages/|"; } > "$SPEC" || exit 1
rm -rf "$RT" "$WORK/.mamba-cache"
"$APP/micromamba" create --no-rc --offline --yes --always-copy --platform "$PLATFORM" \
  --root-prefix "$WORK/.mamba-cache" --prefix "$RT" --file "$SPEC" || { echo 'HATA: micromamba ortamı kuramadı'; exit 2; }
rm -rf "$WORK/.mamba-cache"
# Apple Silicon kills (signal 9) any binary whose signature no longer matches; micromamba writes
# the install path into some of them. Give every Mach-O file in the runtime a fresh ad-hoc signature.
resign(){
  find "$RT" -type f \( -perm -u+x -o -name '*.dylib' -o -name '*.so' \) -print0 | while IFS= read -r -d '' f; do
    case "$(file -b "$f")" in *Mach-O*) codesign --force --sign - "$f" >/dev/null 2>&1 || echo "imzalanamadı: $f";; esac
  done
}
resign
"$RT/bin/python" -c 'import sys' || { echo 'HATA: Python imzadan sonra da çalışmadı'; exit 5; }
"$RT/bin/python" -m pip install --no-index --find-links "$APP/wheels" 'faster-whisper==1.2.1' 'pypdf==6.21.2' || { echo 'HATA: konuşma/PDF paketleri kurulamadı'; exit 3; }
resign
"$RT/bin/python" -c 'import tkinter,faster_whisper,pypdf' || { echo 'HATA: Python ortamı eksik'; exit 4; }
echo "== tamam"
