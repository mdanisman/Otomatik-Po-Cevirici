@echo off
title Otomatik PO Cevirici - Kurulum ve Calistirma

echo ==========================================
echo  Otomatik PO Cevirici - Kurulum Basliyor
echo ==========================================
echo.

:: Python kontrol
python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi.
    echo Lutfen Python 3.9+ yukleyin:
    echo https://www.python.org/downloads/
    pause
    exit
)

:: Sanal ortam yoksa olustur
if not exist venv (
    echo [1/4] Sanal ortam olusturuluyor...
    python -m venv venv
)

:: Sanal ortami aktif et
echo [2/4] Sanal ortam aktif ediliyor...
call venv\Scripts\activate

:: Pip guncelle
echo [3/4] Pip guncelleniyor...
python -m pip install --upgrade pip

:: Gereksinimler
if exist requirements.txt (
    echo [4/4] requirements.txt yukleniyor...
    pip install -r requirements.txt
) else (
    echo [UYARI] requirements.txt bulunamadi!
)

echo.
echo Kurulum tamamlandi.
echo Program baslatiliyor...
echo.

python ceviri_gui.py
pause
