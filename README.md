## OTOMATİK PO ÇEVİRİCİ – GPT DESTEKLİ - Güncel Sürüm: v3.0.3 - 02 Ocak 2026 / 12:18:00

Bu uygulama, .po uzantılı dil dosyalarını GPT destekli gelişmiş bir çeviri motoru kullanarak Türkçe ↔ İngilizce başta olmak üzere farklı diller arasında otomatik olarak çevirmenizi sağlar.
Çeviri sürecinde mevcut çevirileri korur, yalnızca boş veya eksik msgstr alanlarını hedef alır ve dil dosyasının yapısını bozmadan güvenli bir şekilde güncelleme yapar.
Kullanıcı dostu arayüzü sayesinde teknik bilgi gerektirmeden hızlı ve tutarlı çeviriler üretmenize olanak tanırken, tekrar eden ifadelerde zaman ve maliyet tasarrufu sağlamayı hedefler

<br>
<p align="center">
  <img
    src="https://github.com/user-attachments/assets/512fded2-349d-4dbf-b348-2d9e43f5b075"
    alt="image"
    width="auto"
    height="auto"
  />
</p>

<p align="center">
<a href="https://www.buymeacoffee.com/mdanisman3f" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>
</p>
<br>

## Uygulama özellikleri:

- WordPress tema / eklenti çevirileri

- SEO, WooCommerce ve admin panel metinleri

- Teknik UI açıklamaları için üretim ortamına uygun, güvenli ve kontrollü bir çeviri sunar.

## TEMEL ÖZELLİKLER

- Tek .po dosyası veya klasör (batch) çeviri

- Akıllı sabit metin algılama

- URL, marka, ID, kod, shortcode çevrilmez

- Placeholder ve HTML etiketleri korunur

- Translation Memory (tercihler.json)

- Aynı metin tekrar çevrilmez

- İşlem durdurma (iptal)

- Batch raporu (reports/ klasörü)

- Detaylı loglama (logs/ klasörü)

- Uzun batch işlemleri için stabil mimari

## YENİ ÖZELLİKLER (v3.0.3)

### Kritik Düzeltmeler
- **Hata takibi**: stats["hata"] sayacı artık doğru çalışıyor
- **OpenAI timeout**: 30 saniye timeout ile sonsuz askıda kalma önlendi
- **Atomik dosya yazma**: Ayar kayıtları daha güvenli

### Kod Kalitesi İyileştirmeleri
- **UI Message Type sabitleri**: Daha temiz ve güvenli kod
- **Dil seçici**: 🇹🇷 Türkçe / 🇬🇧 English gösterimi
- **Menü sistemi**: Daha sağlam hata yönetimi

## ÖNCEKİ ÖZELLİKLER (v3.0.2)

### Önizleme Modu
- Tam çeviri öncesi ilk 10 entry'yi test edin
- API maliyetini kontrol altında tutun
- Çeviri kalitesini önizleyin

### Özel Sözlük
- Marka isimleri ve özel terimlerinizi tanımlayın
- Model yerine direkt çevirileriniz kullanılır
- `Araçlar → Özel Sözlük Düzenle` menüsünden yönetin

### Toplu Geri Al
- Son batch işlemini tek tıkla geri alın
- Hatalı çevirileri kolayca temizleyin
- `Araçlar → Son Batch'i Geri Al`

### Çok Dilli Destek
- Türkçe ↔ İngilizce
- Türkçe ↔ Fransızca, Almanca, İspanyolca, İtalyanca, Portekizce
- Daha fazla dil yakında...

### Çok Dilli Arayüz
- Uygulama arayüzü 2 dilde desteklenir:
  - 🇹🇷 **Türkçe** (varsayılan)
  - 🇬🇧 **İngilizce**
- Sağ üst köşedeki **"Dil:"** menüsünden dil değiştirebilirsiniz
- Dil değişikliği **anında** uygulanır, uygulama yeniden başlatılmasına gerek yoktur
- Dil tercihiniz otomatik olarak kaydedilir

### Gelişmiş Ayarlar
- Model temperature kontrolü
- Retry sayısı ayarı
- Tercihler kayıt aralığı
- Log saklama süresi
- `Araçlar → Gelişmiş Ayarlar`

## DESTEKLENEN SENARYOLAR

- WordPress tema / eklenti .po dosyaları

- SEO ayar ekranları

- WooCommerce bileşenleri

- Yönetim paneli açıklamaları

- Teknik kullanıcı arayüzleri

## GEREKSİNİMLER

- Python 3.9 veya üzeri
- https://www.python.org/downloads/

## OpenAI API Anahtarı
- https://platform.openai.com/account/api-keys

## KURULUM

- ZIP dosyasını bilgisayarınıza çıkartın

- Klasörün içinde bulunan Kur-Calistir.bat dosyasına tıklayın.

- Bu bat dosyası gerekli kütüphaneleri yükleyecek ve programı çalıştıracaktır.


## API KEY KULLANIMI

Uygulama API anahtarını şu öncelik sırasına göre alır:

1. **GUI'deki API Key alanı** (doldurulursa)
2. **`.env` dosyası** (OPENAI_API_KEY değişkeni)

### .env Dosyası Kurulumu

1. Proje kök dizininde `.env` dosyası oluşturun
2. Aşağıdaki formatı kullanın:
   ```
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
   ```
3. API anahtarınızı https://platform.openai.com/account/api-keys adresinden alın

⚠️ **GÜVENLİK UYARISI:** `.env` dosyası `.gitignore`'da olduğundan Git'e yüklenmeyecektir.
API anahtarınızı asla paylaşmayın!

## HATA GİDERME

### ❌ API anahtarı bulunamadı hatası
- `.env` dosyasının proje kök dizininde olduğundan emin olun
- `.env` dosyasında `OPENAI_API_KEY=` satırının doğru olduğunu kontrol edin
- Veya GUI'deki API Key alanını doldurun

## KULLANIM ADIMLARI

- .env dosyanız hazır olsun

- .po dosyası veya klasör seçin

- Çeviri yönünü seçin (EN → TR / TR → EN / FR → TR vb.)

- Modeli seçin (gpt-4o / gpt-4o-mini)

- İsteğe bağlı: Önizleme için "Önizleme (10 Entry)" butonuna basın

- Çeviriyi Başlat butonuna basın

- Logları ve ilerlemeyi anlık izleyin

- Gerekirse Durdur ile işlemi iptal edin


### Önizleme Modu
1. .po dosyası seçin
2. "Önizleme (10 Entry)" butonuna tıklayın
3. Sonuçları kontrol edin
4. Devam etmek için "Çeviriyi Başlat"

### Özel Sözlük
1. `Araçlar → Özel Sözlük Düzenle`
2. "Yeni Ekle" ile terim ekleyin
3. Kaynak ve hedef metni girin
4. "Kaydet" ile uygulayın

### Çok Dilli Çeviri
1. "Yön" dropdown'ından dil çiftini seçin
2. Örnek: FR-TR (Fransızca → Türkçe)
3. Normal şekilde çeviriyi başlatın

### Arayüz Dili Değiştirme
1. Sağ üst köşedeki **"Dil:"** açılır menüsünü kullanın
2. İstediğiniz dili seçin (Türkçe veya English)
3. Tüm arayüz metinleri **anında** değişir
4. Ayarlarınız (API key, model seçimi vb.) korunur
5. Bir sonraki açılışta son seçtiğiniz dil kullanılır

### Gelişmiş Ayarlar
1. `Araçlar → Gelişmiş Ayarlar`
2. Temperature, retry sayısı vb. ayarları yapın
3. "Kaydet" ile uygulayın

## ÇIKTI DOSYALARI
## Tek Dosya Çevirisi:
- example.po → example_EN-TR_CEVRILDI.po

## Batch (Klasör) Çevirisi:

- Her .po dosyası ayrı ayrı çevrilir

- Otomatik batch raporu oluşturulur:

- reports/batch_YYYY-MM-DD_HH-MM-SS.json

## AKILLI DAVRANIŞLAR

Aşağıdaki içerikler bilerek çevrilmez:

- URL’ler

- Marka / ürün adları (Google Ads, WooCommerce, Jegtheme vb.)

- ID / kod / sürüm bilgileri

- Shortcode ve teknik UI seçenekleri

- Log çıktısı örneği: ↩ Çevrilmedi (sabit): Google Ads

## SORUN GİDERME

❌ ModuleNotFoundError
- pip install <modül_adı>

❌ Pencere açılıp kapanıyor

- CMD üzerinden çalıştırın: python ceviri_gui.py

❌ API hatası

- OpenAI hesabınızı kontrol edin

- API limitinizi doğrulayın

- .env dosyasının doğru dizinde olduğundan emin olun

## GELİŞTİRİCİLER İÇİN

### Yeni Arayüz Dili Ekleme
1. `diller/LANG_CODE/LC_MESSAGES/` klasörünü oluşturun
   - Örnek: `diller/de_DE/LC_MESSAGES/` (Almanca için)
2. `app.po` dosyasını oluşturun ve çevirileri ekleyin
3. `python derle_diller.py` ile MO dosyasını derleyin
4. `ceviri_gui.py` içinde dil listesine ekleyin:
   ```python
   dil_combo = ttk.Combobox(..., values=["tr_TR", "en_US", "de_DE"], ...)
   ```
5. Uygulamayı yeniden başlatın

## NOTLAR

- Uygulama teknik çeviri için tasarlanmıştır

- Pazarlama dili eklemez, anlam genişletmez

- Aynı metin bir kez çevrildikten sonra bellekten kullanılır

- Uzun batch işlemleri için RAM koruması aktiftir

## LİSANS

Geliştirici:
Muharrem DANIŞMAN - mdanisman3@gmail.com

Lisans: MIT
Kullanım: Ücretsiz – ticari kullanım serbesttir
