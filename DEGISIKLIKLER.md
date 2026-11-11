# Değişiklikler

Sürümlere göre teknik notlar (en yenisi üstte).

## Android 1.4.4 ve Google Play

- Paket adı `com.donusturucu.app` (Java paketi `org.local.donusturucu` olarak kaldı; manifestte etkinlik adları tam yazılı), hedef API 36, Android 16 geri hareketi için `OnBackInvokedCallback`
- `android/build_aab.py`: Play için App Bundle. Önce `build_apk.py`'yi çalıştırır, sonra `base` modülü ve konuşma modelini taşıyan install-time asset pack `speech_models`'i bundletool ile birleştirir (bundletool Gradle önbelleğinden, ya da `BUNDLETOOL=/yol/bundletool-all.jar`), `signing/` anahtarıyla imzalar ve doğrular. Çıktı: `dist/Donusturucu-arm64.aab`
- Play mağaza metinleri, görseller ve gizlilik politikası depo dışında `../playstore/` klasöründe

## Android 1.4.2 – 1.4.3

- **Hızlı önizleme** (`QuickView.java`): Dosyalar uygulamasında dokununca seçim listesinde "Önizle" çıkar; dosya yöneticisinin üstünde alttan açılan panelde fotoğraf (yakınlaştırma), PDF ve Word/ODT/EPUB (kaydırarak sayfa geçişi), video, ses ve metin gösterilir; dışına dokunmak veya aşağı çekmek kapatır, tam ekran düğmesi var. "Dönüştür" dosyayı çalışma alanına aktarır, sonuçların "Aç" düğmesi de bu görüntüleyiciyi kullanır
- Yakınlaştırılabilir resim görünümü `Widgets.Zoom`
- 1.4.3: panelde önizleme dosyanın en/boy oranında büyür; altında donut biçim seçici ve araç kısayolları. Seçim `quick_action` / `quick_format` ile `MainActivity`'ye geçer: biçim hemen dönüştürülür, araç ayarlarıyla açılır

## Masaüstü (Linux) 1.9.0

- Yeni GTK penceresi `donusturucu/studio.py` (bileşenler `gtkui.py`); `app.main()` artık bunu açar, eski pencere `app.classic_main()` ile durur
- Yeni araçlar `studio_ops.py` (FFmpeg, pypdf, cairo, pdftoppm) ve `pdf_watermark.py`
- Android'deki tasarım ve özellikler: donut biçim seçici, araç ızgarası, Önizle, filigran silme, ses temizleme, küçültme, PDF sayfa araçları, fotoğraf
- Windows/macOS ve tarayıcı: aynı tasarımın HTML hâli `donusturucu/web/index.html`, yerel sunucu `donusturucu/webapp.py` (yalnız 127.0.0.1 ve rastgele anahtar). Masaüstü kipinde dosyalar yerinde okunur, sonuçlar kayıt klasörüne yazılır, sayfa Edge/Chrome uygulama penceresinde açılır; eski Tk penceresi `launch.py --tk` ile
- Başlat/Önizle mantığı `donusturucu/jobs.py`'de ortak; motor cairo gerektirmez (fotoğraftan PDF doğrudan yazılır)
- `browser-ui/server.py` artık `webapp.serve(desktop=False)` çağırır

## Android 1.4.0

- Yeni arayüz: Ana sayfa / Geçmiş / Ayarlar, dosya küçük resimleri, donut biçim seçici, araç ızgarası, vurgu rengi seçimi
- İşlemden önce **Önizle**: videoda kısa örnek klip ve tahmini boyut, seste orijinal/sonuç dinleme, PDF ve fotoğrafta önce/sonra kaydırıcısı
- **Filigran / logo silme**: video ve fotoğrafta alan çerçeveleyip çevreden doldurma veya bulanıklaştırma (FFmpeg `delogo`/`boxblur`); PDF'de filigran katmanı, açıklaması, yarı saydam eğik yazı veya verilen kelime otomatik silinir, gerekirse alan kapatılır (`PdfWatermark.java`)
- **Sesi temizle**: hışırtı (`afftdn`), cızırtı/tıkırtı (`adeclick`, `adeclip`), uğultu (`highpass`, `bandreject`), konuşmayı netleştirme ve ses seviyesi dengeleme (`loudnorm`); videoda görüntü kopyalanır
- Video ve PDF küçültme, PDF sayfa seçme/silme/sıralama/döndürme, PDF → PNG/JPG, fotoğraf → JPG/PNG/WEBP/BMP/PDF, fotoğraflardan PDF
- Cihaz testi: `adb shell am start -n org.local.donusturucu/.MainActivity --ez tools_test true` (`ToolsSelfTest.java`)
- Diğer dağıtımlar (masaüstü, HTML) değişmedi.
