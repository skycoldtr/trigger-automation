TRIGGER - .exe DERLEME REHBERI
================================

1) Bu klasordeki tum dosyalari (trigger.py, icon.png, icon.ico,
   requirements.txt, build.bat) TEK bir klasore koy.

2) Windows'ta Python 3.10+ kurulu olmali (pip de gelir).

3) build.bat dosyasina CIFT TIKLA. Otomatik olarak:
   - requirements.txt'teki paketleri kurar (pyautogui, keyboard,
     Pillow, tkinterdnd2, pyinstaller)
   - PyInstaller ile tek dosyalik, konsolsuz (--noconsole),
     ikonlu bir .exe uretir
   - icon.png ve icon.ico'yu exe'nin icine gomer (--add-data),
     trigger.py zaten bunlari calisirken otomatik bulacak
     sekilde yazildi (sys._MEIPASS destegi mevcut)

4) Bittiginde exe'yi dist\TRIGGER.exe altinda bulursun.
   Bu TEK dosyayi istedigin yere tasiyip calistirabilirsin,
   Python kurulu olmasi gerekmez.

NOT: "keyboard" kutuphanesi Windows'ta global tus dinleme icin
genelde YONETICI (Administrator) yetkisi ister. exe'yi "Yonetici
olarak calistir" ile acmayi dene, aksi halde Q tusu ile iptal
ozelligi calismayabilir.

ANTIVIRUS UYARISI:
PyInstaller ile derlenmis, imzasiz (unsigned) exe'ler; ozellikle
klavye/mouse otomasyonu yapanlar, Windows Defender / SmartScreen
tarafindan yanlis pozitif (false positive) olarak isaretlenebilir.
Bu normal bir durumdur, kod imzalama sertifikasi olmadan tamamen
onlenemez.
