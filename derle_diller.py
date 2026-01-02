#!/usr/bin/env python3

import os
import subprocess
import sys

DILLER_KLASORU = "diller"
DILLER = ["tr_TR", "en_US"]

for dil in DILLER:
    po_yolu = os.path.join(DILLER_KLASORU, dil, "LC_MESSAGES", "app.po")
    mo_yolu = os.path.join(DILLER_KLASORU, dil, "LC_MESSAGES", "app.mo")
    
    if os.path.exists(po_yolu):
        try:
            subprocess.run(["msgfmt", "-o", mo_yolu, po_yolu], check=True)
            print(f"✅ {dil} derlendi: {mo_yolu}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                import polib
                po = polib.pofile(po_yolu)
                po.save_as_mofile(mo_yolu)
                print(f"✅ {dil} derlendi (polib): {mo_yolu}")
            except Exception as e:
                print(f"❌ {dil} derlenirken hata: {e}")
    else:
        print(f"⚠️ {po_yolu} bulunamadı")
