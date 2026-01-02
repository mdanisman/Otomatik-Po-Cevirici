import polib
import os
import json
import re
import time
import glob
import logging
from logging.handlers import RotatingFileHandler
import threading
from datetime import datetime
from collections import defaultdict
from openai import OpenAI
from dotenv import load_dotenv
from helpers import temizle_metin

load_dotenv()
_durdur_olayi = threading.Event()

TERCIHLER_DOSYASI = "tercihler.json"
SOZLUK_DOSYASI = "sozluk.json"
GELISMIS_AYARLAR_DOSYASI = "gelismis_ayarlar.json"
LOG_DIR = "günlükler"
REPORT_DIR = "raporlar"

gelismis_ayarlar = {
    "temperature": 0.05,
    "maks_deneme_sayisi": 3,
    "tercihler_kayit_araligi": 50,
    "log_saklama_gun": 30,
    "onizleme_entry_sayisi": 10,
    "max_tokens":  500,
    "top_p":  0.9
}

_tercihler_dirty = False
_tercihler_counter = 0

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

DIL_KODLARI = {
    "EN": "English",
    "TR": "Turkish",
    "FR": "French",
    "DE": "German",
    "ES": "Spanish",
    "IT": "Italian",
    "PT": "Portuguese"
}

if os.path.exists(GELISMIS_AYARLAR_DOSYASI):
    try:
        with open(GELISMIS_AYARLAR_DOSYASI, "r", encoding="utf-8") as f:
            yuklenen = json.load(f)
            gelismis_ayarlar.update(yuklenen)

    except Exception as e: 

        pass

TERCIHLER_SAVE_INTERVAL = gelismis_ayarlar["tercihler_kayit_araligi"]
LOG_RETENTION_DAYS = gelismis_ayarlar["log_saklama_gun"]

log_dosyasi = os.path.join(LOG_DIR, f"ceviri_{datetime.now().strftime('%Y-%m-%d')}.log")

dosya_handler = RotatingFileHandler(
    log_dosyasi,
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8"
)

logging.basicConfig(
    level=logging. INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        dosya_handler,
        logging. StreamHandler()
    ]
)

logger = logging.getLogger("ceviri")

def _temizle_eski_loglar():

    try:
        simdi = time.time()
        saklama_saniye = LOG_RETENTION_DAYS * 24 * 60 * 60
        
        for dosya in os.listdir(LOG_DIR):
            if dosya.startswith("ceviri_") and dosya.endswith(".log"):
                dosya_yolu = os.path.join(LOG_DIR, dosya)
                dosya_zamani = os.path.getmtime(dosya_yolu)
                
                if simdi - dosya_zamani > saklama_saniye: 
                    os.remove(dosya_yolu)
                    logger.info(f"Eski log silindi: {dosya}")
    except Exception as e:
        logger. warning(f"Eski log temizleme hatası: {e}")

_temizle_eski_loglar()

tercihler = {}
if os.path.exists(TERCIHLER_DOSYASI):
    try:
        with open(TERCIHLER_DOSYASI, "r", encoding="utf-8") as f:
            tercihler = json.load(f)
        logger.info(f"Tercihler yüklendi: {len(tercihler)} kayıt")
    except Exception as e:
        logger.warning(f"tercihler. json okunamadı veya bozuk, sıfırdan başlatılıyor: {e}")

        try:
            yedek_adi = f"{TERCIHLER_DOSYASI}.bak. {datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(TERCIHLER_DOSYASI, yedek_adi)
            logger. info(f"Bozuk dosya yedeklendi: {yedek_adi}")
        except Exception: 
            pass
        tercihler = {}

ozel_sozluk = {}
if os. path.exists(SOZLUK_DOSYASI):
    try:
        with open(SOZLUK_DOSYASI, "r", encoding="utf-8") as f:
            yuklenen = json.load(f)

            ozel_sozluk = {k: v for k, v in yuklenen.items() if not k.startswith("_")}
        logger.info(f"Özel sözlük yüklendi: {len(ozel_sozluk)} terim")
    except Exception as e: 
        logger.warning(f"sozluk.json okunamadı:  {e}")
        ozel_sozluk = {}

def _kaydet_tercihler():

    try:
        gecici_dosya = TERCIHLER_DOSYASI + ".tmp"
        with open(gecici_dosya, "w", encoding="utf-8") as f:
            json.dump(tercihler, f, ensure_ascii=False, indent=4)
        os.replace(gecici_dosya, TERCIHLER_DOSYASI)
        logger.info(f"Tercihler kaydedildi: {len(tercihler)} kayıt")
    except Exception as e: 
        logger.error(f"Tercihler kaydedilemedi: {e}")
        raise

_YER_TUTUCU_DESENI = re.compile(
    r"%(?:\d+\$)?[sdufxobci]|"  # C-style:  %s, %d, %f, %u, %x, %o, %b, %c, %i, %1$s
    r"{\w+}|{{\w+}}|"            # Python/JavaScript: {name}, {{count}}
    r"\[[^\]]+\]|"               # WordPress: [tag]
    r"<[a-zA-Z][^>]*>|"          # HTML tags: <b>, <a href="#">
    r"</[a-zA-Z]+>"              # HTML closing tags:  </b>
)

_KOTU_DESENLER = re.compile(
    r"(here is|translated text|translation:|çeviri:|açıklama:|not: )",
    re.IGNORECASE
)

def _yer_tutucular_cikar(metin:  str) -> set:

    return set(_YER_TUTUCU_DESENI.findall(metin or ""))

def _yer_tutucular_uyumlu(kaynak: str, hedef: str) -> bool:

    return _yer_tutucular_cikar(kaynak) == _yer_tutucular_cikar(hedef)

def _cevirilmez_mi(kaynak: str) -> bool: 

    kaynak = kaynak.strip()

    if not kaynak:
        return True

    if re.match(r"https?://", kaynak):
        return True

    if _YER_TUTUCU_DESENI.fullmatch(kaynak):
        return True

    if re.match(r"^[^@]+@[^@]+\.[^@]+$", kaynak):
        return True

    if re.match(r"^#[0-9a-fA-F]{3,6}$", kaynak):
        return True

    if re.match(r"^v?\d+\.\d+\.\d+", kaynak):
        return True

    if re.match(r"^[/\\]|^[a-zA-Z]:[/\\]", kaynak):
        return True

    if " " not in kaynak and len(kaynak) >= 4:

        if re.fullmatch(r"[A-Z_]{4,}", kaynak):
            return True

        if ("_" in kaynak or "-" in kaynak) and not kaynak[0].isupper():
            return True

        if re.fullmatch(r"[a-z]+\.[a-z]{2,4}", kaynak):
            return True

    return False

def _ceviri_gecerli(kaynak: str, hedef: str) -> bool:

    if not hedef or not hedef.strip():
        return False

    if hedef. strip() == kaynak.strip():

        if " " not in kaynak. strip() and kaynak.strip()[0].isupper():
            return True
        return False

    if len(hedef) > len(kaynak) * 5:
        return False

    if _KOTU_DESENLER.search(hedef):
        return False
    
    return True

def _context_al(entry) -> str: 

    if entry. msgctxt:
        return entry. msgctxt. strip()
    if entry.comment:
        return entry.comment. strip()
    return "__NO_CONTEXT__"

def _bellek_anahtari(kaynak: str, context: str) -> str: 

    return f"{context}|||{kaynak}"

def ayarlari_guncelle(yeni_ayarlar: dict):

    global TERCIHLER_SAVE_INTERVAL, LOG_RETENTION_DAYS
    gelismis_ayarlar. update(yeni_ayarlar)
    TERCIHLER_SAVE_INTERVAL = gelismis_ayarlar["tercihler_kayit_araligi"]
    LOG_RETENTION_DAYS = gelismis_ayarlar["log_saklama_gun"]

def sozluk_guncelle(yeni_sozluk: dict):

    global ozel_sozluk
    ozel_sozluk = {k: v for k, v in yeni_sozluk.items() if not k.startswith("_")}

def _api_anahtari_al(gui_anahtar=None):

    if gui_anahtar and gui_anahtar.strip():
        logger.info("API key GUI'den alındı")
        return gui_anahtar.strip()
    
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key and env_key.strip():
        logger.info("API key . env dosyasından alındı")
        return env_key.strip()
    
    raise ValueError(
        "API anahtarı bulunamadı!\n"
        "Lütfen . env dosyasına ekleyin veya GUI'de girin."
    )

def durdur_islem():
    _durdur_olayi. set()

def cevir(
    api_anahtar,
    dosya_yolu,
    model,
    tercihe_kaydet,
    yon,
    progress_cb,
    log_cb,
    done_cb
):

    global _tercihler_dirty, _tercihler_counter
    _durdur_olayi.clear()

    try:
        kaynak_kod, hedef_kod = yon.split("-")
        kaynak_dil = DIL_KODLARI. get(kaynak_kod, "English")
        hedef_dil = DIL_KODLARI.get(hedef_kod, "Turkish")
    except (ValueError, AttributeError):

        kaynak_dil = "English"
        hedef_dil = "Turkish"
    
    logger.info(f"Çeviri:  {kaynak_dil} → {hedef_dil}")

    hata_sayaci = defaultdict(int)

    try:
        gercek_api_anahtar = _api_anahtari_al(api_anahtar)
        istemci = OpenAI(api_key=gercek_api_anahtar, timeout=30.0)
    except ValueError as e:
        log_cb(f"❌ HATA: {e}")
        done_cb(0, 0, {"CONFIG_ERROR": 1})
        return
    
    try:
        po = polib.pofile(dosya_yolu)

        entries = [e for e in po if not e.translated() and (e.msgid or "").strip()]
        toplam = len(entries)

        cevrilen = 0
        atlanan = 0
        progress_cb(0, toplam)

        for i, entry in enumerate(entries):
            if _durdur_olayi. is_set():
                log_cb("⛔ İşlem kullanıcı tarafından durduruldu.")
                hata_sayaci["USER_CANCELLED"] += 1
                break

            progress_cb(i + 1, toplam)
            kaynak_metin = entry.msgid. strip()
            context = _context_al(entry)
            bellek_anahtar = _bellek_anahtari(kaynak_metin, context)

            if _cevirilmez_mi(kaynak_metin):
                entry.msgstr = kaynak_metin
                cevrilen += 1
                log_cb(f"↩ Çevrilmedi (sabit): {kaynak_metin}")
                continue

            if kaynak_metin in ozel_sozluk: 
                hedef_metin = ozel_sozluk[kaynak_metin]
                entry.msgstr = hedef_metin
                cevrilen += 1
                log_cb(f"📖 {kaynak_metin} → {hedef_metin} (Özel Sözlük)")
                continue

            if bellek_anahtar in tercihler: 
                bellek_ceviri = tercihler[bellek_anahtar]
                if _yer_tutucular_uyumlu(kaynak_metin, bellek_ceviri) and _ceviri_gecerli(kaynak_metin, bellek_ceviri):
                    entry.msgstr = bellek_ceviri
                    cevrilen += 1
                    log_cb(f"✓ {kaynak_metin} → {bellek_ceviri} (Bellek)")
                    continue

            hedef_metin = None
            deneme = 1
            maks_deneme = gelismis_ayarlar["maks_deneme_sayisi"]

            while deneme <= maks_deneme and hedef_metin is None: 
                try:

                    prompt = (
                        "Sen profesyonel bir yazılım yerelleştirme uzmanısın.\n"
                        "Bu metin üretim ortamındaki bir . po çeviri dosyasından.\n\n"
                        "KESİN KURALLAR:\n"
                        "1) SADECE çevrilmiş metni çıktı ver, açıklama ekleme.\n"
                        "2) Yer tutucuları AYNEN koru (%s, %1$s, {name}, {{count}}, [tag]).\n"
                        "3) HTML etiketlerini ve sırasını değiştirme (<b>, </b>, <a>, vb.).\n"
                        "4) URL, email, dosya yolları, versiyon numaralarını çevirme.\n"
                        "5) Teknik terimler (API, URL, Email, ID) aynı kalabilir.\n"
                        "6) UI etiketleri kısa ve doğal olmalı - uzatma.\n"
                        "7) Eğer metin çevrilemez veya anlamsızsa, olduğu gibi döndür.\n"
                        "8) Kesinlikle 'Translation:', 'Here is', 'Çeviri: ' gibi ön ekler ekleme.\n\n"
                        f"Kaynak dil: {kaynak_dil}\n"
                        f"Hedef dil: {hedef_dil}\n"
                        f"Bağlam: {context if context != '__NO_CONTEXT__' else 'Yok'}\n\n"
                        f"METİN:\n{kaynak_metin}"
                    )

                    yanit = istemci.chat. completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "Yazılım UI metinleri çeviriyorsun.  Sadece çeviriyi döndür, açıklama ekleme. "},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=gelismis_ayarlar. get("temperature", 0.05),
                        max_tokens=gelismis_ayarlar. get("max_tokens", 500),
                        top_p=gelismis_ayarlar. get("top_p", 0.9)
                    )

                    temiz = temizle_metin(yanit.choices[0].message.content)

                    if not temiz:
                        logger.warning(f"Model boş çıktı döndü: {kaynak_metin}")
                        hata_sayaci["EMPTY_OUTPUT"] += 1
                        if deneme >= maks_deneme:

                            hedef_metin = kaynak_metin
                            log_cb(f"⚠️ Fallback (boş çıktı): {kaynak_metin}")
                            break
                        deneme += 1
                        continue
                        
                    if not _yer_tutucular_uyumlu(kaynak_metin, temiz):
                        logger.warning(f"Placeholder uyumsuzluğu: {kaynak_metin} -> {temiz}")
                        hata_sayaci["PLACEHOLDER_MISMATCH"] += 1
                        if deneme >= maks_deneme:

                            hedef_metin = kaynak_metin
                            log_cb(f"⚠️ Fallback (placeholder hatası): {kaynak_metin}")
                            break
                        deneme += 1
                        continue
                        
                    if not _ceviri_gecerli(kaynak_metin, temiz):
                        logger.warning(f"Model output validation başarısız: {kaynak_metin} -> {temiz}")
                        hata_sayaci["VALIDATION_FAILED"] += 1

                        if temiz. strip() == kaynak_metin.strip():
                            hedef_metin = kaynak_metin
                            log_cb(f"📌 Teknik terim korundu: {kaynak_metin}")
                            break
                        
                        if deneme >= maks_deneme: 

                            hedef_metin = kaynak_metin
                            log_cb(f"⚠️ Fallback (validation hatası): {kaynak_metin}")
                            break
                        deneme += 1
                        continue

                    hedef_metin = temiz
                    break

                except Exception as e: 
                    hata_str = str(e).lower()

                    if "rate" in hata_str or "429" in hata_str: 
                        bekleme_suresi = (2 ** deneme)
                        logger.warning(f"Rate limit, {bekleme_suresi}s bekleniyor...  (deneme {deneme}/{maks_deneme})")
                        time.sleep(bekleme_suresi)
                        hata_sayaci["RATE_LIMIT"] += 1

                    elif "connection" in hata_str or "timeout" in hata_str: 
                        logger.warning(f"Network hatası, tekrar deneniyor... (deneme {deneme}/{maks_deneme})")
                        time.sleep(1)
                        hata_sayaci["NETWORK_ERROR"] += 1

                    else:
                        logger.error(f"API hatası: {e}")
                        hata_sayaci["API_ERROR"] += 1

                        if deneme >= maks_deneme: 
                            hedef_metin = kaynak_metin
                            log_cb(f"⚠️ Fallback (API hatası): {kaynak_metin}")
                            break
                
                deneme += 1

            if hedef_metin is not None:
                entry.msgstr = hedef_metin
                cevrilen += 1
                if tercihe_kaydet: 
                    tercihler[bellek_anahtar] = hedef_metin
                    _tercihler_dirty = True
                    _tercihler_counter += 1
                log_cb(f"{kaynak_metin} → {hedef_metin}")
            else:

                atlanan += 1
                hata_sayaci["MODEL_INVALID"] += 1
                log_cb(f"❌ Çevrilemedi: {kaynak_metin}")

            if _tercihler_counter >= TERCIHLER_SAVE_INTERVAL and _tercihler_dirty: 
                _kaydet_tercihler()
                _tercihler_dirty = False
                _tercihler_counter = 0
                log_cb(f"💾 Tercihler kaydedildi (periyodik)")

        if cevrilen > 0:

            yeni_ad = os.path.splitext(dosya_yolu)[0] + f"_{yon}_CEVRILDI. po"
            try:
                po. save(yeni_ad)
                log_cb(f"✅ Kaydedildi: {yeni_ad}")

                if _tercihler_dirty and tercihe_kaydet:
                    _kaydet_tercihler()
                    _tercihler_dirty = False
                    _tercihler_counter = 0
                    
            except Exception as e:
                logger.error(f"Dosya kaydetme hatası: {e}")
                log_cb(f"❌ HATA:  Dosya kaydedilemedi: {e}")
                hata_sayaci["FILE_SAVE_ERROR"] += 1

        done_cb(cevrilen, atlanan, dict(hata_sayaci))

    except Exception as e:
        log_cb(f"❌ Kritik hata: {e}")
        done_cb(0, 0, {"EXCEPTION": 1})

def onizleme_cevir(
    api_anahtar,
    dosya_yolu,
    model,
    yon,
    log_cb,
    done_cb,
    onizleme_sayisi=None
):

    _durdur_olayi. clear()
    
    if onizleme_sayisi is None:
        onizleme_sayisi = gelismis_ayarlar["onizleme_entry_sayisi"]

    try:
        kaynak_kod, hedef_kod = yon.split("-")
        kaynak_dil = DIL_KODLARI.get(kaynak_kod, "English")
        hedef_dil = DIL_KODLARI.get(hedef_kod, "Turkish")
    except (ValueError, AttributeError):
        kaynak_dil = "English"
        hedef_dil = "Turkish"
    
    try:
        gercek_api_anahtar = _api_anahtari_al(api_anahtar)
        istemci = OpenAI(api_key=gercek_api_anahtar, timeout=30.0)
    except ValueError as e:
        log_cb(f"❌ HATA: {e}")
        done_cb(None)
        return None
    
    try:
        po = polib.pofile(dosya_yolu)
        entries = [e for e in po if not e.translated() and (e.msgid or "").strip()]
        toplam = len(entries)
        
        if toplam == 0:
            log_cb("⚠️ Çevrilecek entry bulunamadı")
            done_cb(None)
            return None

        onizleme_entries = entries[:min(onizleme_sayisi, toplam)]
        
        log_cb(f"📊 Toplam {toplam} entry bulundu, ilk {len(onizleme_entries)} önizleme için çevriliyor...")
        
        cevrilen = 0
        ornekler = []
        
        for i, entry in enumerate(onizleme_entries):
            kaynak_metin = entry.msgid.strip()
            context = _context_al(entry)

            if _cevirilmez_mi(kaynak_metin):
                hedef_metin = kaynak_metin
                log_cb(f"↩ Çevrilmedi (sabit): {kaynak_metin}")

            elif kaynak_metin in ozel_sozluk:
                hedef_metin = ozel_sozluk[kaynak_metin]
                cevrilen += 1
                ornekler.append({"kaynak": kaynak_metin, "hedef": hedef_metin})
                log_cb(f"📖 {kaynak_metin} → {hedef_metin} (Özel Sözlük)")
            else: 

                hedef_metin = None
                deneme = 1
                maks_deneme = 2
                
                while deneme <= maks_deneme and hedef_metin is None: 
                    try:

                        prompt = (
                            "Sen profesyonel bir yazılım yerelleştirme uzmanısın.\n"
                            "Bu metin üretim ortamındaki bir .po çeviri dosyasından.\n\n"
                            "KESİN KURALLAR:\n"
                            "1) SADECE çevrilmiş metni çıktı ver, açıklama ekleme.\n"
                            "2) Yer tutucuları AYNEN koru (%s, %1$s, {name}, {{count}}, [tag]).\n"
                            "3) HTML etiketlerini ve sırasını değiştirme (<b>, </b>, <a>, vb.).\n"
                            "4) URL, email, dosya yolları, versiyon numaralarını çevirme.\n"
                            "5) Teknik terimler (API, URL, Email, ID) aynı kalabilir.\n"
                            "6) UI etiketleri kısa ve doğal olmalı - uzatma.\n"
                            "7) Eğer metin çevrilemez veya anlamsızsa, olduğu gibi döndür.\n"
                            "8) Kesinlikle 'Translation:', 'Here is', 'Çeviri: ' gibi ön ekler ekleme.\n\n"
                            f"Kaynak dil: {kaynak_dil}\n"
                            f"Hedef dil: {hedef_dil}\n"
                            f"Bağlam: {context if context != '__NO_CONTEXT__' else 'Yok'}\n\n"
                            f"METİN:\n{kaynak_metin}"
                        )
                        
                        yanit = istemci.chat. completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": "Yazılım UI metinleri çeviriyorsun. Sadece çeviriyi döndür, açıklama ekleme."},
                                {"role":  "user", "content": prompt}
                            ],
                            temperature=gelismis_ayarlar.get("temperature", 0.05),
                            max_tokens=gelismis_ayarlar.get("max_tokens", 500),
                            top_p=gelismis_ayarlar.get("top_p", 0.9)
                        )
                        
                        temiz = temizle_metin(yanit.choices[0].message. content)

                        if temiz and _yer_tutucular_uyumlu(kaynak_metin, temiz) and _ceviri_gecerli(kaynak_metin, temiz):
                            hedef_metin = temiz
                            break
                        elif deneme >= maks_deneme:

                            hedef_metin = kaynak_metin
                            break
                            
                    except Exception as e: 
                        deneme += 1
                        if deneme > maks_deneme:
                            hedef_metin = kaynak_metin
                            break
                
                if hedef_metin: 
                    cevrilen += 1
                    ornekler. append({"kaynak": kaynak_metin, "hedef":  hedef_metin})
                    log_cb(f"✓ {kaynak_metin} → {hedef_metin}")
                else:
                    log_cb(f"❌ Çevrilemedi: {kaynak_metin}")
        
        sonuc = {
            "toplam_entry": toplam,
            "onizleme_sayisi": len(onizleme_entries),
            "cevrilen": cevrilen,
            "ornekler": ornekler
        }
        
        log_cb(f"\n📊 ÖNİZLEME SONUCU:")
        log_cb(f"   Toplam entry: {toplam}")
        log_cb(f"   Önizleme:  {len(onizleme_entries)} entry")
        log_cb(f"   Başarılı: {cevrilen} çeviri")
        log_cb(f"\n💡 Devam etmek için 'Çeviriyi Başlat' butonunu kullanın.")
        
        done_cb(sonuc)
        return sonuc
        
    except Exception as e:
        log_cb(f"❌ Kritik hata: {e}")
        done_cb(None)
        return None

def toplu_geri_al(log_cb, done_cb):

    if not os.path.exists(REPORT_DIR):
        log_cb("❌ Rapor klasörü bulunamadı")
        done_cb(False)
        return
    
    raporlar = [f for f in os.listdir(REPORT_DIR) if f.startswith("batch_") and f.endswith(".json")]
    
    if not raporlar: 
        log_cb("❌ Geri alınacak batch işlemi bulunamadı")
        done_cb(False)
        return

    raporlar.sort(reverse=True)
    son_rapor = os.path.join(REPORT_DIR, raporlar[0])
    
    try:
        with open(son_rapor, "r", encoding="utf-8") as f:
            rapor = json.load(f)
        
        log_cb(f"📋 Son batch raporu bulundu:  {raporlar[0]}")
        log_cb(f"   Tarih: {rapor. get('tarih', 'Bilinmiyor')}")
        log_cb(f"   Klasör: {rapor.get('klasor', 'Bilinmiyor')}")
        log_cb(f"   Çevrilen: {rapor.get('toplam_cevrilen', 0)} entry")
        log_cb("")
        
        silinen = 0
        hata = 0
        
        for dosya_info in rapor.get("dosyalar", []):
            dosya_adi = dosya_info.get("dosya", "")

            klasor = rapor.get("klasor", "")
            orijinal_yol = os.path.join(klasor, dosya_adi)

            base_name = orijinal_yol.replace(".po", "")
            pattern = f"{base_name}_*_CEVRILDI.po"
            
            for cevrilen_dosya in glob.glob(pattern):
                try:
                    os.remove(cevrilen_dosya)
                    log_cb(f"🗑️ Silindi: {os.path.basename(cevrilen_dosya)}")
                    silinen += 1
                except (OSError, PermissionError) as e:
                    log_cb(f"❌ Silinemedi: {os.path.basename(cevrilen_dosya)} - {e}")
                    hata += 1

        yedek_rapor = son_rapor.replace(". json", "_GERI_ALINDI.json")
        os.rename(son_rapor, yedek_rapor)
        
        log_cb("")
        log_cb(f"✅ Geri alma tamamlandı!")
        log_cb(f"   Silinen dosya: {silinen}")
        log_cb(f"   Hata:  {hata}")
        log_cb(f"   Rapor yedeklendi: {os.path.basename(yedek_rapor)}")
        
        done_cb(True)
        
    except Exception as e: 
        log_cb(f"❌ Geri alma hatası: {e}")
        done_cb(False)

def cevir_klasor(
    api_anahtar,
    klasor_yolu,
    model,
    tercihe_kaydet,
    yon,
    progress_cb,
    log_cb,
    done_cb
):

    po_dosyalari = [
        os.path.join(klasor_yolu, f)
        for f in os.listdir(klasor_yolu)
        if f.lower().endswith(".po")
    ]

    if not po_dosyalari:
        log_cb("❌ Klasörde . po bulunamadı.")
        done_cb(0, 0, {})
        return

    rapor = {
        "klasor": klasor_yolu,
        "tarih": datetime.now().isoformat(),
        "dosyalar": [],
        "toplam_cevrilen": 0,
        "toplam_atlanan": 0
    }

    for idx, po_yolu in enumerate(po_dosyalari, start=1):
        if _durdur_olayi.is_set():
            break

        def _progress(v, m):
            tamamlanan_dosyalar = idx - 1
            mevcut_dosya_orani = v / m if m > 0 else 0
            toplam_oran = (tamamlanan_dosyalar + mevcut_dosya_orani) / len(po_dosyalari)
            progress_cb(toplam_oran * len(po_dosyalari), len(po_dosyalari))

        def _done(c, a, h):
            rapor["dosyalar"].append({
                "dosya": os.path.basename(po_yolu),
                "cevrilen": c,
                "atlanan": a,
                "hatalar": h
            })
            rapor["toplam_cevrilen"] += c
            rapor["toplam_atlanan"] += a

        cevir(
            api_anahtar,
            po_yolu,
            model,
            tercihe_kaydet,
            yon,
            _progress,
            log_cb,
            _done
        )

    rapor_yolu = os.path.join(
        REPORT_DIR,
        f"batch_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
    )

    with open(rapor_yolu, "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=4)

    log_cb(f"📊 Batch raporu oluşturuldu: {rapor_yolu}")
    done_cb(rapor["toplam_cevrilen"], rapor["toplam_atlanan"], {})
