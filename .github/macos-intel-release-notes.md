**Dönüştürücü — Intel işlemcili Mac'ler için** (masaüstü 1.9.2 ile aynı uygulama)

| Cihaz | Dosya |
| --- | --- |
| Mac, Intel işlemci (macOS 13 Ventura ve sonrası) | `Donusturucu-macOS-Intel-Kurulum.pkg` |

M1–M4 Mac'ler, Windows, Linux ve Android için: [v1.9.2](../v1.9.2)

Mac'inizin Intel mi Apple Silicon mı olduğunu  → **Bu Mac Hakkında** gösterir: "İşlemci: Intel" yazıyorsa bu paket sizin içindir.

## Kurulum

1. `Donusturucu-macOS-Intel-Kurulum.pkg` dosyasını indirin.
2. Paket imzasız olduğu için çift tıklayınca macOS açmayabilir. Dosyaya **sağ tıklayın → Aç**, çıkan pencerede yine **Aç**'a basın. (Ya da **Sistem Ayarları → Gizlilik ve Güvenlik → Yine de Aç**.)
3. Kurulum birkaç dakika sürer: yerel motor hazırlanır ve tüm işlevler denenir (en az 6 GB boş alan gerekir).
4. Uygulama açılmazsa Terminal'de şunu çalıştırıp yeniden deneyin:

```
xattr -dr com.apple.quarantine /Applications/Donusturucu.app
```

Kurulum kaydı: `/Applications/Donusturucu.app/Contents/Resources/app/installation.log`

Dönüştürme işlemleri internet gerektirmez; dosyalar cihazdan çıkmaz.
