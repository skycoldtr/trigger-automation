@echo off
REM ============================================
REM  TRIGGER - Windows .exe build script
REM  Bu dosyayi trigger.py, icon.png, icon.ico
REM  ile AYNI klasore koyup cift tikla.
REM ============================================

echo [1/3] Gerekli paketler kuruluyor...
pip install -r requirements.txt

echo.
echo [2/3] .exe derleniyor (PyInstaller)...
pyinstaller --onefile --noconsole --clean ^
    --name "TRIGGER" ^
    --icon "icon.ico" ^
    --add-data "icon.png;." ^
    --add-data "icon.ico;." ^
    trigger.py

echo.
echo [3/3] Tamamlandi! .exe dosyan: dist\TRIGGER.exe
echo.
pause
