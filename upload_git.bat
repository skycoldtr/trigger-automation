@echo off
chcp 65001 > nul
title GitHub Otomasyon - Akilli Yukleme
cd /d "%~dp0"

echo ========================================================
echo         GITHUP DOSYA YUKLEME OTOMASYONU (V2)
echo ========================================================
echo.

:: 1. Git Başlatma (Yoksa)
if not exist ".git" (
    echo [+] Git reposu bulunamadi, kuruluyor...
    git init
    set /p "repo_url=Repo linkini yapistirin: "
    git remote add origin %repo_url%
)

:: 2. Dosya Seçimi
echo.
echo --------------------------------------------------------
echo [1] Tek dosya yukle
echo [2] Tum klasoru yukle
echo --------------------------------------------------------
set /p "secim=Seciminiz: "

if "%secim%"=="1" (
    set /p "f_name=Dosya adi: "
    git add "%f_name%"
) else (
    git add .
)

:: 3. Commit Kontrolü ve Branch Sabitleme
:: Burada "Hata vermesin diye" önce bir commit atıyoruz.
echo [+] Commit hazirlaniyor...
git commit -m "Otomatik yukleme: %date% %time%" 2>nul

:: Branch ismini main yap ve pushla
echo [+] Branch 'main' olarak ayarlanip gonderiliyor...
git branch -M main
git push -u origin main --force

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo      ISLEM BASARILI! Dosyalar GitHub'a ulasti.
    echo ========================================================
) else (
    echo.
    echo [!] HATA: Push islemi basarisiz. 
    echo - Repo linkini dogru yazdigindan emin ol.
    echo - GitHub'a giris yapmamis olabilirsin (tarayiciyi kontrol et).
)

pause