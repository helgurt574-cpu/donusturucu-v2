#!/usr/bin/env bash
set -euo pipefail
base="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$base/donusturucu_1.3.0_all.deb" ]]; then
 package="$base/donusturucu_1.3.0_all.deb"
elif [[ -f "$base/dist/donusturucu_1.3.0_all.deb" ]]; then
 package="$base/dist/donusturucu_1.3.0_all.deb"
else
 echo 'Kurulum paketi bulunamadı.'; exit 1
fi
printf 'Dönüştür ve gerekli yerel araçlar kurulacak. Eksik bağımlılıkların ilk kurulumu internet isteyebilir.\n'
sudo apt-get install -y "$package"
local_launcher="$HOME/.local/share/applications/donusturucu.desktop"
if [[ -f "$local_launcher" ]] && grep -Fq "Exec=$base/baslat.sh" "$local_launcher"; then
 rm -- "$local_launcher"
fi
printf '\nKuruldu. Uygulamalar menüsünden Dönüştür uygulamasını açabilirsin.\n'
