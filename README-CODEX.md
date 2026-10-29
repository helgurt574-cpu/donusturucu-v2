CURRENT HANDOFF: desktop1.6.7, Windows1.6.7.1 candidate, Android1.2.0, browser1.6.7.1.
Generated speechSRT overlap fix: normalize millisecond boundaries, preserve recognized text; unit and real-video regression reports in qa-user-video-20261028-2. Android unchanged.
Recursive folder import and sequential batch operations implemented. See KULLANIM-KLASOR.txt and tests/test_folder_batch.py.
TXT/SRT speech output implemented. Desktop SRT decodes pause-separated utterances separately; Android uses chunk boundaries.
External translation workflow: SRT → one TXT line per cue → translate elsewhere → restore TXT using original SRT. Original cue numbers/times preserved; count mismatch rejected. No translation engine or translated-text ASR realignment.
See KULLANIM-ALTYAZI.txt, tests/test_subtitles.py, tests/test_speech_srt.py, donusturucu/subtitles.py and Android SubtitleFiles.java.
Native Windows/macOS and physical Android/ARM testing unavailable. Never present emulation/static archive checks as native device tests.
Dependencies/models/SDK/binary test fixtures/signing material intentionally excluded; provision dependencies and fixture files before full integration tests. Do not archive signing keys. Historical notes below may name older releases.

CURRENT HANDOFF: desktop1.6.7, Windows1.6.7.1 candidate, Android1.2.0, browser1.6.7.1.
Generated speechSRT overlap fix: normalize millisecond boundaries, preserve recognized text; unit and real-video regression reports in qa-user-video-20261028-2. Android unchanged.
Recursive folder import and sequential batch operations implemented. See KULLANIM-KLASOR.txt and tests/test_folder_batch.py.
TXT/SRT speech output implemented. Desktop SRT decodes pause-separated utterances separately; Android uses chunk boundaries.
External translation workflow: SRT → one TXT line per cue → translate elsewhere → restore TXT using original SRT. Original cue numbers/times preserved; count mismatch rejected. No translation engine or translated-text ASR realignment.
See KULLANIM-ALTYAZI.txt, tests/test_subtitles.py, tests/test_speech_srt.py, donusturucu/subtitles.py and Android SubtitleFiles.java.
Native Windows/macOS and physical Android/ARM testing unavailable. Never present emulation/static archive checks as native device tests.
Dependencies/models/SDK/binary test fixtures/signing material intentionally excluded; provision dependencies and fixture files before full integration tests. Do not archive signing keys. Historical notes below may name older releases.

CURRENT HANDOFF: desktop1.6.6, Windows1.6.6.1 candidate, Android1.2.0, browser1.6.6.1.
Recursive folder import and sequential batch operations implemented. See KULLANIM-KLASOR.txt and tests/test_folder_batch.py.
TXT/SRT speech output implemented. Desktop SRT decodes pause-separated utterances separately; Android uses chunk boundaries.
External translation workflow: SRT → one TXT line per cue → translate elsewhere → restore TXT using original SRT. Original cue numbers/times preserved; count mismatch rejected. No translation engine or translated-text ASR realignment.
See KULLANIM-ALTYAZI.txt, tests/test_subtitles.py, tests/test_speech_srt.py, donusturucu/subtitles.py and Android SubtitleFiles.java.
Native Windows/macOS and physical Android/ARM testing unavailable. Never present emulation/static archive checks as native device tests.
Dependencies/models/SDK/binary test fixtures/signing material intentionally excluded; provision dependencies and fixture files before full integration tests. Do not archive signing keys. Historical notes below may name older releases.

CURRENT HANDOFF: desktop1.6.6, Windows1.6.6.1 candidate, Android1.2.0, browser1.6.6.1.
Recursive folder import and sequential batch operations implemented. See KULLANIM-KLASOR.txt and tests/test_folder_batch.py.
TXT/SRT speech output implemented. Desktop SRT decodes pause-separated utterances separately; Android uses chunk boundaries.
External translation workflow: SRT → one TXT line per cue → translate elsewhere → restore TXT using original SRT. Original cue numbers/times preserved; count mismatch rejected. No translation engine or translated-text ASR realignment.
See KULLANIM-ALTYAZI.txt, tests/test_subtitles.py, tests/test_speech_srt.py, donusturucu/subtitles.py and Android SubtitleFiles.java.
Native Windows/macOS and physical Android/ARM testing unavailable. Never present emulation/static archive checks as native device tests.
Dependencies/models/SDK/binary test fixtures/signing material intentionally excluded; provision dependencies and fixture files before full integration tests. Do not archive signing keys. Historical notes below may name older releases.

CURRENT HANDOFF: desktop1.6.5, Windows1.6.5.1 candidate, Android1.1.9, browser1.6.5.1.
TXT/SRT speech output implemented. Desktop SRT decodes pause-separated utterances separately; Android uses chunk boundaries.
External translation workflow: SRT → one TXT line per cue → translate elsewhere → restore TXT using original SRT. Original cue numbers/times preserved; count mismatch rejected. No translation engine or translated-text ASR realignment.
See KULLANIM-ALTYAZI.txt, tests/test_subtitles.py, tests/test_speech_srt.py, donusturucu/subtitles.py and Android SubtitleFiles.java.
Native Windows/macOS and physical Android/ARM testing unavailable. Never present emulation/static archive checks as native device tests.
Dependencies/models/SDK/signing material intentionally excluded. Do not archive signing keys. Historical notes below may name older releases.

CURRENT HANDOFF: desktop1.6.5, Windows1.6.5.1 candidate, Android1.1.9, browser1.6.5.1.
TXT/SRT speech output implemented. Desktop SRT decodes pause-separated utterances separately; Android uses chunk boundaries.
External translation workflow: SRT → one TXT line per cue → translate elsewhere → restore TXT using original SRT. Original cue numbers/times preserved; count mismatch rejected. No translation engine or translated-text ASR realignment.
See KULLANIM-ALTYAZI.txt, tests/test_subtitles.py, tests/test_speech_srt.py, donusturucu/subtitles.py and Android SubtitleFiles.java.
Native Windows/macOS and physical Android/ARM testing unavailable. Never present emulation/static archive checks as native device tests.
Dependencies/models/SDK/signing material intentionally excluded. Do not archive signing keys. Historical notes below may name older releases.

# Dönüştürücü — geliştirme kaynakları

Bu klasörü Codex ile aç ve buradan geliştirmeye devam et.

## Son sürümler
- Masaüstü:1.6.3 — donusturucu/
- Android:1.1.7 — android/src/, android/res/, AndroidManifest.xml
- HTML/yerel sunucu:1.6.3.1 — browser-ui/
- Paketleme: build.py ve packaging/
- Test kaynakları: tests/, android/tests/, android/instrumentation/

## Önemli teknik durum
Türkçe ve Kurmancî arayüz, çevrimdışı çalışma ve orijinalleri koruma davranışını koru. HTML tek başına dönüştürmez; browser-ui/server.py mevcut motora bağlanan127.0.0.1 sunucusudur. BrowserRunner, sistem araçlarına PYTHONHOME/PYTHONPATH taşınmasını engeller. Masaüstü1.6.3 video kesme düzeltmesi kare sıklığı filtresinden sonra çıktı tarafında keser; uzun kesmeler daha yavaş olabilir. Android motoruna bu kesme düzeltmesi taşınmadı. Android listesi seçili dosyada işlem yapar; otomatik toplu kuyruk yoktur. HTML toplu dönüştürmeyi destekler. OCR/konuşma hatasız değildir; gürültülü Türkçe tanımada bilinen kayıplar vardır. Windows/macOS kurulumları içerik açısından doğrulandı, gerçek sistemlerde çalıştırılmadı. Kali gerçek sistem testi yapılmadı.

## Bu kaynak arşivinin kapsamı
Hazır uygulama/kurulum dosyaları, derleme çıktıları, SDK/JAR/wheel paketleri, üçüncü taraf programlar, Python ortamları, OCR/konuşma modelleri, test verisi koleksiyonları ve imza anahtarları dahil değildir. Kaynak değiştirilebilir; derlemek veya tüm testleri çalıştırmak için bağımlılık ve test verileri ayrıca hazırlanmalıdır. Derleme betikleri önceki çalışma alanındaki yerel cache/yolları varsayabilir; yeni bilgisayarda uyarlanmalıdır. Önce platformu ve eksik araçları tespit et. Eski bilgisayardaki mutlak yolları yeni bilgisayarda geçerli kabul etme. Arşivdeki dosyaların SHA256 listesi SOURCE-MANIFEST.json içindedir.

Python motoru: FFmpeg/FFprobe, LibreOffice, Pandoc, Poppler, pypdf; OCR için Tesseract/dil verileri; konuşma için faster-whisper ve yerel Whisper modeli. Linux ağ yalıtımı bubblewrap veya libseccomp2 ile yapılır; kısıtsız geri dönüş ekleme. HTML başlangıcı: python3 browser-ui/server.py. Masaüstü: baslat.sh. Android: android/build_apk.py, ayrıca Android araçları ve model bağımlılıkları gerekir. Özel imza anahtarını paylaşma; yeni cihazda kendi geliştirme anahtarını kullan.

Windows1.6.3.1 sonradan eklenen kurulum/başlatıcı tanılama adayıdır. Kullanıcı Windows kurulumunun gerçekleşmediğini bildirdi; neden henüz kesin değil. VBS yerine CMD başlatıcı, açılış hata kayıtları, Tk başlangıç kontrolü ve kurulum günlüğü eklendi. Gerçek Windows testi yoktur; sorun çözüldü kabul etme.

Windows1.6.3.1 sonradan eklenen kurulum/başlatıcı tanılama adayıdır. Kullanıcı Windows kurulumunun gerçekleşmediğini bildirdi; neden henüz kesin değil. VBS yerine CMD başlatıcı, açılış hata kayıtları, Tk başlangıç kontrolü ve kurulum günlüğü eklendi. Gerçek Windows testi yoktur; sorun çözüldü kabul etme.

2026-10-27: Desktop1.6.4 / Android1.1.8 TXT-SRT output selection. SRT uses original source timeline; Android cue timestamps use decoded chunk boundaries, not word timestamps. Native Windows/macOS untested. Models and SDKs intentionally excluded.
