import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import json
import os
import logging
from datetime import datetime

import ceviri
from i18n import i18n
from ui_texts import ui_texts

class UIMessageType:
    LOG = "log"
    PROGRESS = "progress"
    DONE = "done"
    STATS = "stats"
    ONIZLEME_DONE = "onizleme_done"
    GERI_AL_DONE = "geri_al_done"

CONFIG_PATH = "ayarlar.json"

_gui_logger = logging.getLogger("ceviri_gui")

def _yukle_ayarlar():

    varsayilan = {
        "api_key": "",
        "model": "gpt-4o-mini",
        "yon": "EN-TR",
        "auto_save": True,
        "dil": "tr_TR"
    }
    
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                yuklenen = json.load(f)
                varsayilan.update(yuklenen)
        except Exception as e:
            pass
    
    return varsayilan

cfg = _yukle_ayarlar()
i18n.yukle(cfg.get("dil", "tr_TR"))
_ = i18n._

root = tk.Tk()
root.geometry("850x700")
root.minsize(850, 700)

ui_queue = queue.Queue()
worker_lock = threading.Lock()
worker_running = False

def log_cb(msg):
    ui_queue.put((UIMessageType.LOG, msg))

def progress_cb(val, maxv):
    ui_queue.put((UIMessageType.PROGRESS, val, maxv))

def done_cb(ok, skip, hatalar=None):
    toplam_hata = sum(hatalar.values()) if hatalar else 0
    ui_queue.put((UIMessageType.DONE, ok, skip, hatalar or {}, toplam_hata))

def durdur_click():
    ceviri.durdur_islem()
    status_var.set(_("⏹️ Durduruluyor..."))
    log_text.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {_('⚠️ Durdurma isteği gönderildi...')}\n")
    log_text.see("end")

stats = {"cevrilen": 0, "atlanan": 0, "hata": 0}

def set_ui_state(running: bool):
    state = "disabled" if running else "normal"
    btn_start.config(state=state)
    btn_onizleme.config(state=state)
    btn_file.config(state=state)
    btn_folder.config(state=state)
    btn_stop.config(state="normal" if running else "disabled")
    combo_model.config(state="disabled" if running else "readonly")
    combo_yon.config(state="disabled" if running else "readonly")
    chk_kaydet.config(state=state)
    entry_path.config(state=state)
    entry_api.config(state=state)

def ui_poller():
    global worker_running
    try:
        while True:
            item = ui_queue.get_nowait()

            if item[0] == UIMessageType.LOG:

                try:
                    lines = int(log_text.index("end-1c").split('.')[0])
                    if lines > 500:

                        log_text.delete("1.0", "250.0")
                except (ValueError, IndexError):

                    pass

                log_text.insert(
                    "end",
                    f"[{datetime.now().strftime('%H:%M:%S')}] {item[1]}\n"
                )
                log_text.see("end")

                msg = item[1]
                if "→" in msg and "Bellek" not in msg and "Özel Sözlük" not in msg:
                    stats["cevrilen"] += 1
                    ui_queue.put((UIMessageType.STATS, "cevrilen", stats["cevrilen"]))
                elif "❌" in msg:
                    stats["atlanan"] += 1
                    ui_queue.put((UIMessageType.STATS, "atlanan", stats["atlanan"]))

            elif item[0] == UIMessageType.STATS:
                stat_type, value = item[1], item[2]
                if stat_type == "cevrilen":
                    cevrilen_label.config(text=_("✔ Çevrilen: ") + str(value))
                elif stat_type == "atlanan":
                    atlanan_label.config(text=_("⚠ Atlanan: ") + str(value))
                elif stat_type == "hata":
                    hata_label.config(text=_("❌ Hata: ") + str(value))

            elif item[0] == UIMessageType.PROGRESS:
                progress["maximum"] = item[2]
                progress["value"] = item[1]
                status_var.set(_("İşleniyor: {} / {}").format(item[1], item[2]))

            elif item[0] == UIMessageType.DONE:
                global worker_running
                ok, skip, hatalar, toplam_hata = item[1], item[2], item[3], item[4]

                stats["hata"] = toplam_hata
                ui_queue.put((UIMessageType.STATS, "hata", toplam_hata))
                
                hata_txt = f"\n{_('Hata')}: {hatalar}" if hatalar else ""
                status_var.set(f"✔ {_('İşlem Tamamlandı')} | {_('Çevrilen: ')}{ok} | {_('Atlanan: ')}{skip}")
                messagebox.showinfo(
                    _("İşlem Tamamlandı"),
                    f"{_('Çevrilen: ')}{ok}\n{_('Atlanan: ')}{skip}{hata_txt}"
                )
                set_ui_state(running=False)
                with worker_lock:
                    worker_running = False

            elif item[0] == UIMessageType.ONIZLEME_DONE:
                sonuc = item[1]
                
                if sonuc:
                    mesaj = _("Önizleme Tamamlandı!\n\nToplam Entry: {}\nÖnizleme: {} entry\nBaşarılı: {} çeviri\n\nDevam etmek istiyor musunuz?").format(
                        sonuc['toplam_entry'],
                        sonuc['onizleme_sayisi'],
                        sonuc['cevrilen']
                    )
                    
                    if messagebox.askyesno(_("Önizleme Sonucu"), mesaj):
                        status_var.set(_("✔ Önizleme tamamlandı - Tam çeviri için 'Çeviriyi Başlat' butonunu kullanın"))
                    else:
                        status_var.set(_("Önizleme iptal edildi"))
                else:
                    status_var.set(_("❌ Önizleme başarısız"))
                
                set_ui_state(running=False)
                with worker_lock:
                    worker_running = False

            elif item[0] == UIMessageType.GERI_AL_DONE:
                basarili = item[1]
                if basarili:
                    status_var.set(_("✅ Geri alma tamamlandı"))
                    messagebox.showinfo(_("Başarılı"), _("Son batch işlemi geri alındı"))
                else:
                    status_var.set(_("❌ Geri alma başarısız"))
                    messagebox.showerror(_("Hata"), _("Geri alma işlemi başarısız"))

    except queue.Empty:
        pass
    finally:
        root.after(100, ui_poller)

def dosya_sec():
    path = filedialog.askopenfilename(filetypes=[("PO Dosyası", "*.po")])
    if path:
        path_var.set(path)
        is_folder_var.set(False)
        status_var.set(_("Dosya seçildi"))

def klasor_sec():
    path = filedialog.askdirectory()
    if path:
        path_var.set(path)
        is_folder_var.set(True)
        status_var.set(_("Klasör seçildi (Batch)"))

def onizleme_baslat():
    global worker_running
    
    with worker_lock:
        if worker_running:
            messagebox.showwarning(_("Uyarı"), _("Zaten bir işlem devam ediyor"))
            return
        worker_running = True
    
    dosya = path_var.get().strip()
    api_anahtar = api_key_var.get().strip()
    
    if not dosya or not os.path.exists(dosya):
        messagebox.showwarning(_("Uyarı"), _("Geçerli bir dosya seçin."))
        with worker_lock:
            worker_running = False
        return
    
    if is_folder_var.get():
        messagebox.showinfo(_("Bilgi"), _("Önizleme modu sadece tek dosya için çalışır.\nLütfen bir .po dosyası seçin."))
        with worker_lock:
            worker_running = False
        return
    
    log_text.delete("1.0", "end")
    status_var.set(_("🔍 Önizleme başlatılıyor..."))
    set_ui_state(running=True)
    
    def onizleme_done_cb(sonuc):
        ui_queue.put((UIMessageType.ONIZLEME_DONE, sonuc))
    
    t = threading.Thread(
        target=ceviri.onizleme_cevir,
        daemon=True,
        args=(
            api_anahtar,
            dosya,
            model_var.get(),
            yon_var.get(),
            log_cb,
            onizleme_done_cb
        )
    )
    t.start()

def geri_al_baslat():

    if not messagebox.askyesno(
        _("Onay"), 
        _("Son batch çeviri işlemini geri almak istediğinizden emin misiniz?\n\nÇevrilmiş tüm dosyalar silinecek!")
    ):
        return
    
    log_text.delete("1.0", "end")
    status_var.set(_("🔄 Geri alma işlemi başlatılıyor..."))
    
    def geri_al_done_cb(basarili):
        ui_queue.put((UIMessageType.GERI_AL_DONE, basarili))
    
    t = threading.Thread(
        target=ceviri.toplu_geri_al,
        daemon=True,
        args=(log_cb, geri_al_done_cb)
    )
    t.start()

def sozluk_duzenle():

    sozluk_pencere = tk.Toplevel(root)
    sozluk_pencere.title(_("Özel Sözlük Düzenleyici"))
    sozluk_pencere.geometry("600x400")

    aciklama = ttk.Label(
        sozluk_pencere, 
        text=_("Özel terimlerinizi ekleyin. Bu terimler model yerine direkt kullanılacak."),
        font=("Segoe UI", 9)
    )
    aciklama.pack(pady=10)

    frame = ttk.Frame(sozluk_pencere)
    frame.pack(fill="both", expand=True, padx=10, pady=5)

    tree = ttk.Treeview(frame, columns=("kaynak", "hedef"), show="headings")
    tree.heading("kaynak", text=_("Kaynak Metin"))
    tree.heading("hedef", text=_("Hedef Metin"))
    tree.column("kaynak", width=250)
    tree.column("hedef", width=250)
    tree.pack(side="left", fill="both", expand=True)
    
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    scrollbar.pack(side="right", fill="y")
    tree.configure(yscrollcommand=scrollbar.set)

    def yukle_sozluk():
        tree.delete(*tree.get_children())
        if os.path.exists("sozluk.json"):
            try:
                with open("sozluk.json", "r", encoding="utf-8") as f:
                    sozluk = json.load(f)
                    for k, v in sozluk.items():
                        if not k.startswith("_"):
                            tree.insert("", "end", values=(k, v))
            except Exception as e:
                messagebox.showerror(_("Hata"), _("Sözlük yüklenemedi: {}").format(e))
    
    yukle_sozluk()

    btn_frame = ttk.Frame(sozluk_pencere)
    btn_frame.pack(pady=10)
    
    def ekle():
        ekle_pencere = tk.Toplevel(sozluk_pencere)
        ekle_pencere.title(_("Yeni Terim Ekle"))
        ekle_pencere.geometry("400x150")
        
        ttk.Label(ekle_pencere, text=_("Kaynak Metin:")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        kaynak_entry = ttk.Entry(ekle_pencere, width=30)
        kaynak_entry.grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(ekle_pencere, text=_("Hedef Metin:")).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        hedef_entry = ttk.Entry(ekle_pencere, width=30)
        hedef_entry.grid(row=1, column=1, padx=10, pady=10)
        
        def kaydet():
            kaynak = kaynak_entry.get().strip()
            hedef = hedef_entry.get().strip()
            
            if not kaynak or not hedef:
                messagebox.showwarning(_("Uyarı"), _("Her iki alanı da doldurun"))
                return
            
            tree.insert("", "end", values=(kaynak, hedef))
            ekle_pencere.destroy()
        
        ttk.Button(ekle_pencere, text=_("Ekle"), command=kaydet).grid(row=2, column=1, pady=10)
    
    def sil():
        secili = tree.selection()
        if not secili:
            messagebox.showwarning(_("Uyarı"), _("Silinecek terimi seçin"))
            return
        tree.delete(secili)
    
    def kaydet_sozluk():
        yeni_sozluk = {
            "_aciklama": "Özel terimler ve çevirileri. 'kaynak': 'hedef' formatında.",
        }
        
        for item in tree.get_children():
            kaynak, hedef = tree.item(item)["values"]
            yeni_sozluk[kaynak] = hedef
        
        try:
            with open("sozluk.json", "w", encoding="utf-8") as f:
                json.dump(yeni_sozluk, f, ensure_ascii=False, indent=4)
            messagebox.showinfo(_("Başarılı"), _("Sözlük kaydedildi"))

            ceviri.sozluk_guncelle(yeni_sozluk)
            
        except Exception as e:
            messagebox.showerror(_("Hata"), _("Sözlük kaydedilemedi: {}").format(e))
    
    ttk.Button(btn_frame, text=_("Yeni Ekle"), command=ekle).pack(side="left", padx=5)
    ttk.Button(btn_frame, text=_("Sil"), command=sil).pack(side="left", padx=5)
    ttk.Button(btn_frame, text=_("Kaydet"), command=kaydet_sozluk).pack(side="left", padx=5)

def gelismis_ayarlar():

    ayarlar_pencere = tk.Toplevel(root)
    ayarlar_pencere.title(_("Gelişmiş Ayarlar"))
    ayarlar_pencere.geometry("500x350")

    mevcut = ceviri.gelismis_ayarlar.copy()

    ttk.Label(ayarlar_pencere, text=_("Model Temperature (0.0 - 1.0):")).grid(row=0, column=0, padx=20, pady=10, sticky="w")
    temp_var = tk.DoubleVar(value=mevcut["temperature"])
    temp_scale = ttk.Scale(ayarlar_pencere, from_=0.0, to=1.0, orient="horizontal", variable=temp_var, length=200)
    temp_scale.grid(row=0, column=1, padx=20, pady=10)
    temp_label = ttk.Label(ayarlar_pencere, text=f"{mevcut['temperature']:.2f}")
    temp_label.grid(row=0, column=2, padx=10)
    
    def temp_update(val):
        temp_label.config(text=f"{float(val):.2f}")
    temp_scale.config(command=temp_update)

    ttk.Label(ayarlar_pencere, text=_("Maksimum Deneme Sayısı:")).grid(row=1, column=0, padx=20, pady=10, sticky="w")
    deneme_var = tk.IntVar(value=mevcut["maks_deneme_sayisi"])
    deneme_spin = ttk.Spinbox(ayarlar_pencere, from_=1, to=5, textvariable=deneme_var, width=10)
    deneme_spin.grid(row=1, column=1, padx=20, pady=10, sticky="w")
    
    ttk.Label(ayarlar_pencere, text=_("Tercihler Kayıt Aralığı:")).grid(row=2, column=0, padx=20, pady=10, sticky="w")
    tercih_var = tk.IntVar(value=mevcut["tercihler_kayit_araligi"])
    tercih_spin = ttk.Spinbox(ayarlar_pencere, from_=10, to=200, increment=10, textvariable=tercih_var, width=10)
    tercih_spin.grid(row=2, column=1, padx=20, pady=10, sticky="w")

    ttk.Label(ayarlar_pencere, text=_("Log Saklama Süresi (gün):")).grid(row=3, column=0, padx=20, pady=10, sticky="w")
    log_var = tk.IntVar(value=mevcut["log_saklama_gun"])
    log_spin = ttk.Spinbox(ayarlar_pencere, from_=7, to=90, increment=7, textvariable=log_var, width=10)
    log_spin.grid(row=3, column=1, padx=20, pady=10, sticky="w")

    ttk.Label(ayarlar_pencere, text=_("Önizleme Entry Sayısı:")).grid(row=4, column=0, padx=20, pady=10, sticky="w")
    onizleme_var = tk.IntVar(value=mevcut["onizleme_entry_sayisi"])
    onizleme_spin = ttk.Spinbox(ayarlar_pencere, from_=5, to=50, increment=5, textvariable=onizleme_var, width=10)
    onizleme_spin.grid(row=4, column=1, padx=20, pady=10, sticky="w")
    
    def kaydet():
        yeni_ayarlar = {
            "temperature": round(temp_var.get(), 2),
            "maks_deneme_sayisi": deneme_var.get(),
            "tercihler_kayit_araligi": tercih_var.get(),
            "log_saklama_gun": log_var.get(),
            "onizleme_entry_sayisi": onizleme_var.get()
        }
        
        try:
            with open("gelismis_ayarlar.json", "w", encoding="utf-8") as f:
                json.dump(yeni_ayarlar, f, ensure_ascii=False, indent=4)

            ceviri.ayarlari_guncelle(yeni_ayarlar)
            
            messagebox.showinfo(_("Başarılı"), _("Gelişmiş ayarlar kaydedildi"))
            ayarlar_pencere.destroy()
            
        except Exception as e:
            messagebox.showerror(_("Hata"), _("Ayarlar kaydedilemedi: {}").format(e))
    
    def varsayilan():
        if messagebox.askyesno(_("Onay"), _("Varsayılan ayarlara dönmek istediğinizden emin misiniz?")):
            temp_var.set(0.1)
            deneme_var.set(2)
            tercih_var.set(50)
            log_var.set(30)
            onizleme_var.set(10)
    
    btn_frame = ttk.Frame(ayarlar_pencere)
    btn_frame.grid(row=5, column=0, columnspan=3, pady=20)
    
    ttk.Button(btn_frame, text=_("Kaydet"), command=kaydet).pack(side="left", padx=10)
    ttk.Button(btn_frame, text=_("Varsayılan"), command=varsayilan).pack(side="left", padx=10)
    ttk.Button(btn_frame, text=_("İptal"), command=ayarlar_pencere.destroy).pack(side="left", padx=10)

def baslat():
    global worker_running
    
    with worker_lock:
        if worker_running:
            messagebox.showwarning(_("Uyarı"), _("Zaten bir işlem devam ediyor"))
            return
        worker_running = True

    path = path_var.get().strip()
    api_key = api_key_var.get().strip()

    if not path or not os.path.exists(path):
        messagebox.showwarning(_("Uyarı"), _("Geçerli bir dosya veya klasör seçin."))
        with worker_lock:
            worker_running = False
        return

    try:

        gecici_dosya = CONFIG_PATH + ".tmp"
        with open(gecici_dosya, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "api_key": api_key,
                    "model": model_var.get(),
                    "yon": yon_var.get(),
                    "auto_save": kaydet_var.get(),
                    "dil": i18n.aktif_dil,
                },
                f,
                ensure_ascii=False,
                indent=2
            )
        os.replace(gecici_dosya, CONFIG_PATH)
    except Exception as e:
        _gui_logger.warning(f"Ayarlar kaydedilemedi: {e}")
        messagebox.showwarning(_("Uyarı"), _("Ayarlar kaydedilemedi: {}").format(e))

    log_text.delete("1.0", "end")
    progress["value"] = 0
    status_var.set(_("⏳ Çeviri başlatıldı..."))
    set_ui_state(running=True)
    
    stats["cevrilen"] = 0
    stats["atlanan"] = 0
    stats["hata"] = 0
    cevrilen_label.config(text=_("✔ Çevrilen: ") + "0")
    atlanan_label.config(text=_("⚠ Atlanan: ") + "0")
    hata_label.config(text=_("❌ Hata: ") + "0")

    target = ceviri.cevir_klasor if is_folder_var.get() else ceviri.cevir

    t = threading.Thread(
        target=target,
        daemon=True,
        args=(
            api_key,
            path,
            model_var.get(),
            kaydet_var.get(),
            yon_var.get(),
            progress_cb,
            log_cb,
            done_cb
        )
    )
    t.start()

main = ttk.Frame(root, padding=20)
main.pack(fill="both", expand=True)
main.columnconfigure(1, weight=1)

DIL_GOSTERIM = {
    "tr_TR": "🇹🇷 Türkçe",
    "en_US": "🇬🇧 English"
}

GOSTERIM_DIL = {v: k for k, v in DIL_GOSTERIM.items()}

dil_frame = ttk.Frame(main, padding=5)
dil_frame.grid(row=0, column=0, columnspan=2, sticky="e", pady=5)

lbl_dil = ttk.Label(dil_frame)
lbl_dil.pack(side="left", padx=5)
ui_texts.kaydet(lbl_dil, "Dil:")

mevcut_gosterim = DIL_GOSTERIM.get(i18n.aktif_dil, i18n.aktif_dil)
dil_var = tk.StringVar(value=mevcut_gosterim)

dil_combo = ttk.Combobox(
    dil_frame, 
    textvariable=dil_var, 
    values=list(DIL_GOSTERIM.values()),
    state="readonly", 
    width=15
)
dil_combo.pack(side="left")

def dil_degistir(*args):
    gosterim = dil_var.get()
    yeni_dil = GOSTERIM_DIL.get(gosterim, "tr_TR")
    
    if yeni_dil == i18n.aktif_dil:
        return
    
    i18n.yukle(yeni_dil)
    
    global _
    _ = i18n._
    
    ui_texts.guncelle(i18n._)
    
    root.title(_("GPT Destekli Otomatik .PO Çeviri v 3.0.3 - Muharrem DANIŞMAN"))
    
    cevrilen_label.config(text=_("✔ Çevrilen: ") + str(stats["cevrilen"]))
    atlanan_label.config(text=_("⚠ Atlanan: ") + str(stats["atlanan"]))
    hata_label.config(text=_("❌ Hata: ") + str(stats["hata"]))
    
    status_var.set(_("Hazır"))
    
    try:
        mevcut_cfg = _yukle_ayarlar()
        mevcut_cfg["dil"] = yeni_dil
        gecici_dosya = CONFIG_PATH + ".tmp"
        with open(gecici_dosya, "w", encoding="utf-8") as f:
            json.dump(mevcut_cfg, f, ensure_ascii=False, indent=2)
        os.replace(gecici_dosya, CONFIG_PATH)
    except Exception as e:
        _gui_logger.warning(f"Dil tercihi kaydedilemedi: {e}")

dil_combo.bind("<<ComboboxSelected>>", dil_degistir)

api_frame = ttk.LabelFrame(main, padding=10)
api_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
ui_texts.kaydet(api_frame, " API ", "text")

lbl_api = ttk.Label(api_frame)
lbl_api.pack(side="left")
ui_texts.kaydet(lbl_api, "OpenAI API Key (opsiyonel):")

api_key_var = tk.StringVar()
entry_api = ttk.Entry(api_frame, textvariable=api_key_var, show="*", width=50)
entry_api.pack(side="left", padx=5)

path_frame = ttk.LabelFrame(main, padding=10)
path_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
ui_texts.kaydet(path_frame, " Kaynak ", "text")

path_var = tk.StringVar()
is_folder_var = tk.BooleanVar(value=False)

entry_path = ttk.Entry(path_frame, textvariable=path_var, width=60)
entry_path.pack(side="left", padx=5)

btn_file = ttk.Button(path_frame, command=dosya_sec)
btn_file.pack(side="left", padx=2)
ui_texts.kaydet(btn_file, "Dosya Seç", "text")

btn_folder = ttk.Button(path_frame, command=klasor_sec)
btn_folder.pack(side="left", padx=2)
ui_texts.kaydet(btn_folder, "Klasör Seç", "text")

opt_frame = ttk.LabelFrame(main, padding=10)
opt_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
ui_texts.kaydet(opt_frame, " Ayarlar ", "text")

model_var = tk.StringVar(value="gpt-4o-mini")
yon_var = tk.StringVar(value="EN-TR")
kaydet_var = tk.BooleanVar(value=True)

lbl_model = ttk.Label(opt_frame)
lbl_model.grid(row=0, column=0, sticky="w")
ui_texts.kaydet(lbl_model, "Model:")

combo_model = ttk.Combobox(
    opt_frame,
    textvariable=model_var,
    values=["gpt-4o", "gpt-4o-mini"],
    state="readonly"
)
combo_model.grid(row=0, column=1, sticky="w")

lbl_yon = ttk.Label(opt_frame)
lbl_yon.grid(row=0, column=2, sticky="w", padx=10)
ui_texts.kaydet(lbl_yon, "Yön:")

combo_yon = ttk.Combobox(
    opt_frame,
    textvariable=yon_var,
    values=[
        "EN-TR",  # İngilizce → Türkçe
        "TR-EN",  # Türkçe → İngilizce
        "FR-TR",  # Fransızca → Türkçe
        "TR-FR",  # Türkçe → Fransızca
        "DE-TR",  # Almanca → Türkçe
        "TR-DE",  # Türkçe → Almanca
        "ES-TR",  # İspanyolca → Türkçe
        "TR-ES",  # Türkçe → İspanyolca
        "IT-TR",  # İtalyanca → Türkçe
        "TR-IT",  # Türkçe → İtalyanca
        "PT-TR",  # Portekizce → Türkçe
        "TR-PT",  # Türkçe → Portekizce
    ],
    state="readonly",
    width=15
)
combo_yon.grid(row=0, column=3, sticky="w")

chk_kaydet = ttk.Checkbutton(
    opt_frame,
    variable=kaydet_var
)
chk_kaydet.grid(row=1, column=0, columnspan=2, sticky="w", pady=5)
ui_texts.kaydet(chk_kaydet, "Belleğe Kaydet (tercihler.json)", "text")

btn_frame = ttk.Frame(main)
btn_frame.grid(row=4, column=0, columnspan=2, pady=10)

btn_onizleme = ttk.Button(btn_frame, width=22, command=onizleme_baslat)
btn_onizleme.pack(side="left", padx=10)
ui_texts.kaydet(btn_onizleme, "Önizleme (10 Entry)", "text")

btn_start = ttk.Button(btn_frame, width=22, command=baslat)
btn_start.pack(side="left", padx=10)
ui_texts.kaydet(btn_start, "Çeviriyi Başlat", "text")

btn_stop = ttk.Button(btn_frame, width=22, command=durdur_click)
btn_stop.pack(side="left", padx=10)
btn_stop.config(state="disabled")
ui_texts.kaydet(btn_stop, "Durdur", "text")

stats_frame = ttk.Frame(main)
stats_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=5)

cevrilen_label = ttk.Label(stats_frame, font=("Segoe UI", 9))
cevrilen_label.pack(side="left", padx=10)

atlanan_label = ttk.Label(stats_frame, font=("Segoe UI", 9))
atlanan_label.pack(side="left", padx=10)

hata_label = ttk.Label(stats_frame, font=("Segoe UI", 9))
hata_label.pack(side="left", padx=10)

status_var = tk.StringVar()
ttk.Label(main, textvariable=status_var, font=("Segoe UI", 10, "bold")).grid(
    row=6, column=0, columnspan=2, sticky="w"
)

progress = ttk.Progressbar(main, orient="horizontal", mode="determinate")
progress.grid(row=7, column=0, columnspan=2, sticky="ew", pady=10)
log_frame = ttk.LabelFrame(main, padding=5)
log_frame.grid(row=8, column=0, columnspan=2, sticky="nsew")
main.rowconfigure(8, weight=1)
ui_texts.kaydet(log_frame, " İşlem Logları ", "text")

log_text = tk.Text(log_frame, font=("Consolas", 9), bg="#f4f4f4")
log_text.pack(fill="both", expand=True)

menu_bar = tk.Menu(root)
root.config(menu=menu_bar)

_araclar_menu_ref = None

araclar_menu = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(menu=araclar_menu, label=_("Araçlar"))
_araclar_menu_ref = araclar_menu

def update_menu_labels():
    araclar_menu.delete(0, "end")
    araclar_menu.add_command(label=_("Özel Sözlük Düzenle"), command=sozluk_duzenle)
    araclar_menu.add_command(label=_("Gelişmiş Ayarlar"), command=gelismis_ayarlar)
    araclar_menu.add_separator()
    araclar_menu.add_command(label=_("Son Batch'i Geri Al"), command=geri_al_baslat)

update_menu_labels()

original_guncelle = ui_texts.guncelle

def guncelle_with_menu(ceviri_fonk):
    original_guncelle(ceviri_fonk)
    
    update_menu_labels()
    
    try:

        menu_bar.entryconfigure(_("Araçlar"), label=ceviri_fonk("Araçlar"))
    except (tk.TclError, KeyError) as e:

        try:
            for i in range(menu_bar.index("end") + 1):
                try:
                    if menu_bar.type(i) == "cascade":
                        submenu = menu_bar.nametowidget(menu_bar.entrycget(i, "menu"))
                        if submenu == _araclar_menu_ref:
                            menu_bar.entryconfigure(i, label=ceviri_fonk("Araçlar"))
                            break
                except tk.TclError:
                    continue
        except Exception as ex:
            _gui_logger.warning(f"Menü güncellenemedi: {e}, fallback de başarısız: {ex}")

ui_texts.guncelle = guncelle_with_menu

ui_texts.guncelle(i18n._)

root.title(_("GPT Destekli Otomatik .PO Çeviri v 3.0.3 - Muharrem DANIŞMAN"))

status_var.set(_("Hazır"))
cevrilen_label.config(text=_("✔ Çevrilen: ") + "0")
atlanan_label.config(text=_("⚠ Atlanan: ") + "0")
hata_label.config(text=_("❌ Hata: ") + "0")
api_key_var.set(cfg.get("api_key", ""))
model_var.set(cfg.get("model", ""))
yon_var.set(cfg.get("yon", ""))
kaydet_var.set(cfg.get("auto_save", False))

root.after(100, ui_poller)
root.mainloop()
