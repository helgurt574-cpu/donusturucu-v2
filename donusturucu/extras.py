"""A separate, type-aware editing workspace; no controls added to conversion settings."""
from pathlib import Path
import argparse,os,queue,subprocess,sys,threading
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,font as tkfont
from . import core,runtime,theme,tktheme,VERSION
from .i18n import STRINGS
from .operations import Editor,Request,actions,OperationError

TEXT={
 'tr':{
 'title':'Farklı işlemler','intro':'Dosyanı seç; yalnız dosya türüne uygun işlemler gösterilir.',
 'add':'Dosya ekle','remove':'Kaldır','up':'Yukarı','down':'Aşağı','action':'Yapılacak işlem',
 'choose':'Seç','output':'Kaydedilecek yer','open':'Klasörü aç','run':'İşlemi başlat','stop':'Durdur',
 'start':'Başlangıç / videoya eklenecek saniye','end':'Bitiş (boş = dosyanın sonu)',
 'part':'Her parçanın süresi','pages':'Sayfa aralıkları (isteğe bağlı)','page_count':'Her parçada sayfa sayısı',
 'audio':'Eklenecek ses dosyası','audio_start':'Ses dosyasından alınacak başlangıç','audio_end':'Sesin bitiş zamanı (boş = son)',
 'factor':'Çarpan (0,5–2 hız; 0–3 ses düzeyi)','rotate_factor':'Dönüş açısı: 90 / 180 / 270',
 'segment':'Birleştirmede bu dosyadan kullanılacak bölüm','seg_start':'Başlangıç','seg_end':'Bitiş (boş = son)',
 'apply':'Aralığı kaydet','time_help':'Süre: 15, 01:15 veya 00:01:15.500 yazabilirsin. Aralık dışındaki bölümler, açıklamada aksi belirtilmedikçe korunur.',
 'pdf_hint':'Belge işlemleri PDF üretir. Sayfa düzeni korunur; DOCX/ODT çıktısı oluşturulmaz. Aralık örneği: 1-3;4-6;7,9 (noktalı virgül = ayrı dosya). Boşsa sayfa sayısına göre parçalanır.',
 'media_hint':'Video çıktısı MP4, ses çıktısı WAV olur. Hassas kesme/düzenleme yeniden kodlama gerektirir. Birleştirmede sıra listedeki gibidir; farklı videolar ilk videonun boyutuna uyarlanır.',
 'range_hint':'Başlangıç ve bitiş, ilk seçili dosyaya uygulanır. Birleştirmede her dosyanın aralığını listeden ayrı kaydet.',
 'only_hint':'Bu işlem yalnız seçili aralığı yeni dosyaya kaydeder.',
 'audio_hint':'Başlangıç/bitiş videodaki hedef aralığıdır. Sesin kendi bölümünü ayrıca seç. Ekle mevcut sesle karıştırır; değiştir yalnız hedef aralığın mevcut sesini susturur. Video süresi korunur.',
 'status_ready':'Hazır. Orijinal dosyalar değiştirilmez.','busy':'İşleniyor…','done':'İşlem tamamlandı.','cancelled':'İşlem durduruldu.','error':'İşlem yapılamadı','detected':'Dosyalar okunuyor…',
 'trim':'Seçili aralığı kaydet','remove_range':'Seçili aralığı çıkar','split':'Parçala','merge':'Birleştir',
 'mute_range':'Seçili aralıkta sesi sustur','mute':'Videonun tüm sesini kaldır','extract_audio':'Seçili aralığın sesini çıkar (MP3)',
 'add_audio':'Aralığa ses ekle / karıştır','replace_audio':'Aralıktaki sesi değiştir','frame':'Belirli saniyeyi resim olarak kaydet (PNG)',
 'gif':'Seçili aralıktan GIF oluştur','rotate':'Seçili aralığı döndür','speed':'Seçili aralığın hızını değiştir',
 'volume':'Seçili aralığın ses düzeyini değiştir','fade_in':'Aralıkta sesi yavaşça yükselt','fade_out':'Aralıkta sesi yavaşça azalt',
 'choose_file':'Önce bir dosya seç.','invalid_time':'Süreyi pozitif saniye veya saat:dakika:saniye olarak yaz.',
 'invalid_range':'Başlangıç bitişten küçük olmalı; bitiş dosya süresini aşamaz.','invalid_pages':'Sayfa aralığı veya parça sayfa sayısı geçersiz.',
 'need_two':'Birleştirmek için en az iki dosya ekle.','same_kind':'Yalnız aynı türden dosyaları birleştirebilirsin (belge, ses veya video).',
 'no_audio':'Bu dosyada ses akışı yok.','choose_audio':'Eklenecek dosya bir ses dosyası olmalı.','invalid_factor':'Geçerli çarpan veya dönüş açısı gir.',
 'too_many_parts':'En fazla 1000 parça oluşturulabilir; parça süresini artır.','empty_result':'İşlem sonunda dosyada içerik kalmıyor.',
 'range_too_short':'Seçilen aralıkta video karesi yok; aralığı genişlet veya daha erken bir saniye seç.','unknown_duration':'Bu dosyanın süresi okunamadı.','invalid_media':'Dosyanın ses/video bilgisi okunamadı.',
 'encrypted':'Şifreli PDF desteklenmiyor.','invalid_action':'Bu dosya için bu işlem kullanılamaz.',
 'close_busy':'İşlemi durdurup pencereyi kapatmak istiyor musun?','duration':'Süre','selected':'Seçili','choose_one':'Listeden bir dosya seç.',
 },
 'ku':{
 'title':'Karên din','intro':'Pela xwe hilbijêre; tenê karên guncaw tên nîşandan.',
 'add':'Pelê zêde bike','remove':'Rake','up':'Jor','down':'Jêr','action':'Karê ku bê kirin',
 'choose':'Hilbijêre','output':'Peldanka encamê','open':'Peldankê veke','run':'Karê dest pê bike','stop':'Rawestîne',
 'start':'Destpêk / saniyeya lêzêdekirina dengê','end':'Dawî (vala = dawiya pelê)',
 'part':'Demê her parçeyê','pages':'Navberên rûpelan (ne mecbûrî)','page_count':'Hejmara rûpelan di her parçeyê de',
 'audio':'Pela dengê ku bê zêdekirin','audio_start':'Destpêka parçeya dengê','audio_end':'Dawiya parçeya dengê (vala = dawî)',
 'factor':'Rêje (0,5–2 lez; 0–3 asta dengê)','rotate_factor':'Goşeya zivirandinê: 90 / 180 / 270',
 'segment':'Parçeya vê pelê ji bo yekbûnê','seg_start':'Destpêk','seg_end':'Dawî (vala = dawî)',
 'apply':'Navberê tomar bike','time_help':'Dem: 15, 01:15 an 00:01:15.500. Beşên li derveyî navberê tên parastin, heke ravekirin tiştekî din nebêje.',
 'pdf_hint':'Karên belgeyan PDF derdixin; ne DOCX/ODT. Mînak: 1-3;4-6;7,9 (her navbera bi ; veqetandî = pelek). Heke vala be, li gorî hejmara rûpelan tê parçekirin.',
 'media_hint':'Vîdyo wek MP4, deng wek WAV tê derxistin. Birîn û sererastkirin ji nû ve kodkirinê dixwaze. Rêz li gorî lîsteyê ye; mezinahî li gorî vîdyoya yekem tê guncandin.',
 'range_hint':'Destpêk/dawî li pela yekem tên sepandin. Di yekbûnê de navbera her pelê ji lîsteyê tomar bike.',
 'only_hint':'Ev kar tenê navbera hilbijartî di pelekî nû de tomar dike.',
 'audio_hint':'Destpêk/dawî navbera vîdyoyê ye. Parçeya dengê jî cuda hilbijêre. Lêzêdekirin deng tevlihev dike; guhertin tenê dengê navbera hilbijartî dişemitîne. Dema vîdyoyê tê parastin.',
 'status_ready':'Amade. Pelên orîjînal nayên guhertin.','busy':'Tê xebitandin…','done':'Kar qediya.','cancelled':'Kar hat rawestandin.','error':'Kar nehat kirin','detected':'Pel tên xwendin…',
 'trim':'Navbera hilbijartî tomar bike','remove_range':'Navbera hilbijartî rake','split':'Parçe bike','merge':'Yek bike',
 'mute_range':'Dengê navbera hilbijartî bêdeng bike','mute':'Hemû dengê vîdyoyê rake','extract_audio':'Dengê navbera hilbijartî derxe (MP3)',
 'add_audio':'Dengê li navberê zêde / tevlihev bike','replace_audio':'Dengê navberê biguherîne','frame':'Saniyeyeke wek wêne tomar bike (PNG)',
 'gif':'Ji navbera hilbijartî GIF çêke','rotate':'Navbera hilbijartî bizivirîne','speed':'Leza navbera hilbijartî biguherîne',
 'volume':'Asta dengê navbera hilbijartî biguherîne','fade_in':'Dengê di navberê de hêdî bilind bike','fade_out':'Dengê di navberê de hêdî kêm bike',
 'choose_file':'Pêşî pelekê hilbijêre.','invalid_time':'Demê bi saniye an demjimêr:deqe:saniye binivîse.',
 'invalid_range':'Destpêk divê ji dawiyê biçûktir be û navber di dema pelê de be.','invalid_pages':'Navbera rûpelan an hejmara rûpelan ne derbasdar e.',
 'need_two':'Ji bo yekbûnê herî kêm du pel zêde bike.','same_kind':'Tenê pelên heman cureyê yek bike (belge, deng an vîdyo).',
 'no_audio':'Di vê pelê de deng tune.','choose_audio':'Pela lêzêdekirinê divê pela dengê be.','invalid_factor':'Rêje an goşeyeke derbasdar binivîse.',
 'too_many_parts':'Herî zêde 1000 parçe; dema parçeyê zêde bike.','empty_result':'Piştî karê naverok namîne.',
 'range_too_short':'Di navberê de çarçoveya vîdyoyê tune; navberê fireh bike an demeke zûtir hilbijêre.','unknown_duration':'Dema pelê nehat xwendin.','invalid_media':'Agahiyên deng/vîdyoyê nehatin xwendin.',
 'encrypted':'PDF bi şîfre nayê piştgirîkirin.','invalid_action':'Ev kar ji bo vê pelê tune.',
 'close_busy':'Karê rawestînî û pencereyê bigirî?','duration':'Dem','selected':'Hilbijartî','choose_one':'Pelek ji lîsteyê hilbijêre.',
 }}

# Short, familiar action names; details are explained beneath the selection.
TEXT['tr'].update({
 'pick_operation':'Ne yapmak istiyorsun?','pick_operation_help':'Soldan bir işlem seç. Ardından o işlem için kullanacağın dosyayı seçebilirsin.',
 'pick_file':'İşlem yapılacak dosyayı seç','change_video':'Başka video seç','change_audio':'Başka ses dosyası seç','change_document':'Başka belge seç',
 'pick_more':'Birleştirilecek dosyaları seç','remove_join':'Birleştirmeden çıkar','join_order':'Birleştirme sırası','details':'İşlem ayrıntılarını göster / gizle','transcribe':'Konuşmayı yazıya dök','speech_format':'Çıktı biçimi (TXT / SRT)','speech_language':'Konuşmanın dili','speech_model_missing':'Konuşma modeli bu bilgisayarda hazır değil. Yerel konuşma paketini kur.','speech_engine_missing':'Konuşma tanıma motoru bu bilgisayarda hazır değil. Yerel konuşma paketini kur.','speech_language_invalid':'Türkçe veya English seç.','speech_no_text':'Bu bölümde konuşma algılanmadı. Başka bir zaman aralığı dene.','browse_audio':'Ses dosyası seç','change_output':'Kayıt yerini değiştir',
 'remove':'Dosyayı listeden çıkar','up':'Sırada öne al','down':'Sırada arkaya al',
 'action':'Ne yapmak istiyorsun?','start':'Başlangıç zamanı','end':'Bitiş zamanı (boş bırakırsan sona kadar)',
 'trim':'Kes','remove_range':'Bir bölüm sil','split':'Parçalara ayır','merge':'Birleştir',
 'mute_range':'Bir bölümün sesini kapat','mute':'Videoyu sessiz yap','extract_audio':'Sesi çıkar (MP3 olarak kaydet)',
 'add_audio':'Ses ekle','replace_audio':'Videonun sesini değiştir','frame':'Videodan fotoğraf al',
 'gif':'GIF oluştur','rotate':'Videoyu döndür','speed':'Hızı değiştir','volume':'Ses düzeyini değiştir',
 'fade_in':'Sesi yavaşça aç','fade_out':'Sesi yavaşça kıs',
 'segment':'Bu dosyanın hangi bölümünü birleştirelim?','apply':'Aralığı uygula',
 'time_help':'Örnek: 15 = 15. saniye, 01:30 = 1 dakika 30 saniye.',
 'whole_file':'Dosyanın tamamı','custom_range':'Başlangıç ve bitiş zamanı seç',
 'custom_audio':'Eklenecek sesin yalnız bir bölümünü kullan','custom_pages':'Sayfa aralıklarını kendim seçeceğim',
 'insert_start':'Ses videoya ne zaman girsin?','insert_end':'Sesin videodaki bitişi (boş = son)' ,
 'frame_time':'Kaçıncı saniyenin fotoğrafı alınsın?',
 'audio_start':'Eklenecek sesin başlangıç zamanı','audio_end':'Eklenecek sesin bitiş zamanı (boş = sesin sonu)',
 'part':'Her parça kaç saniye olsun?','speed_factor':'Hız (0,5 = yavaş; 1 = normal; 2 = hızlı)',
 'volume_factor':'Ses düzeyi (0 = sessiz; 1 = normal; 2 = iki kat)',
 'merge_help':'Dosyalar listedeki sırayla birleştirilir. Sırayı değiştirmek için dosyayı seçip Sırada öne al / Sırada arkaya al düğmesine bas.',
 'merge_audio_help':'Sesler listedeki sırayla art arda eklenir; aynı anda çalınmaz.',
 'page_help':'Her parçada sayfa sayısını yaz veya sayfa aralıklarını belirt: 1-3;4-6 → iki PDF. Sonuç PDF olarak kaydedilir.',
 'pdf_merge_help':'Belgeler listedeki sırayla tek PDF olur. Sırayı değiştirmek için dosyayı seçip Sırada öne al / Sırada arkaya al düğmesine bas.',
})
TEXT['ku'].update({
 'pick_operation':'Tu dixwazî çi bikî?','pick_operation_help':'Ji çepê karek hilbijêre. Piştre pela ji bo wî karî hilbijêre.',
 'pick_file':'Pela karê hilbijêre','change_video':'Vîdyoyeke din hilbijêre','change_audio':'Pela dengekî din hilbijêre','change_document':'Belgeyeke din hilbijêre',
 'pick_more':'Pelên yekbûnê hilbijêre','remove_join':'Ji yekbûnê derxe','join_order':'Rêza yekbûnê','details':'Hûrguliyan nîşan bide / veşêre','transcribe':'Axaftinê bike nivîs','speech_format':'Formata encamê (TXT / SRT)','speech_language':'Zimanê axaftinê','speech_model_missing':'Modela axaftinê amade nîne. Pakêta herêmî saz bike.','speech_engine_missing':'Motora axaftinê amade nîne. Pakêta herêmî saz bike.','speech_language_invalid':'Türkçe an English hilbijêre.','speech_no_text':'Di vê beşê de axaftin nehat nasîn. Navbereke din biceribîne.','browse_audio':'Pela dengê hilbijêre','change_output':'Cihê tomarkirinê biguherîne',
 'remove':'Pelê ji lîsteyê derxe','up':'Pêşî yek bike','down':'Paşê yek bike',
 'action':'Tu dixwazî çi bikî?','start':'Dema destpêkê','end':'Dema dawiyê (vala = dawiya pelê)',
 'trim':'Bibire','remove_range':'Beşekê jê bibe','split':'Parçe bike','merge':'Yek bike',
 'mute_range':'Dengê beşekê bigire','mute':'Vîdyoyê bêdeng bike','extract_audio':'Deng derxe (MP3)',
 'add_audio':'Deng zêde bike','replace_audio':'Dengê vîdyoyê biguherîne','frame':'Ji vîdyoyê wêne bigire',
 'gif':'GIF çêke','rotate':'Vîdyoyê bizivirîne','speed':'Lezê biguherîne','volume':'Asta dengê biguherîne',
 'fade_in':'Dengê hêdî veke','fade_out':'Dengê hêdî kêm bike',
 'segment':'Kîjan beşa vê pelê yek bikin?','apply':'Beşa vê pelê tomar bike',
 'time_help':'Mînak: 15 = saniyeya 15, 01:30 = deqeyek û 30 saniye.',
 'whole_file':'Hemû pel','custom_range':'Tenê beşekê bi kar bîne','custom_audio':'Tenê beşek ji dengê lêzêdekirinê bi kar bîne','custom_pages':'Ez ê navberên rûpelan hilbijêrim',
 'insert_start':'Deng kengî bikeve vîdyoyê?','insert_end':'Deng di vîdyoyê de kengî biqede? (vala = dawî)',
 'frame_time':'Wêne ji kîjan saniyeyê bê girtin?',
 'audio_start':'Destpêka dengê lêzêdekirinê','audio_end':'Dawiya dengê lêzêdekirinê (vala = dawî)',
 'part':'Her parçe çend saniye be?','speed_factor':'Lez (0,5 = hêdî; 1 = normal; 2 = bilez)',
 'volume_factor':'Asta dengê (0 = bêdeng; 1 = normal; 2 = du qat)',
 'merge_help':'Pel li gorî rêza lîsteyê yek dibin. Pelê hilbijêre û bi Pêşî yek bike / Paşê yek bike rêzê biguherîne.',
 'merge_audio_help':'Deng li pey hev têne zêdekirin; ne di heman demê de.',
 'page_help':'Hejmara rûpelan an navberan binivîse: 1-3;4-6 → du PDF. Encam PDF e.',
 'pdf_merge_help':'Belge li gorî rêza lîsteyê di PDFekê de yek dibin. Bi Pêşî yek bike / Paşê yek bike rêzê biguherîne.',
})
for _lang,_strings in {
 'tr':{'subtitle_text':'SRT → TXT (çeviri için)','subtitle_restore':'Çevrilmiş TXT → SRT','subtitle_original':'Orijinal SRT dosyası (zaman kodları)','subtitle_text_help':'Her altyazı bölümü TXT’de tek satır olur. Çeviri ayrı programda yapılır. Çevirirken satır sayısını ve sırasını koru; orijinal SRT dosyasını sakla.','subtitle_restore_help':'Çevrilmiş TXT ve orijinal SRT dosyasını seç. Orijinal zaman kodları aynen korunur; çeviri veya yeni zamanlama yapılmaz. Her altyazı için tek satır bulunmalı.','subtitle_line_count':'TXT satır sayısı orijinal SRT ile aynı olmalı. Çeviride satırları birleştirme, bölme veya boş bırakma.','subtitle_invalid':'SRT biçimi veya zaman kodları geçersiz.','subtitle_original_required':'Zamanları korumak için orijinal SRT dosyasını seç.'},
 'ku':{'subtitle_text':'SRT → TXT (ji bo wergerê)','subtitle_restore':'TXT ya wergerandî → SRT','subtitle_original':'Pela SRT ya orîjînal (demkod)','subtitle_text_help':'Her beşa binivîsê di TXT de rêzek e. Di bernameyeke din de wergerîne; hejmara rêzan û rêzê biparêze. SRT ya orîjînal biparêze.','subtitle_restore_help':'TXT ya wergerandî û SRT ya orîjînal hilbijêre. Demkodên orîjînal tên parastin; werger an demkirina nû nayê kirin.','subtitle_line_count':'Hejmara rêzên TXT û SRT divê yek be. Rêzan yek neke, parçe neke û vala nehêle.','subtitle_invalid':'Formata SRT an demkod ne rast in.','subtitle_original_required':'Ji bo parastina deman SRT ya orîjînal hilbijêre.'}
}.items():TEXT[_lang].update(_strings)
for _lang,_strings in {
 'tr':{'action_not_for_file':'“{action}” bu dosyaya uygulanamaz ({kind}). Bu dosya için yapılabilecek işlemler solda listelendi.','video_files':'Video dosyaları','media_files':'Ses ve video dosyaları','dialog_cancel':'İptal','no_file':'Henüz dosya seçilmedi','use_last_srt':'Son SRT’yi kullan','clear_file':'Kaldır','change_file':'Değiştir',
  'busy_percent':'İşleniyor… %{percent}','busy_eta':' · yaklaşık {eta} kaldı','minutes':'{m} dk {s} sn','seconds_only':'{s} sn','all_files':'Tüm dosyalar',
  'add_subtitle':'Altyazıyı videoya ekle','subtitle_file':'Altyazı dosyası (SRT / ASS / VTT)','browse_subtitle':'Altyazı dosyası seç',
  'subtitle_mode':'Altyazı nasıl eklensin?','subtitle_burn':'Kalıcı (görüntüye yazılır)','subtitle_soft':'Açılıp kapatılabilir (ayrı iz)',
  'choose_subtitle':'Zaman kodlu geçerli bir altyazı dosyası (SRT, ASS veya VTT) seç.','subtitle_ready':'Son oluşturulan SRT bu işlem için hazır: {name}',
  'log_empty':'Henüz işlem yapılmadı. Bir işlem başlattığında hangi dosyanın işlendiği, nereye kaydedildiği, süresi ve olası hatalar burada görünür.',
  'log_start':'▶ {time} · {action} başladı','log_files':'  Dosya: {files}','log_output':'  Kayıt yeri: {folder}','log_elapsed':'  Süre: {seconds} sn',
  'log_failed':'✕ İşlem yapılamadı: {error}','log_cancelled':'■ Durduruldu'},
 'ku':{'action_not_for_file':'“{action}” bi vê pelê nabe ({kind}). Karên ku bi vê pelê dibin li çepê hatin rêzkirin.','video_files':'Pelên vîdyoyê','media_files':'Pelên deng û vîdyoyê','dialog_cancel':'Betal','no_file':'Hîn pel nehatiye hilbijartin','use_last_srt':'SRT ya dawî bi kar bîne','clear_file':'Rake','change_file':'Biguherîne',
  'busy_percent':'Tê xebitandin… %{percent}','busy_eta':' · nêzî {eta} maye','minutes':'{m} deq {s} çirk','seconds_only':'{s} çirk','all_files':'Hemû pel',
  'add_subtitle':'Binnivîsê li vîdyoyê zêde bike','subtitle_file':'Pela binnivîsê (SRT / ASS / VTT)','browse_subtitle':'Pela binnivîsê hilbijêre',
  'subtitle_mode':'Binnivîs çawa bê zêdekirin?','subtitle_burn':'Mayînde (li ser wêneyê tê nivîsandin)','subtitle_soft':'Vekirin/girtin dibe (rêza cuda)',
  'choose_subtitle':'Pela binnivîsê ya derbasdar bi demkodan (SRT, ASS an VTT) hilbijêre.','subtitle_ready':'SRT ya dawî ji bo vî karî amade ye: {name}',
  'log_empty':'Hîn kar nehatiye kirin. Dema karekî dest pê bikî, pel, cihê tomarkirinê, dem û çewtî li vir xuya dibin.',
  'log_start':'▶ {time} · {action} dest pê kir','log_files':'  Pel: {files}','log_output':'  Cihê tomarkirinê: {folder}','log_elapsed':'  Dem: {seconds} çirk',
  'log_failed':'✕ Kar nehat kirin: {error}','log_cancelled':'■ Hat rawestandin'},
}.items():TEXT[_lang].update(_strings)
TEXT['tr'].update(add_folder='Klasör ekle (alt klasörlerle)',batch_all='Listedeki uygun dosyaların tümüne uygula',remove_batch='Dosyayı listeden çıkar',batch_list='Dosya listesi',batch_issues='Atlanan / hatalı dosya')
TEXT['ku'].update(add_folder='Peldankê zêde bike (bi binpeldankan)',batch_all='Li hemû pelên guncav ên lîsteyê bi kar bîne',remove_batch='Pela ji lîsteyê derxe',batch_list='Lîsteya pelan',batch_issues='Pelên derbaskirî / çewt')

HELP={
 'tr':{
 'transcribe':'TXT düz metin veya SRT zaman kodlu altyazı seç. SRT zamanları kaynak videoya göredir. Türkçe veya İngilizce seç; dosyanın tamamını ya da bir bölümünü kullanabilirsin. Metni sonradan çevirebilirsin. Otomatik metni dinleyerek kontrol et.',
 'trim':'Başlangıç ve bitiş arasındaki bölümü ayrı bir dosya olarak kaydeder.',
 'remove_range':'Belirttiğin bölümü siler; öncesini ve sonrasını birleştirir.',
 'split':'Dosyayı belirttiğin uzunlukta ayrı parçalara ayırır.',
 'mute_range':'Yalnız belirttiğin bölümde sesi kapatır. Görüntü ve diğer bölümlerdeki ses kalır.',
 'mute':'Görüntüyü korur ve videonun tamamındaki sesi kaldırır.',
 'extract_audio':'Videonun sesini ayrı bir MP3 dosyasına kaydeder. İstersen yalnız bir bölümünü alabilirsin.',
 'add_audio':'Seçtiğin sesi videoya ekler. Videonun mevcut sesi de çalmaya devam eder.',
 'replace_audio':'Belirttiğin bölümün mevcut sesini kapatıp yerine seçtiğin sesi koyar. Diğer bölümlerin sesi kalır.',
 'frame':'Belirttiğin zamandaki görüntüyü PNG fotoğraf olarak kaydeder.',
 'gif':'Seçtiğin bölümden sessiz, hareketli bir GIF oluşturur.',
 'rotate':'Videoyu seçtiğin açıyla döndürür. İstersen yalnız bir bölümünü yeni dosyaya alabilirsin.',
 'speed':'Videoyu veya sesi yavaşlatır/hızlandırır. Yalnız bölüm seçersen diğer bölümlerin hızı kalır.',
 'volume':'Ses düzeyini değiştirir. Yalnız bölüm seçersen diğer bölümlerin ses düzeyi kalır.',
 'fade_in':'Belirttiğin bölümde ses, sessizlikten normal düzeyine doğru yükselir.',
 'fade_out':'Belirttiğin bölümde ses, normal düzeyinden sessizliğe doğru azalır.',
 'add_subtitle':'SRT, ASS veya VTT altyazıyı videoya ekler; sonuç MP4 olur. Kalıcı seçenekte yazı görüntünün parçası olur ve her oynatıcıda, telefonda, sosyal medyada görünür; video yeniden kodlandığı için biraz sürer. Açılıp kapatılabilir seçenekte altyazı ayrı iz olarak eklenir, çok hızlıdır ve kalite kaybı olmaz; oynatıcıdan açılması gerekir. Önce Konuşmayı yazıya dök ile SRT çıkarabilirsin.',
 },
 'ku':{
 'transcribe':'TXT nivîsa sade an SRT binivîsa bi deman hilbijêre. Demên SRT li gor çavkaniyê ne. Türkçe an English hilbijêre. Hemû pel an beşek hilbijêre; piştre dikarî nivîsê wergerînî. Nivîsa bixweber kontrol bike.',
 'trim':'Beşa di navbera destpêk û dawiyê de di pelekî cuda de tomar dike.',
 'remove_range':'Beşa diyarkirî jê dibe; pêş û paşê yek dike.',
 'split':'Pelê li gorî dema diyarkirî li parçe dike.',
 'mute_range':'Tenê dengê beşa diyarkirî digire. Wêne û dengê beşên din dimînin.',
 'mute':'Wêneyê diparêze û hemû dengê vîdyoyê radike.',
 'extract_audio':'Dengê vîdyoyê di MP3ekê de tomar dike. Tu dikarî tenê beşekê hilbijêrî.',
 'add_audio':'Dengê hilbijartî li vîdyoyê zêde dike. Dengê berê jî didome.',
 'replace_audio':'Dengê beşa diyarkirî digire û dengê hilbijartî li şûna wê datîne. Dengê beşên din dimîne.',
 'frame':'Wêneya dema diyarkirî wek PNG tomar dike.',
 'gif':'Ji beşa hilbijartî GIFeke hereketdar û bêdeng çêdike.',
 'rotate':'Vîdyoyê li gorî goşeyê dizivirîne. Tu dikarî tenê beşekê di pelekî nû de tomar bikî.',
 'speed':'Leza vîdyo an dengê diguherîne. Heke beşek hilbijêrî, leza beşên din dimîne.',
 'volume':'Asta dengê diguherîne. Heke beşek hilbijêrî, asta beşên din dimîne.',
 'fade_in':'Dengê di beşa diyarkirî de hêdî ji bêdengiyê bilind dike.',
 'fade_out':'Dengê di beşa diyarkirî de hêdî ber bi bêdengiyê kêm dike.',
 'add_subtitle':'Binnivîsa SRT, ASS an VTT li vîdyoyê zêde dike; encam MP4 e. Di vebijarka mayînde de nivîs dibe beşek ji wêneyê û li her derê xuya dibe; ji ber kodkirina nû demek digire. Di vebijarka vekirin/girtinê de binnivîs wek rêzeke cuda tê zêdekirin, pir bilez e û kalîte kêm nabe. Pêşî bi Axaftinê bike nivîs SRT derxe.',
 }}

PERCENT_ACTIONS={'transcribe','add_subtitle','mute','add_audio','replace_audio','mute_range','volume','fade_in','fade_out'}

def clock(value):
    from .operations import seconds
    total=seconds(value);hours=int(total//3600);minutes=int(total%3600//60);secs=total%60
    text=f'{hours:02}:{minutes:02}:{secs:06.3f}'.rstrip('0').rstrip('.')
    return text

class ExtraWindow(tk.Toplevel):
    def __init__(self,owner,language='tr',source=None,output=None,theme_name=None):
        super().__init__(owner);self.lang=language if language in TEXT else 'tr'
        self.title(self.t('title'));self.geometry('1080x820');self.minsize(960,700)
        style=ttk.Style(self)
        if style.theme_use()!='clam':style.theme_use('clam')
        self.font=tktheme.pick_font(self)
        self.surfaces=[];self.text_widgets=[];self.theme_name=None;self.theme_tick=0
        self.apply_theme(theme_name if theme_name in theme.PALETTES else theme.resolve(theme.stored_mode()))
        self.files=[];self.ranges=[];self.info=None;self.running=False;self.detecting=False;self.runner=None;self.events=queue.Queue();self.closing=False
        self.output=Path(output or Path.home()/'Dönüştürülenler');self.last_selected=None;self.action_ids=[]
        self.vars={k:tk.StringVar(value=v) for k,v in {'start':'0','end':'','part':'60','pages':'','page_count':'1','audio':'','audio_start':'0','audio_end':'','factor':'1','speech_language':'Türkçe','speech_format':'TXT','subtitle_mode':self.t('subtitle_burn')}.items()}
        self.last_srt=None;self.started_at=0
        self.batch_all=tk.BooleanVar(value=False);self.fields={};self.field_labels={};self.mutable=[];self.order_buttons=[]
        self.use_range=tk.BooleanVar(value=False);self.use_audio_range=tk.BooleanVar(value=False)
        self.pending_action=None;self.build();self.show_fields();self.protocol('WM_DELETE_WINDOW',self.close);self.after(80,self.poll)
        if source:self.add_paths([source])
    def t(self,k):return TEXT[self.lang].get(k,k)
    def build(self):
        shell=ttk.Frame(self,padding=16,style='Extra.TFrame');shell.pack(fill='both',expand=True)
        menu=ttk.Frame(shell,style='Extra.TFrame',width=270);menu.pack(side='left',fill='y',padx=(0,18));menu.pack_propagate(False)
        ttk.Label(menu,text=self.t('title'),style='Title.TLabel').pack(anchor='w',pady=(0,12))
        menu_canvas=tk.Canvas(menu,highlightthickness=0);self.surfaces.append(menu_canvas)
        menu_scroll=ttk.Scrollbar(menu,orient='vertical',command=menu_canvas.yview);menu_scroll.pack(side='right',fill='y')
        menu_canvas.configure(yscrollcommand=menu_scroll.set);menu_canvas.pack(side='left',fill='both',expand=True)
        menu_content=ttk.Frame(menu_canvas,style='Extra.TFrame');menu_window=menu_canvas.create_window((0,0),window=menu_content,anchor='nw')
        menu_content.bind('<Configure>',lambda e:menu_canvas.configure(scrollregion=menu_canvas.bbox('all')))
        menu_canvas.bind('<Configure>',lambda e:menu_canvas.itemconfigure(menu_window,width=e.width))
        self.menu=menu_content;self.menu_buttons={};self.menu_signature=None
        container=ttk.Frame(shell,style='Extra.TFrame');container.pack(side='left',fill='both',expand=True)
        canvas=tk.Canvas(container,highlightthickness=0);self.surfaces.append(canvas)
        scrollbar=ttk.Scrollbar(container,orient='vertical',command=canvas.yview);scrollbar.pack(side='right',fill='y')
        canvas.configure(yscrollcommand=scrollbar.set);canvas.pack(side='left',fill='both',expand=True)
        outer=ttk.Frame(canvas,style='Extra.TFrame');window=canvas.create_window((0,0),window=outer,anchor='nw')
        outer.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
        self.operation_title=ttk.Label(outer,text=self.t('pick_operation'),style='Title.TLabel');self.operation_title.pack(anchor='w',pady=(0,8))
        self.hint=ttk.Label(outer,style='Extra.TLabel',wraplength=580,justify='left');self.hint.pack(anchor='w',pady=(0,14))
        self.source_card=ttk.Frame(outer,style='Card.TFrame',padding=(14,12));self.source_card.pack(fill='x',pady=(0,10))
        self.source_label=ttk.Label(self.source_card,style='CardTitle.TLabel',text=self.t('no_file'));self.source_label.pack(anchor='w')
        self.source_meta=ttk.Label(self.source_card,style='CardMeta.TLabel',text='');self.source_meta.pack(anchor='w',pady=(2,8))
        self.source_buttons=ttk.Frame(self.source_card,style='CardInner.TFrame');self.source_buttons.pack(anchor='w')
        self.pick_button=ttk.Button(self.source_buttons,style='Extra.TButton',text=self.t('pick_file'),command=self.choose_single);self.pick_button.pack(side='left',padx=(0,8));self.mutable.append(self.pick_button)
        self.merge_panel=ttk.LabelFrame(outer,text=self.t('join_order'),padding=9,style='Extra.TLabelframe')
        self.listbox=tk.Listbox(self.merge_panel,height=4,exportselection=False);self.text_widgets.append(self.listbox);self.listbox.pack(fill='x');self.listbox.bind('<<ListboxSelect>>',self.selected)
        bar=ttk.Frame(self.merge_panel,style='Extra.TFrame');bar.pack(fill='x',pady=(7,0))
        self.list_controls={}
        for n,(label,cmd) in enumerate([('pick_more',self.choose),('remove_join',self.remove),('up',lambda:self.move(-1)),('down',lambda:self.move(1))]):
            button=ttk.Button(bar,style='Extra.TButton',text=self.t(label),command=cmd);button.grid(row=n//2,column=n%2,sticky='ew',padx=3,pady=3);self.mutable.append(button);self.list_controls[label]=button
        bar.columnconfigure(0,weight=1);bar.columnconfigure(1,weight=1)
        self.add_folder_button=ttk.Button(self.source_buttons,text=self.t('add_folder'),command=self.choose_folder,style='Extra.TButton');self.add_folder_button.pack(side='left');self.mutable.append(self.add_folder_button)
        self.batch_toggle=ttk.Checkbutton(outer,text=self.t('batch_all'),variable=self.batch_all,command=self.show_fields);self.mutable.append(self.batch_toggle)
        self.action=ttk.Combobox(outer,state='readonly')  # Internal selection model; actions are visible buttons.
        self.range_toggle=ttk.Checkbutton(outer,text=self.t('custom_range'),variable=self.use_range,command=self.show_fields)
        self.audio_toggle=ttk.Checkbutton(outer,text=self.t('custom_audio'),variable=self.use_audio_range,command=self.show_fields)
        self.mutable.extend([self.range_toggle,self.audio_toggle])
        self.form=ttk.Frame(outer,style='Extra.TFrame');self.form.pack(fill='x',pady=8)
        labels={'factor':'factor'}
        for key in self.vars:
            row=ttk.Frame(self.form,style='Extra.TFrame');self.fields[key]=row
            label=ttk.Label(style='Extra.TLabel',master=row,text=self.t(labels.get(key,key)),width=35,wraplength=235);label.pack(side='left');
            self.field_labels[key]=label
            if key=='factor':self.factor_label=label
            if key=='audio':
                self.build_file_card(row);continue
            entry=ttk.Combobox(row,textvariable=self.vars[key],values=[self.t('subtitle_burn'),self.t('subtitle_soft')],state='readonly') if key=='subtitle_mode' else ttk.Combobox(row,textvariable=self.vars[key],values=['Türkçe','English'],state='readonly') if key=='speech_language' else ttk.Combobox(row,textvariable=self.vars[key],values=['TXT','SRT'],state='readonly') if key=='speech_format' else ttk.Entry(style='Extra.TEntry',master=row,textvariable=self.vars[key])
            if key=='speech_language':self.speech_combo=entry
            if key=='speech_format':self.speech_format_combo=entry
            if key=='subtitle_mode':self.subtitle_mode_combo=entry
            entry.pack(side='left',fill='x',expand=True);self.mutable.append(entry)
        self.segment=ttk.LabelFrame(outer,text=self.t('segment'),padding=7,style='Extra.TLabelframe')
        self.seg_start=tk.StringVar(value='0');self.seg_end=tk.StringVar(value='')
        for key,var in [('seg_start',self.seg_start),('seg_end',self.seg_end)]:
            ttk.Label(style='Extra.TLabel',master=self.segment,text=self.t(key)).pack(side='left');e=ttk.Entry(style='Extra.TEntry',master=self.segment,textvariable=var,width=12);e.pack(side='left',padx=6);self.mutable.append(e)
        b=ttk.Button(self.segment,style='Extra.TButton',text=self.t('apply'),command=self.save_range);b.pack(side='right');self.mutable.append(b)
        folder=ttk.Frame(outer,style='Extra.TFrame');folder.pack(fill='x',pady=6)
        ttk.Label(style='Extra.TLabel',master=folder,text=self.t('output')+':').pack(side='left')
        self.folder_label=ttk.Label(style='Extra.TLabel',master=folder,text=str(self.output),wraplength=340);self.folder_label.pack(side='left',fill='x',expand=True,padx=6)
        b=ttk.Button(folder,style='Extra.TButton',text=self.t('change_output'),command=self.choose_output);b.pack(side='right');self.mutable.append(b)
        ttk.Button(folder,style='Extra.TButton',text=self.t('open'),command=self.open_output).pack(side='right',padx=5)
        self.progress=ttk.Progressbar(outer,mode='determinate',maximum=1,value=0);self.progress.pack(fill='x',pady=7)
        self.status=ttk.Label(style='Extra.TLabel',master=outer,text=self.t('status_ready'),wraplength=810);self.status.pack(anchor='w')
        buttons=ttk.Frame(outer,style='Extra.TFrame');buttons.pack(fill='x',pady=6)
        self.run_button=ttk.Button(buttons,style='Accent.TButton',text=self.t('run'),command=self.run);self.run_button.pack(side='right')
        self.stop_button=ttk.Button(buttons,text=self.t('stop'),command=self.cancel,style='ExtraStop.TButton',state='disabled');self.stop_button.pack(side='right',padx=8)
        self.log=tk.Text(outer,height=8,wrap='word');self.log.insert('1.0',self.t('log_empty'));self.log.configure(state='disabled');self.log_placeholder=True;self.text_widgets.append(self.log);self.recolor_widgets()
        ttk.Button(outer,text=self.t('details'),command=self.toggle_log,style='Extra.TButton').pack(anchor='w',pady=7)
    def apply_theme(self,name):
        if name==self.theme_name:return
        self.theme_name=name;tktheme.apply(self,name,self.font)
        self.recolor_widgets()
    def recolor_widgets(self):
        p=theme.PALETTES[self.theme_name]
        for canvas in self.surfaces:canvas.configure(bg=p['bg'])
        for widget in self.text_widgets:
            widget.configure(bg=p['surface'],fg=p['text'],selectbackground=p['selection'],selectforeground=p['selection_fg'],relief='flat',borderwidth=0,
                highlightthickness=1,highlightbackground=p['border'],highlightcolor=p['accent'],font=(self.font,10))
            if isinstance(widget,tk.Text):widget.configure(insertbackground=p['text'],padx=8,pady=6)
            else:widget.configure(disabledforeground=p['disabled_fg'],activestyle='none')
        for combo in (getattr(self,'speech_combo',None),getattr(self,'speech_format_combo',None),getattr(self,'subtitle_mode_combo',None)):
            if combo is None:continue
            try:
                popdown=self.tk.call('ttk::combobox::PopdownWindow',combo)
                self.tk.call(popdown+'.f.l','configure','-background',p['surface'],'-foreground',p['text'],'-selectbackground',p['accent'],'-selectforeground',p['accent_fg'])
            except tk.TclError:pass
    def follow_main_theme(self):
        # The main window records its resolved theme; follow it so both windows switch together.
        self.theme_tick=(self.theme_tick+1)%12
        if self.theme_tick:return
        name=theme.load_settings().get('active_theme')
        if name in theme.PALETTES:self.apply_theme(name)
    def toggle_log(self):
        if self.log.winfo_manager():self.log.pack_forget()
        else:self.log.pack(fill='x',pady=6)
    def render_menu(self):
        ids=self.action_ids if self.info else ['trim','merge','add_audio','extract_audio','remove_range','split','mute_range','mute','frame','gif','rotate','speed','volume','fade_in','fade_out','transcribe','add_subtitle']
        signature=(tuple(ids),self.info.kind if self.info else None)
        if signature!=self.menu_signature:
            for button in self.menu_buttons.values():button.destroy()
            self.menu_buttons={};self.menu_signature=signature
            for action in ids:
                label=self.action_name(action)
                if self.lang=='tr' and action=='extract_audio':label='Sesi çıkar'
                if not self.info and self.lang=='tr':label={'trim':'Video kes','merge':'Birleştir','split':'Parçalara ayır'}.get(action,label)
                button=ttk.Button(self.menu,text=label,command=lambda a=action:self.select_operation(a),style='Operation.TButton');button.pack(fill='x',pady=3)
                self.menu_buttons[action]=button
        for action,button in self.menu_buttons.items():button.configure(style='ChosenOperation.TButton' if action==self.current_action() else 'Operation.TButton',state='disabled' if self.running or self.detecting else 'normal')
    def select_operation(self,action):
        if self.running or self.detecting:return
        if not self.info:
            self.pending_action=action
            self.choose() if action=='merge' else self.choose_single()
            return
        if action not in self.action_ids:return
        self.action.current(self.action_ids.index(action));self.show_fields(event=True)
    def build_file_card(self,row):
        card=ttk.Frame(row,style='Card.TFrame',padding=(12,10));card.pack(side='left',fill='x',expand=True)
        self.file_name=ttk.Label(card,style='CardTitle.TLabel');self.file_name.pack(anchor='w')
        self.file_folder=ttk.Label(card,style='CardMeta.TLabel');self.file_folder.pack(anchor='w',pady=(2,8))
        bar=ttk.Frame(card,style='CardInner.TFrame');bar.pack(anchor='w')
        self.audio_browse_button=ttk.Button(bar,style='Accent.TButton',text=self.t('browse_audio'),command=self.choose_audio);self.audio_browse_button.pack(side='left',padx=(0,8))
        self.last_srt_button=ttk.Button(bar,style='Extra.TButton',text=self.t('use_last_srt'),command=lambda:self.vars['audio'].set(str(self.last_srt)))
        self.clear_file_button=ttk.Button(bar,style='Extra.TButton',text=self.t('clear_file'),command=lambda:self.vars['audio'].set(''))
        self.mutable.extend([self.audio_browse_button,self.last_srt_button,self.clear_file_button])
        for widget in (card,self.file_name,self.file_folder):widget.bind('<Double-Button-1>',lambda e:self.choose_audio())
        self.vars['audio'].trace_add('write',lambda *_:self.refresh_file_card());self.refresh_file_card()
    def refresh_file_card(self):
        value=self.vars['audio'].get().strip();path=Path(value) if value else None
        if path:
            self.file_name.configure(text=path.name,style='CardTitle.TLabel')
            size=path.stat().st_size if path.is_file() else None
            size='' if size is None else f' · {size} B' if size<1024 else f' · {size/1024:.0f} KB' if size<1048576 else f' · {size/1048576:.1f} MB'
            self.file_folder.configure(text=str(path.parent)+size)
            self.clear_file_button.pack(side='left',padx=(0,8))
        else:
            self.file_name.configure(text=self.t('no_file'),style='CardEmpty.TLabel');self.file_folder.configure(text='');self.clear_file_button.pack_forget()
        offer=self.current_action()=='add_subtitle' and self.last_srt and Path(self.last_srt).is_file() and value!=str(self.last_srt)
        if offer:self.last_srt_button.pack(side='left',padx=(0,8))
        else:self.last_srt_button.pack_forget()
        has_file=bool(path)
        self.audio_browse_button.configure(style='Extra.TButton' if has_file else 'Accent.TButton')
    def ask(self,mode,title,filters=None,initial=None):
        """Native GTK chooser on Linux (sidebar, search, theme); Tk elsewhere or as fallback."""
        if sys.platform.startswith('linux') and os.environ.get('DONUSTURUCU_NATIVE_DIALOGS','1')!='0':
            args=[sys.executable,'-m','donusturucu.filepicker','--mode',mode,'--title',title,'--theme',self.theme_name or 'light',
                '--accept',self.t('choose'),'--cancel',self.t('dialog_cancel')]
            if initial:args+=['--start',str(initial)]
            for label,patterns in filters or []:args+=['--filter',label+'|'+patterns]
            try:
                self.update_idletasks()
                done=subprocess.run(args,cwd=str(Path(__file__).resolve().parents[1]),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,timeout=3600)
                if done.returncode==0:
                    import json;paths=json.loads(done.stdout.strip().splitlines()[-1] if done.stdout.strip() else '[]')
                    return paths if mode=='open-multiple' else (paths[0] if paths else '')
            except (OSError,ValueError,subprocess.TimeoutExpired,IndexError):pass
        types=[(label,patterns) for label,patterns in filters or []]
        if mode=='folder':return filedialog.askdirectory(parent=self,title=title,initialdir=str(initial) if initial else None)
        if mode=='open-multiple':return filedialog.askopenfilenames(parent=self,title=title,**({'filetypes':types} if types else {}))
        return filedialog.askopenfilename(parent=self,title=title,**({'filetypes':types} if types else {}))
    def start_folder(self):
        return self.info.path.parent if self.info else Path.home()
    def operation_filters(self):
        """Only offer files the chosen operation can use (all files remain one click away)."""
        video='*.mp4 *.mkv *.webm *.avi *.mov *.mpeg *.mpg *.ts *.m4v *.MP4 *.MKV *.MOV *.AVI *.WEBM'
        audio='*.mp3 *.wav *.flac *.ogg *.opus *.m4a *.aac *.aiff *.wma *.MP3 *.WAV *.M4A *.FLAC'
        a=self.pending_action;everything=(self.t('all_files'),'*')
        if a in {'mute','frame','gif','rotate','add_audio','replace_audio','extract_audio','add_subtitle'}:return [(self.t('video_files'),video),everything]
        if a in {'trim','remove_range','mute_range','volume','speed','fade_in','fade_out','transcribe'}:return [(self.t('media_files'),video+' '+audio),everything]
        return None
    def choose_single(self):
        if self.running or self.detecting:return
        path=self.ask('open',self.t('pick_file'),self.operation_filters(),initial=self.start_folder())
        if path:self.files=[];self.ranges=[];self.info=None;self.add_paths([path])
    def log_text(self,text):
        self.log.configure(state='normal')
        if self.log_placeholder:self.log.delete('1.0','end');self.log_placeholder=False
        self.log.insert('end',text+'\n');self.log.see('end');self.log.configure(state='disabled')
    def choose(self):
        paths=self.ask('open-multiple',self.t('add'),self.operation_filters(),initial=self.start_folder())
        if paths:self.add_paths(paths)
    def choose_folder(self):
        folder=self.ask('folder',self.t('add_folder'),initial=self.start_folder())
        if folder:self.batch_all.set(True);self.add_paths([folder])
    def add_paths(self,paths):
        if self.running or self.detecting:return
        self.detecting=True;self.status.configure(text=self.t('detected'));self.controls(False)
        requested=self.pending_action
        def work():
            infos=[];errors=[]
            for path in core.expand_paths(paths):
                try:infos.append(core.detect(path))
                except Exception as e:errors.append(Path(path).name+': '+self.error(e))
            self.events.put(('files',(infos,errors,requested)))
        threading.Thread(target=work,daemon=True).start()
    def display_files(self,index=None):
        self.listbox.delete(0,'end')
        for n,(info,pair) in enumerate(zip(self.files,self.ranges),1):
            suffix=''
            if self.current_action()=='merge':
                suffix=' — '+(self.t('whole_file') if pair==('0','') else clock(pair[0])+' – '+(clock(pair[1]) if pair[1] else self.t('end').split(' (')[0]))
            self.listbox.insert('end',f'{n}. '+info.path.name+suffix)
        if self.files:
            index=min(index if index is not None else 0,len(self.files)-1);self.listbox.selection_set(index);self.selected()
        else:self.info=None;self.source_label.configure(text=self.t('no_file'));self.source_meta.configure(text='');self.action.configure(values=[]);self.action.set('');self.show_fields()
    def selected(self,event=None):
        selection=self.listbox.curselection()
        if not selection:return
        n=selection[0];self.last_selected=n;self.info=self.files[n];self.seg_start.set(self.ranges[n][0]);self.seg_end.set(self.ranges[n][1])
        old=getattr(self,'pending_action',None) or self.current_action();self.pending_action=None;self.action_ids=actions(self.info)
        self.action.configure(values=[self.action_name(a) for a in self.action_ids]);self.action.current(self.action_ids.index(old) if old in self.action_ids else 0)
        self.source_label.configure(text=self.info.path.name)
        meta=[self.t('duration')+': '+clock(str(self.info.duration))] if self.info.kind in {'audio','video'} else []
        if len(self.files)>1:meta.append(f'{n+1} / {len(self.files)}')
        self.source_meta.configure(text=' · '.join(meta+[str(self.info.path.parent)]))
        self.show_fields()
    def current_action(self):
        n=self.action.current();return self.action_ids[n] if 0<=n<len(self.action_ids) else ''
    def action_name(self,a):
        if a=='remove_range' and self.info and self.lang=='tr':return 'Videodan bölüm sil' if self.info.kind=='video' else 'Sesten bölüm sil'
        if a in {'trim','split','merge'} and self.info:
            kind=self.info.kind
            if self.lang=='tr':
                noun='Video' if kind=='video' else 'Ses' if kind=='audio' else 'Belge'
                return {'trim':noun+' kes','split':noun+' parçala','merge':('Videoları' if kind=='video' else 'Sesleri' if kind=='audio' else 'Belgeleri')+' birleştir'}[a]
        return self.t(a)
    def show_fields(self,event=None):
        for row in self.fields.values():row.pack_forget()
        self.segment.pack_forget();self.range_toggle.pack_forget();self.audio_toggle.pack_forget()
        a=self.current_action();merging=a=='merge'
        self.merge_panel.pack_forget();self.pick_button.pack_forget();self.render_menu()
        self.pick_button.configure(text=self.t('pick_file'))
        if not self.info:
            self.pick_button.pack(side='left',padx=(0,8),before=self.add_folder_button)
            self.hint.configure(text=self.t('pick_operation_help'));return
        for key,button in self.list_controls.items():
            button.configure(text=self.t(key if merging else 'add' if key=='pick_more' else 'remove_batch' if key=='remove_join' else key))
            button.grid() if merging or key not in {'up','down'} else button.grid_remove()
        self.merge_panel.configure(text=self.t('join_order') if merging else self.t('batch_list'))
        self.batch_toggle.pack_forget()
        if len(self.files)>1 and not merging:self.batch_toggle.pack(before=self.form,anchor='w',pady=5)
        if merging or (self.batch_all.get() and len(self.files)>1):self.merge_panel.pack(before=self.form,fill='x',pady=8)
        else:self.pick_button.pack(side='left',padx=(0,8),before=self.add_folder_button)
        self.operation_title.configure(text=self.action_name(a))
        self.pick_button.configure(text=self.t('change_video' if self.info.kind=='video' else 'change_audio' if self.info.kind=='audio' else 'change_document'))
        media=self.info.kind in {'audio','video'};keys=[]
        for key,label in self.field_labels.items():label.configure(text=self.t(key))
        if media:
            self.range_toggle.configure(text=self.t('custom_range'))
            mandatory={'trim','remove_range','mute_range','fade_in','fade_out','gif'}
            optional={'split','extract_audio','rotate','speed','volume','transcribe'}
            if a in optional:
                self.range_toggle.pack(before=self.form,anchor='w',pady=(7,0))
            if a in mandatory or (a in optional and self.use_range.get()):keys+=['start','end']
            if a=='transcribe':keys+=['speech_language','speech_format']
            if a=='add_subtitle':
                keys+=['audio','subtitle_mode'];self.field_labels['audio'].configure(text=self.t('subtitle_file'))
                current=self.vars['audio'].get()
                if self.last_srt and (not current or Path(current).suffix.lower() not in {'.srt','.ass','.ssa','.vtt'}):self.vars['audio'].set(str(self.last_srt))
            if a=='frame':
                keys+=['start'];self.field_labels['start'].configure(text=self.t('frame_time'))
            if a=='split':keys+=['part']
            if a in {'volume','speed','rotate'}:keys+=['factor']
            if a in {'add_audio','replace_audio'}:
                keys+=['audio','start','end']
                self.field_labels['start'].configure(text=self.t('insert_start'))
                self.field_labels['end'].configure(text=self.t('insert_end'))
                self.audio_toggle.pack(before=self.form,anchor='w',pady=(7,0))
                if self.use_audio_range.get():keys+=['audio_start','audio_end']
            if merging:self.segment.pack(before=self.form,fill='x',pady=5)
            hint=self.t('merge_help') if merging else HELP[self.lang].get(a,'')
            if merging and self.info.kind=='audio':hint+='\n'+self.t('merge_audio_help')
            if keys and any(k in keys for k in ['start','end','part']):hint+='\n'+self.t('time_help')
        else:
            if a=='split':
                self.range_toggle.configure(text=self.t('custom_pages'));self.range_toggle.pack(before=self.form,anchor='w',pady=(7,0))
                keys=['pages'] if self.use_range.get() else ['page_count']
            hint=self.t('pdf_merge_help' if merging else 'page_help')
        self.audio_browse_button.configure(text=self.t('choose' if a=='subtitle_restore' else 'browse_subtitle' if a=='add_subtitle' else 'browse_audio'))
        if a=='add_subtitle' and self.last_srt and self.vars['audio'].get()==str(self.last_srt):hint+='\n'+self.t('subtitle_ready').format(name=Path(self.last_srt).name)
        if a=='subtitle_restore':
            keys=['audio'];self.field_labels['audio'].configure(text=self.t('subtitle_original'))
        if a in {'subtitle_text','subtitle_restore'}:hint=self.t(a+'_help')
        self.factor_label.configure(text=self.t('rotate_factor' if a=='rotate' else 'speed_factor' if a=='speed' else 'volume_factor'))
        if event is not None and a=='rotate':self.vars['factor'].set('90')
        elif event is not None and a in {'volume','speed'}:self.vars['factor'].set('1')
        for key in keys:self.fields[key].pack(fill='x',pady=3)
        self.refresh_file_card()
        self.hint.configure(text=hint);self.run_button.configure(text=self.action_name(a))
        # Refresh list labels without changing selection or triggering another action.
        selection=self.listbox.curselection()
        self.listbox.delete(0,'end')
        for n,(info,pair) in enumerate(zip(self.files,self.ranges),1):
            suffix=(' — '+(self.t('whole_file') if pair==('0','') else clock(pair[0])+' – '+(clock(pair[1]) if pair[1] else self.t('whole_file')))) if merging else ''
            self.listbox.insert('end',f'{n}. '+info.path.name+suffix)
        if selection:self.listbox.selection_set(selection[0])
    def save_range(self):
        if self.last_selected is None:return
        try:
            from .operations import seconds
            a=self.seg_start.get();b=self.seg_end.get();seconds(a)
            if b and seconds(b)<=seconds(a):raise OperationError('invalid_range')
            self.ranges[self.last_selected]=(a,b);self.display_files(self.last_selected);return True
        except Exception as e:messagebox.showerror(self.t('error'),self.error(e),parent=self);return False
    def remove(self):
        if self.running or self.detecting:return
        s=self.listbox.curselection()
        if s:n=s[0];self.files.pop(n);self.ranges.pop(n);self.display_files(n)
    def move(self,direction):
        s=self.listbox.curselection()
        if not s or self.running or self.detecting:return
        n=s[0];other=n+direction
        if 0<=other<len(self.files):
            self.files[n],self.files[other]=self.files[other],self.files[n];self.ranges[n],self.ranges[other]=self.ranges[other],self.ranges[n];self.display_files(other)
    def choose_audio(self):
        a=self.current_action()
        current=self.vars['audio'].get().strip();start=Path(current).parent if current else self.start_folder()
        if a in {'subtitle_restore','add_subtitle'}:
            types=[(self.t('subtitle_file'),'*.srt *.SRT' if a=='subtitle_restore' else '*.srt *.ass *.ssa *.vtt *.SRT *.ASS *.SSA *.VTT'),(self.t('all_files'),'*')]
            p=self.ask('open',self.t('subtitle_original' if a=='subtitle_restore' else 'subtitle_file'),types,start)
        else:p=self.ask('open',self.t('audio'),[(self.t('audio'),'*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.wma *.MP3 *.WAV *.M4A'),(self.t('all_files'),'*')],start)
        if p:self.vars['audio'].set(p)
    def choose_output(self):
        p=self.ask('folder',self.t('change_output'),initial=self.output if self.output.exists() else Path.home())
        if p:self.output=Path(p);self.folder_label.configure(text=p)
    def open_output(self):
        self.output.mkdir(parents=True,exist_ok=True)
        if sys.platform=='win32':os.startfile(self.output)
        else:subprocess.Popen(['open' if sys.platform=='darwin' else 'xdg-open',str(self.output)])
    def controls(self,enabled):
        for widget in self.mutable:widget.configure(state='normal' if enabled else 'disabled')
        self.listbox.configure(state='normal' if enabled else 'disabled');self.action.configure(state='readonly' if enabled else 'disabled')
        self.speech_combo.configure(state='readonly' if enabled else 'disabled')
        self.speech_format_combo.configure(state='readonly' if enabled else 'disabled')
        self.subtitle_mode_combo.configure(state='readonly' if enabled else 'disabled')
        self.run_button.configure(state='normal' if enabled else 'disabled')
        for button in self.menu_buttons.values():button.configure(state='normal' if enabled else 'disabled')
    def run(self):
        if self.running or self.detecting:return
        if not self.info:messagebox.showwarning(self.t('title'),self.t('choose_file'),parent=self);return
        a=self.current_action()
        if a=='merge' and not self.save_range():return
        selected=self.last_selected if self.last_selected is not None else 0
        files=[i.path for i in self.files] if a=='merge' or self.batch_all.get() else [self.files[selected].path]
        values={k:v.get() for k,v in self.vars.items()}
        values['speech_format']=values['speech_format'].lower()
        values['speech_language']={'Türkçe':'tr','English':'en'}.get(values['speech_language'],'')
        values['subtitle_mode']='soft' if values['subtitle_mode']==self.t('subtitle_soft') else 'burn'
        if self.info.kind not in {'video','audio'} and a=='split':
            if not self.use_range.get():values['pages']=''
            elif not values['pages'].strip():messagebox.showwarning(self.t('title'),self.t('invalid_pages'),parent=self);return
        if a in {'split','extract_audio','rotate','speed','volume','transcribe'} and not self.use_range.get():values.update(start='0',end='')
        if a in {'add_audio','replace_audio'} and not self.use_audio_range.get():values.update(audio_start='0',audio_end='')
        r=Request(a,files,self.output,**values,segments=list(self.ranges),language=self.lang)
        batch_mode=self.batch_all.get();reference=self.info.path
        self.running=True;self.runner=core.Runner(progress=lambda value:self.events.put(('progress',value)));self.controls(False);self.stop_button.configure(state='normal')
        # Single-pass jobs report trustworthy progress; multi-step ones would jump backwards.
        self.percent_progress=a in PERCENT_ACTIONS and not batch_mode
        if self.percent_progress:self.progress.configure(mode='determinate',maximum=1,value=0)
        else:self.progress.configure(mode='indeterminate');self.progress.start(10)
        self.status.configure(text=self.t('busy'))
        import time;self.started_at=time.monotonic()
        self.log_text(self.t('log_start').format(time=time.strftime('%H:%M:%S'),action=self.action_name(a)))
        self.log_text(self.t('log_files').format(files=', '.join(Path(f).name for f in files)))
        self.log_text(self.t('log_output').format(folder=self.output))
        def work():
            try:
                if batch_mode:self.events.put(('batch_done',Editor(self.runner).execute_many(r,reference=reference)))
                else:self.events.put(('done',Editor(self.runner).execute(r)))
            except Exception as e:self.events.put(('error',e))
        threading.Thread(target=work,daemon=True).start()
    def show_percent(self,fraction):
        import time
        fraction=max(0.0,min(1.0,float(fraction)));self.progress.configure(value=fraction)
        text=self.t('busy_percent').format(percent=int(fraction*100))
        elapsed=time.monotonic()-self.started_at
        if fraction>=0.03 and elapsed>=3:
            left=int(elapsed*(1-fraction)/fraction);m,sec=divmod(left,60)
            text+=self.t('busy_eta').format(eta=self.t('minutes').format(m=m,s=sec) if m else self.t('seconds_only').format(s=sec))
        self.status.configure(text=text)
    def cancel(self):
        if self.runner:self.runner.cancel()
        self.stop_button.configure(state='disabled')
    def error(self,e):
        key=str(e) if isinstance(e,OperationError) else getattr(e,'code',None)
        if key in TEXT[self.lang]:return self.t(key)
        if key and key in STRINGS.get(self.lang,{}):return STRINGS[self.lang][key]
        return str(e)
    def poll(self):
        self.follow_main_theme()
        while True:
            try:kind,data=self.events.get_nowait()
            except queue.Empty:break
            if kind=='progress':
                if self.running and self.percent_progress:self.show_percent(data)
                continue
            if kind=='files':
                infos,errors,requested=data;self.files.extend(infos);self.ranges.extend([('0','') for _ in infos]);self.detecting=False;self.controls(True);self.display_files();self.status.configure(text=self.t('status_ready'))
                if requested and self.info and requested not in self.action_ids:
                    kind=STRINGS.get(self.lang,STRINGS['tr']).get(self.info.kind,self.info.kind)
                    note=self.t('action_not_for_file').format(action=self.t(requested),kind=kind)
                    self.status.configure(text=note);self.hint.configure(text=note+'\n\n'+self.hint.cget('text'))
                for e in errors:self.log_text(e)
                if errors:
                    self.log.pack(fill='x',pady=6);self.status.configure(text=self.t('error'))
            else:
                self.running=False;self.runner=None;self.progress.stop();self.progress.configure(mode='determinate',maximum=1,value=1 if kind in {'done','batch_done'} else 0);self.controls(True);self.stop_button.configure(state='disabled')
                if kind=='batch_done':
                    outputs,issues=data
                    for path,error in issues:self.log_text(str(path)+' — '+self.error(error))
                    self.log_text(self.t('done')+' '+str(len(outputs))+'; '+self.t('batch_issues')+': '+str(len(issues))+'\n'+'\n'.join(map(str,outputs)));self.status.configure(text=self.t('done') if outputs else self.t('error'));self.log.pack(fill='x',pady=6)
                elif kind=='done':
                    if self.percent_progress:self.progress.configure(value=1)
                    self.status.configure(text=self.t('done'));self.log_text('✓ '+self.t('done')+'\n'+'\n'.join('  → '+str(p) for p in data))
                    srt=[Path(p) for p in data if Path(p).suffix.lower()=='.srt']
                    if srt:self.last_srt=srt[-1]
                elif isinstance(data,core.Cancelled):self.status.configure(text=self.t('cancelled'));self.log_text(self.t('log_cancelled'))
                else:self.status.configure(text=self.t('error'));self.log_text(self.t('log_failed').format(error=self.error(data)));messagebox.showerror(self.t('error'),self.error(data),parent=self)
                import time;self.log_text(self.t('log_elapsed').format(seconds=round(time.monotonic()-self.started_at,1))+'\n')
                if not self.log.winfo_manager():self.log.pack(fill='x',pady=6)
                if self.closing:self.destroy();return
        self.after(80,self.poll)
    def close(self):
        if self.detecting:return
        if self.running:
            if messagebox.askyesno(self.t('title'),self.t('close_busy'),parent=self):self.closing=True;self.cancel()
        else:self.destroy()

def main():
    p=argparse.ArgumentParser();p.add_argument('--lang',default='tr');p.add_argument('--source');p.add_argument('--output');p.add_argument('--theme',choices=['light','dark']);args=p.parse_args()
    root=tk.Tk(className='Donusturucu');root.withdraw();ttk.Style(root).theme_use('clam')
    w=ExtraWindow(root,args.lang,args.source,args.output,args.theme)
    w.bind('<Destroy>',lambda event:root.destroy() if event.widget is w else None)
    root.mainloop()
if __name__=='__main__':main()
