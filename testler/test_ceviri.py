import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ceviri import (
    _cevirilmez_mi,
    _yer_tutucular_uyumlu,
    _ceviri_gecerli,
    _yer_tutucular_cikar
)


class TestCevirilmezMetin(unittest.TestCase):
    
    def test_url_algilandi(self):
        self.assertTrue(_cevirilmez_mi("https://example.com"))
        self.assertTrue(_cevirilmez_mi("http://test.org"))
        
    def test_email_algilandi(self):
        self.assertTrue(_cevirilmez_mi("test@example.com"))
        
    def test_hex_renk_algilandi(self):
        self.assertTrue(_cevirilmez_mi("#FF5733"))
        self.assertTrue(_cevirilmez_mi("#FFF"))
        
    def test_versiyon_algilandi(self):
        self.assertTrue(_cevirilmez_mi("v2.1.8"))
        self.assertTrue(_cevirilmez_mi("1.0.0"))
        
    def test_yol_algilandi(self):
        self.assertTrue(_cevirilmez_mi("/usr/local/bin"))
        self.assertTrue(_cevirilmez_mi("C:\\Windows\\System32"))
        
    def test_normal_metin_algilanmadi(self):
        self.assertFalse(_cevirilmez_mi("Hello world"))
        self.assertFalse(_cevirilmez_mi("Merhaba dünya"))


class TestYerTutucular(unittest.TestCase):
    
    def test_yer_tutucular_cikar(self):
        metin = "Hello %s, you have %d messages"
        yer_tutucular = _yer_tutucular_cikar(metin)
        self.assertEqual(yer_tutucular, {"%s", "%d"})
        
    def test_yer_tutucu_uyumlulugu(self):
        self.assertTrue(_yer_tutucular_uyumlu(
            "Hello %s",
            "Merhaba %s"
        ))
        self.assertFalse(_yer_tutucular_uyumlu(
            "Hello %s",
            "Merhaba %d"
        ))
        self.assertFalse(_yer_tutucular_uyumlu(
            "Hello %s",
            "Merhaba"
        ))
        
    def test_html_etiketleri_korundu(self):
        metin = "Click <b>here</b> to continue"
        yer_tutucular = _yer_tutucular_cikar(metin)
        self.assertIn("<b>", yer_tutucular)
        self.assertIn("</b>", yer_tutucular)


class TestModelCikti(unittest.TestCase):
    
    def test_gecerli_cikti(self):
        self.assertTrue(_ceviri_gecerli(
            "Save file",
            "Dosyayı kaydet"
        ))
        
    def test_bos_cikti_gecersiz(self):
        self.assertFalse(_ceviri_gecerli("Save file", ""))
        
    def test_ayni_cikti_gecersiz(self):
        self.assertFalse(_ceviri_gecerli("Save", "Save"))
        
    def test_cok_uzun_cikti_gecersiz(self):
        self.assertFalse(_ceviri_gecerli(
            "Save",
            "A" * 100  # 3x'ten uzun
        ))
        
    def test_kotu_desenler_algilandi(self):
        self.assertFalse(_ceviri_gecerli(
            "Save",
            "Translation: Kaydet"
        ))
        self.assertFalse(_ceviri_gecerli(
            "Save",
            "Here is the translated text: Kaydet"
        ))


if __name__ == '__main__':
    unittest.main()
