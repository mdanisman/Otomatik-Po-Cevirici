import tkinter as tk

class UITextRegistry:
    def __init__(self):
        self._widgets = []
    
    def kaydet(self, widget, metin_anahtari, ozellik="text"):
        self._widgets.append((widget, metin_anahtari, ozellik))
    
    def guncelle(self, ceviri_fonk):
        for widget, anahtar, ozellik in self._widgets:
            try:
                widget.configure(**{ozellik: ceviri_fonk(anahtar)})
            except (AttributeError, tk.TclError):

                pass

ui_texts = UITextRegistry()
