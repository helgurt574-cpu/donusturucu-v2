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
