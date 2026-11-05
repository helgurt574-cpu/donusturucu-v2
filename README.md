# Dönüştürücü

Belgeleri, sesleri ve videoları internete yüklemeden dönüştüren masaüstü (Linux, Windows, macOS Apple Silicon) ve Android uygulaması.

- Belge, PDF, tablo, sunu, e-kitap, ses ve video dönüştürme
- Video/ses düzenleme: kes, birleştir, parçala, ses kapat/ekle, GIF, fotoğraf, döndür, hız
- Konuşmayı yazıya dökme (TXT/SRT), altyazıyı videoya ekleme (kalıcı veya ayrı iz)
- OCR (taranmış veya resim olarak gömülü yazılar)
- Aydınlık/karanlık tema, Türkçe ve Kurmancî arayüz

## Klasörler

| Klasör | İçerik |
| --- | --- |
| `donusturucu/` | Masaüstü uygulamasının kaynak kodu (GTK + Tk) |
| `android/` | Android uygulaması; `prepare_inputs.py` model ve kütüphaneleri indirir, `build_apk.py` APK üretir |
| `packaging/` | Windows, macOS ve Linux paketlerini üreten betikler |
| `tests/` | Masaüstü testleri ve gerçek örnek dosyalar |
| `assets/` | Yazı tipleri ve kendi kendine test dosyaları |

Kurulum ve kullanım için `KULLANIM.txt` dosyasına bakın. Hazır paketler bu depoda değil, Releases bölümündedir.

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
