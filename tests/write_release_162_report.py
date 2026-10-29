from pathlib import Path
import json,re,hashlib,collections
BASE=Path(__file__).resolve().parents[1];root=BASE/'qa-1.6.2';coverage=json.loads((root/'coverage-three.json').read_text());audit=json.loads((root/'audit.json').read_text())
resolutions=coverage.get('resolved_harness_phases',{})
assert coverage['failures']==0 and all(r['status']=='pass' or resolutions.get(r['name'],{}).get('status')=='pass' for r in audit['phases'])
runs=[]
for n in range(1,4):
 text=(root/('regression-'+str(n)+'.log')).read_text();found=re.search(r'Ran (\d+) tests in ([\d.]+)s',text);assert found and re.search(r'\nOK\s*$',text),text[-1000:];runs.append({'round':n,'tests':int(found[1]),'seconds':float(found[2])})
unit=sum(r['tests'] for r in runs);real=coverage['conversion_cases']+coverage['supplement_cases']+coverage['gui_action_cases']+coverage['media_operation_cases']
supp=json.loads((root/'supplement/report.json').read_text());user=[r for r in supp['rows'] if r['option']=='reported-user-video'];assert len(user)==3 and all(r['pass'] and r['source_unchanged'] for r in user)
summary={'version':'1.6.2','platform':'Ubuntu 24.04 amd64','normal_desktop_context':True,'tested_app_root':audit['app_root'],'network_isolation':audit['isolation'],'real_conversion_editing_cases':real,'regression_cases':unit,'regression_rounds':runs,'additional_gui_flows':6,'minimum_repeats_per_option':coverage['minimum_successful_repeats'],'coverage_entries':coverage['covered_options'],'user_video_passes':3,'resolved_test_environment_phases':resolutions,'raw_phase_failures':audit['failures'],'failures':0}
(root/'release-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
report=f'''DÖNÜŞTÜRÜCÜ 1.6.2 — AMD64 LINUX — 24 Ekim 2026

DÜZELTİLENLER
1. Normal masaüstü oturumunda bubblewrap ağ ad alanı kuramıyordu.
   Program artık kullanılabilirliğini gerçek işlem bağlamında sınar.
   Bubblewrap kullanılamıyorsa libseccomp2 ile yardımcı süreçlerin
   AF_UNIX dışındaki soket aileleri engellenir. Yerel ofis/masaüstü IPC
   çalışır; sistem AppArmor/kernel güvenlik ayarı değiştirilmez.
   İki yöntem de kullanılamazsa kısıtsız çalıştırmak yerine hata verir.
2. Önceki DEBde bulunmayan Pandoc, PDF okuyucusu, Tesseract komutları
   ve beş OCR dil verisi artık AMD64 paketinin içindedir.
3. Ekran başlıkları 1.6.2; kurulum betiği eski kaynak klasörü kısayolunu
   yalnız önceki bilinen kısayolsa kurulu uygulamaya yönlendirir.

SON DEB İÇERİĞİYLE, NORMAL MASAÜSTÜ KULLANICI İZİNLERİNDE
- {coverage['conversion_cases']} gerçek kaynak/çıktı dönüşümü; programın üretebildiği
  giriş biçimlerinden uyumlu hedef biçimlere üçer tekrarlı matris.
- {coverage['supplement_cases']} ek seçenek: kalite, çözünürlük, yalnız metin, OCR dilleri,
  OCR çıktı biçimleri, sayfalar, dönüş açısı, hız ve ses düzeyi.
- {coverage['gui_action_cases']} gerçek arayüz düzenleme işlemi; video/ses/PDF için her işlem
  üç kez, Türkçe ve Kurmancî arayüz kullanılarak yürütüldü.
- {coverage['media_operation_cases']} farklı medya dosyası/aralığı düzenleme denemesi.
- {unit} regresyon kontrolü: {len(runs)} tur. Her turdaki test sayıları:
  {', '.join(str(r['tests']) for r in runs)}. Ayrıca üç GTK ve üç ek işlemler arayüz akışı.
- Sayılan {coverage['covered_options']} seçenek/kombinasyonun en az üç başarılı kaydı var.
- Bildirilen Android Platformunda Harita Uygulaması videosunun tamamı
  üç kez konuşma metnine çevrildi; kaynak SHA-256 değeri değişmedi.
- Her medya çıktısı tam çözüldü; belge dönüşüm çıktıları yeniden okunarak
  referans metin denetlendi. Süre, sayfa sayısı ve ilgili ses içeriği
  kontrolleri ayrıca yapıldı.

ÖNCEKİ DENEMELERİN SINIRI VE KAYDI
qa-1.6.2-attempt1: kurulum paketindeki eksik bileşenler bulundu.
qa-1.6.2-attempt2: yedek yolda ağ engelleme eksiği regresyonda bulundu.
Bu denemelerdeki başarılı sayılar nihai test sayılarına eklenmedi.
Nihai sayılar yalnız qa-1.6.2 altındaki son sürüm raporlarından gelir.
Ek arayüz turu 1 ilk ekran görüntüsünde QA Wayland/X11 seçimi yüzünden
hata verdi. Uygulama kodu değiştirilmeden QA ekranı düzeltildi, bütün
arayüz turu yeniden geçti. İlk hata ve başarılı tekrar ayrı tutuldu:
qa-1.6.2/resolved-phases.json ve extras-ui-1-retest.log.
Raw audit.json ilk ortam hatasını saklar; coverage-three.json çözülmemiş
hata kalmadığını ayrıca denetler.

SINIRLAR
Bu sonuç AMD64 Linux içindir. Windows/macOS/Android veya fiziksel ARM
cihaz testleri bu sayılara dahil değildir. Yeni/bozuk/farklı yapıdaki her
olası dosya için garanti değildir. Konuşma ve OCR testlerinin geçmesi
her kelimenin doğru tanındığını göstermez; otomatik metin gözden geçirilmelidir.
Testler DEBden çıkarılan uygulama kodu ve paket içi bileşenlerle yapıldı;
kurulu eski 1.6.1 pencereleri yeni kodu kullanmaz, kurulumdan sonra kapatılıp
uygulama yeniden açılmalıdır.

AYRINTILI KANITLAR
qa-1.6.2/release-summary.json
qa-1.6.2/coverage-three.json
qa-1.6.2/audit.json
qa-1.6.2/matrix/report.json
qa-1.6.2/supplement/report.json
qa-1.6.2/ui-all-actions/report.json
qa-1.6.2/operations/report.json
qa-1.6.2/regression-1.log, regression-2.log, regression-3.log
'''
(BASE/'TEST-SONUCLARI-1.6.2.txt').write_text(report);print(json.dumps(summary,ensure_ascii=False,indent=2))
