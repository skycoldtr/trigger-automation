@echo off
chcp 65001 > nul
title GitHub Kolay Dosya Yukleme Araci

:: Komut dosyasinin calistigi klasöre odaklan (System32 hatasini önler)
cd /d "%~dp0"

echo ========================================================
echo         GITHUP DOSYA YUKLEME OTOMASYONU
echo ========================================================
echo.

:: Git kontrolü
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Sisteminizde Git yuklu degil veya PATH e eklenmemis!
    goto HATA_CIKIS
)

:: Git reposu kontrolü
if not exist ".git" (
    echo [+] Bu klasorde bir Git reposu bulunamadi.
    set /p "repo_url=Repo linkini yapistirin (Orn: https://github.com/kullanici/repo.git): "
    
    git init
    git remote add origin %repo_url%
    if %errorlevel% neq 0 (
        echo [HATA] Repo eklenirken bir sorun olustu!
        goto HATA_CIKIS
    )
    echo [+] Repo basariyla tanimlandi.
    echo.
) else (
    echo [+] Mevcut Git reposu algilandi.
)

echo.
echo --------------------------------------------------------
echo YUKLEME SECENEKLERI:
echo [1] Tek bir dosya yuklemek istiyorum
echo [2] Toplu dosya / Tum klasoru yuklemek istiyorum
echo --------------------------------------------------------
set /p "secim=Seciminiz (1 veya 2): "

if "%secim%"=="1" (
    echo.
    set /p "dosya_adi=Yuklenecek dosyanin tam adini ve uzantisini yazin (Orn: index.html): "
    if not exist "%dosya_adi%" (
        echo [HATA] '%dosya_adi%' adinda bir dosya bulunamadi!
        goto HATA_CIKIS
    )
    git add "%dosya_adi%"
) else if "%secim%"=="2" (
    echo.
    echo [+] Tum dosya ve klasorler ekleniyor...
    git add .
) else (
    echo [HATA] Gecersiz secim yaptiniz!
    goto HATA_CIKIS
)

echo.
echo --------------------------------------------------------
echo AYNI DOSYA KONTROLU:
echo Sunucuda ayni isimde dosya varsa uzerine yazilsin/degistirilsin mi?
echo [1] Evet, degistirsin (Guncelle)
echo [2] Hayir, iptal et / Guvenli mod
echo --------------------------------------------------------
set /p "conflict_secim=Seciminiz (1 veya 2): "

if "%conflict_secim%"=="2" (
    echo [!] Islem kullanici tarafindan iptal edildi.
    git reset
    goto HATA_CIKIS
)

echo.
set /p "commit_mesaji=Commit (guncelleme) mesaji girin (Orn: Dosyalar guncellendi): "
if "%commit_mesaji%"=="" set "commit_mesaji=Otomatik dosya guncellemesi"

echo.
echo [+] Degisiklikler kaydediliyor...
git commit -m "%commit_mesaji%" >nul 2>&1

echo.
echo [+] Dosyalar GitHub a gonderiliyor...
set /p "branch=Hangi branch e gondereceksiniz? (Genelde main veya master yazilir): "
if "%branch%"=="" set "branch=main"

:: Ilk defa yuklemede hata vermemesi icin branch'i zorla olusturup gonderiyoruz
git branch -M %branch%
git push -u origin %branch% --force

if %errorlevel% eq 0 (
    echo.
    echo ========================================================
    echo    ISLEM BASARILI! Dosyalar GitHub a yuklendi.
    echo ========================================================
    goto BITIR
) else (
    echo.
    echo [HATA] Dosyalar gonderilirken bir hata olustu.
    goto HATA_CIKIS
)

:HATA_CIKIS
echo.
echo [!] Islem basarisiz oldu veya durduruldu.
pause
exit

:BITIR
pause