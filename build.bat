@echo off
setlocal EnableDelayedExpansion
title TRIGGER Build

REM ============================================
REM  TRIGGER - Windows .exe build script
REM  Bu dosyayi trigger.py, icon.png, icon.ico,
REM  requirements.txt, errors-code.txt ile AYNI
REM  klasore koyup CIFT TIKLA.
REM  (Yonetici olarak calistirmana gerek yok.)
REM ============================================

REM Windows bu dosyayi "Yonetici olarak calistir" ile actiginda
REM varsayilan calisma dizinini C:\Windows\system32 yapiyor. Bu satir
REM ne olursa olsun bu .bat dosyasinin GERCEKTEN bulundugu klasore
REM geciyor, boylece requirements.txt / trigger.py her zaman bulunur.
cd /d "%~dp0"

REM --- TRIGGER renk paleti ile ANSI true-color kodlari (accent turuncu) ---
for /F %%E in ('echo prompt $E ^| cmd') do set "ESC=%%E"
set "ACCENT=%ESC%[38;2;255;87;34m"
set "MUTED=%ESC%[38;2;136;136;136m"
set "GREEN=%ESC%[38;2;76;175;80m"
set "RED=%ESC%[38;2;207;102;121m"
set "BOLD=%ESC%[1m"
set "RESET=%ESC%[0m"

echo %ACCENT%%BOLD%
echo   =====================================
echo    TRIGGER // Automation Engine - Build
echo   =====================================
echo %RESET%
echo %MUTED%Calisma klasoru: %cd%%RESET%
echo.

if not exist "trigger.py" (
    echo %RED%[TRG-BUILD-01] trigger.py bu klasorde bulunamadi: %cd%%RESET%
    echo %MUTED%trigger.py, icon.png, icon.ico, requirements.txt dosyalarinin
    echo build.bat ile AYNI klasorde oldugundan emin ol.%RESET%
    echo.
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo %RED%[TRG-BUILD-02] requirements.txt bu klasorde bulunamadi: %cd%%RESET%
    pause
    exit /b 1
)

if not exist "splash_native.png" (
    echo %RED%[TRG-BUILD-05] splash_native.png bu klasorde bulunamadi: %cd%%RESET%
    pause
    exit /b 1
)

echo %ACCENT%%BOLD%[1/3]%RESET% %ACCENT%Gerekli paketler kuruluyor...%RESET%
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo %RED%[TRG-BUILD-03] pip install basarisiz oldu. Yukaridaki hatayi kontrol et.%RESET%
    pause
    exit /b 1
)

echo.
echo %ACCENT%%BOLD%[2/3]%RESET% %ACCENT%.exe derleniyor (PyInstaller)...%RESET%
pyinstaller --onefile --noconsole --clean ^
    --name "TRIGGER" ^
    --icon "icon.ico" ^
    --splash "splash_native.png" ^
    --add-data "icon.png;." ^
    --add-data "icon.ico;." ^
    --add-data "errors-code.txt;." ^
    trigger.py
if errorlevel 1 (
    echo.
    echo %RED%[TRG-BUILD-04] PyInstaller derlemesi basarisiz oldu. Yukaridaki hatayi kontrol et.%RESET%
    pause
    exit /b 1
)

echo.
if exist "dist\TRIGGER.exe" (
    echo %GREEN%%BOLD%[3/3] Tamamlandi!%RESET% %GREEN%.exe dosyan: %cd%\dist\TRIGGER.exe%RESET%
) else (
    echo %RED%[UYARI] Derleme bitti ama dist\TRIGGER.exe bulunamadi, yukarida hata olabilir.%RESET%
)
echo.
pause
