import gettext
import os

DILLER_KLASORU = "diller"
DOMAIN = "app"

class I18N:
    def __init__(self, varsayilan_dil="tr_TR"):
        self.aktif_dil = varsayilan_dil
        self._ = lambda s: s
        self.yukle(varsayilan_dil)
    
    def yukle(self, dil_kodu: str):
        try:
            trans = gettext.translation(
                DOMAIN,
                localedir=DILLER_KLASORU,
                languages=[dil_kodu],
                fallback=True
            )
            trans.install()
            self._ = trans.gettext
            self.aktif_dil = dil_kodu
        except (FileNotFoundError, OSError):
            self._ = lambda s: s

i18n = I18N()
