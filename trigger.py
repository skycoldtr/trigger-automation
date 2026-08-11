import os
import sys
import json
import time
import uuid
import traceback
import threading
import tkinter as tk
from tkinter import ttk, filedialog

# ---------- dependency guard (TRG-001) ----------
# If a hard-required package is missing, fail fast with a plain (unstyled,
# since no app/theme exists yet) but clear message instead of a raw traceback.
_MISSING_DEPS = []
try:
    from PIL import Image, ImageTk
except ImportError:
    _MISSING_DEPS.append("Pillow")
try:
    import pyautogui
except ImportError:
    _MISSING_DEPS.append("pyautogui")
try:
    import keyboard
except ImportError:
    _MISSING_DEPS.append("keyboard")

if _MISSING_DEPS:
    from tkinter import messagebox as _mb
    _r = tk.Tk()
    _r.withdraw()
    _mb.showerror(
        "TRG-001 — Missing dependency",
        "TRIGGER can't start because the following required package(s) are missing:\n\n"
        + ", ".join(_MISSING_DEPS)
        + "\n\nFix: run  pip install -r requirements.txt\n\nSee errors-code.txt (code TRG-001) for details."
    )
    sys.exit(1)

# OpenCV is optional but required by PyAutoGUI for confidence-based (fuzzy) image
# matching. Without it, matching silently fails on every attempt — this is the
# single most common reason the app appears to "not click anything".
# NOTE: opencv-python is a genuinely heavy import (can take 1-2+ seconds), and
# importing it here at module load time would delay the splash screen from
# appearing at all — the app would look frozen before you even see it start.
# So this check is deferred (lazy) until the moment it's actually needed
# (when Start is pressed), via _ensure_cv2_checked() below.
_cv2_checked = False
_has_cv2 = False


def _ensure_cv2_checked():
    global _cv2_checked, _has_cv2
    if not _cv2_checked:
        try:
            import cv2  # noqa: F401
            _has_cv2 = True
        except ImportError:
            _has_cv2 = False
        _cv2_checked = True
    return _has_cv2

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

pyautogui.PAUSE = 0.15
pyautogui.FAILSAFE = True

APP_VERSION = "4.6"

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif")

ERROR_CODES = {
    "TRG-001": {
        "EN": ("Missing required library", "Run: pip install -r requirements.txt"),
        "TR": ("Gerekli kütüphane eksik", "Şunu çalıştır: pip install -r requirements.txt"),
    },
    "TRG-002": {
        "EN": ("OpenCV not installed — matching may never find a click target",
               "Run: pip install opencv-python  (or continue with exact pixel matching, less reliable)"),
        "TR": ("OpenCV kurulu değil — eşleştirme hiçbir hedefi bulamayabilir",
               "Şunu çalıştır: pip install opencv-python  (ya da kesin piksel eşleşmesiyle devam et, daha az güvenilir)"),
    },
    "TRG-003": {
        "EN": ("Target image file not found", "Re-select the image for that step, or remove it from the queue."),
        "TR": ("Hedef görsel dosyası bulunamadı", "O adım için görseli yeniden seç, ya da listeden kaldır."),
    },
    "TRG-004": {
        "EN": ("Screen capture / click failed", "Check app permissions, monitor setup, and try again."),
        "TR": ("Ekran yakalama / tıklama başarısız oldu", "Uygulama izinlerini ve ekran ayarlarını kontrol edip tekrar dene."),
    },
    "TRG-005": {
        "EN": ("Global 'Q' abort hotkey unavailable", "Re-run the app as Administrator."),
        "TR": ("Genel 'Q' iptal tuşu çalışmıyor", "Uygulamayı Yönetici olarak yeniden çalıştır."),
    },
    "TRG-006": {
        "EN": ("Settings file was corrupted and reset", "No action needed — your preferences were reset to default."),
        "TR": ("Ayarlar dosyası bozuktu ve sıfırlandı", "Bir şey yapmana gerek yok — tercihlerin varsayılana döndü."),
    },
    "TRG-007": {
        "EN": ("Could not save settings to disk", "Check available disk space and folder permissions."),
        "TR": ("Ayarlar diske kaydedilemedi", "Disk alanını ve klasör izinlerini kontrol et."),
    },
    "TRG-999": {
        "EN": ("Unexpected error", "See details below. Please report this if it keeps happening."),
        "TR": ("Beklenmeyen hata", "Aşağıdaki ayrıntıya bak. Tekrarlarsa lütfen bildir."),
    },
}

UNIT_ALIASES = {
    "ms": "ms", "milisaniye": "ms",
    "sec": "sec", "saniye": "sec", "sn": "sec",
    "min": "min", "dakika": "min", "dk": "min",
}

ACCENT_PRESETS = {
    "orange": ("#FF5722", "#E64A19"),
    "blue":   ("#2196F3", "#1769AA"),
    "green":  ("#4CAF50", "#357A38"),
    "purple": ("#9C27B0", "#6D1B7B"),
    "red":    ("#E53935", "#AB2A26"),
    "teal":   ("#00BCD4", "#00838F"),
    "pink":   ("#EC407A", "#AD1457"),
    "yellow": ("#FBC02D", "#B8860B"),
}

SPLASH_MESSAGES = {
    "TR": ["Modüller yükleniyor...", "Arayüz hazırlanıyor...", "Son kontroller yapılıyor..."],
    "EN": ["Loading modules...", "Preparing interface...", "Running final checks..."],
}


def canon_unit(u):
    return UNIT_ALIASES.get(str(u).strip().lower(), "sec")


def rounded_polygon_points(x1, y1, x2, y2, r):
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1, x1 + r, y1
    ]


def _lerp_color(c1, c2, t):
    """Linearly interpolate between two '#RRGGBB' colors, t in [0,1]."""
    c1 = c1.lstrip("#")
    c2 = c2.lstrip("#")
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _ease_in_out(t):
    return t * t * (3 - 2 * t)


def _rounded_rect_img(w, h, radius, fill_hex, scale=4):
    """Renders a rounded rectangle as a real bitmap via PIL (supersampled for
    smooth edges). This is used instead of Canvas polygon smoothing, which
    can fail to render reliably on some Tk builds — a plain PhotoImage always
    renders, so buttons can never silently 'disappear'."""
    from PIL import ImageDraw
    W, H, R = w * scale, h * scale, radius * scale
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fh = fill_hex.lstrip("#")
    rgb = tuple(int(fh[i:i + 2], 16) for i in (0, 2, 4))
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=R, fill=rgb + (255,))
    return img.resize((w, h), Image.LANCZOS)


class ImageButton(tk.Label):
    """A modern rounded/pill-shaped button rendered as a real PIL bitmap
    (not a Canvas polygon), with a smooth animated color fade on hover and
    a brief press effect. Renders reliably across Tk/Windows versions."""

    STEPS = 8

    def __init__(self, parent, text, command, colors, font, width=180, height=44, radius=None):
        try:
            parent_bg = parent.cget("bg")
        except tk.TclError:
            parent_bg = "#121212"
        self.w, self.h = width, height
        self.r = radius if radius is not None else height // 2
        super().__init__(parent, text=text, font=font, compound="center",
                          bd=0, bg=parent_bg, cursor="hand2")
        self.command = command
        self.colors = colors
        self.enabled = True
        self._anim_job = None

        self._frames = [
            ImageTk.PhotoImage(_rounded_rect_img(
                self.w, self.h, self.r, _lerp_color(colors["bg"], colors["hover"], i / (self.STEPS - 1))
            )) for i in range(self.STEPS)
        ]
        self._pressed_frame = ImageTk.PhotoImage(_rounded_rect_img(self.w, self.h, self.r, colors["hover"]))
        self._disabled_frame = ImageTk.PhotoImage(_rounded_rect_img(self.w, self.h, self.r, colors["disabled_bg"]))

        self.config(image=self._frames[0], fg=colors["fg"])
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", lambda e: self._animate(True))
        self.bind("<Leave>", lambda e: self._animate(False))

    def _animate(self, hover_in):
        if not self.enabled:
            return
        if self._anim_job:
            try:
                self.after_cancel(self._anim_job)
            except Exception:
                pass
        seq = list(range(self.STEPS)) if hover_in else list(range(self.STEPS - 1, -1, -1))

        def step(i=0):
            if not self.winfo_exists() or i >= len(seq):
                self._anim_job = None
                return
            self.config(image=self._frames[seq[i]])
            self._anim_job = self.after(14, lambda: step(i + 1))

        step()

    def _on_press(self, event):
        if self.enabled:
            self.config(image=self._pressed_frame)

    def _on_release(self, event):
        if not self.enabled:
            return
        self.config(image=self._frames[self.STEPS - 1])
        inside = 0 <= event.x <= self.w and 0 <= event.y <= self.h
        if inside and self.command:
            self.command()

    def set_text(self, text):
        self.config(text=text)

    def set_enabled(self, enabled):
        self.enabled = enabled
        if enabled:
            self.config(image=self._frames[0], fg=self.colors["fg"], cursor="hand2")
        else:
            self.config(image=self._disabled_frame, fg=self.colors["disabled_fg"], cursor="arrow")


class PillButton(tk.Canvas):
    """A modern rounded/pill-shaped button drawn on a Canvas — animated hover
    color transitions, a brief press effect, and a subtle outline so it never
    reads as 'missing' even in muted/disabled states."""

    def __init__(self, parent, text, command, colors, font, width=180, height=44, radius=None):
        try:
            parent_bg = parent.cget("bg")
        except tk.TclError:
            parent_bg = "#121212"
        super().__init__(parent, width=width, height=height, bg=parent_bg,
                          highlightthickness=0, bd=0, cursor="hand2")
        self.command = command
        self.colors = colors
        self.text = text
        self.font = font
        self.w, self.h = width, height
        self.r = radius if radius is not None else height // 2
        self.enabled = True
        self._hover_t = 0.0
        self._press_t = 0.0
        self._anim_job = None
        self._redraw()
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", lambda e: self._animate_hover(True))
        self.bind("<Leave>", lambda e: self._animate_hover(False))

    def _animate_hover(self, entering):
        if not self.enabled:
            return
        target = 1.0 if entering else 0.0
        self._run_anim("_hover_t", target, 110)

    def _run_anim(self, attr, target, duration_ms, steps=9):
        if self._anim_job:
            try:
                self.after_cancel(self._anim_job)
            except Exception:
                pass
        start = getattr(self, attr)
        delta = target - start

        def step(i=0):
            if not self.winfo_exists():
                return
            frac = _ease_in_out(i / steps)
            setattr(self, attr, start + delta * frac)
            self._redraw()
            if i < steps:
                self._anim_job = self.after(max(duration_ms // steps, 8), lambda: step(i + 1))
            else:
                setattr(self, attr, target)
                self._anim_job = None
                self._redraw()

        step()

    def _on_press(self, event):
        if not self.enabled:
            return
        self._run_anim("_press_t", 1.0, 70, steps=4)

    def _on_release(self, event):
        if not self.enabled:
            return
        self._run_anim("_press_t", 0.0, 120, steps=6)
        inside = 0 <= event.x <= self.w and 0 <= event.y <= self.h
        if inside and self.command:
            self.command()

    def _redraw(self):
        self.delete("all")
        if not self.enabled:
            bg, fg, outline = self.colors["disabled_bg"], self.colors["disabled_fg"], self.colors.get("outline_disabled", "")
        else:
            bg = _lerp_color(self.colors["bg"], self.colors["hover"], self._hover_t)
            fg = self.colors["fg"]
            outline = self.colors.get("outline", "")

        inset = self._press_t * 2.0
        pts = rounded_polygon_points(1 + inset, 1 + inset, self.w - 1 - inset, self.h - 1 - inset,
                                      max(self.r - inset, 2))
        self.create_polygon(pts, smooth=True, fill=bg, outline=outline, width=1)
        text_fill = fg
        self.create_text(self.w // 2, self.h // 2, text=self.text, fill=text_fill, font=self.font)

    def set_text(self, text):
        self.text = text
        self._redraw()

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.config(cursor="hand2" if enabled else "arrow")
        self._redraw()


CHANGELOG = {
    "4.6": {
        "EN": [
            "🔁 Each step can now click multiple times (1 to 999, your choice) instead of just once",
            "🎯 New 'Select Area' tool: drag a box on screen to restrict where a step searches — this is the fix for clicking the wrong lookalike file/icon when two similar targets are visible at once",
            "📋 The queue list now shows click count and marks steps that have a search area set",
        ],
        "TR": [
            "🔁 Her adım artık sadece bir kez değil, istediğin kadar (1'den 999'a) tıklayabiliyor",
            "🎯 Yeni 'Bölge Seç' aracı: ekranda bir alan sürükleyerek adımın sadece o bölgede aramasını sağla — iki benzer görünümlü dosya/ikon aynı anda ekrandayken yanlışının tıklanması sorununun çözümü bu",
            "📋 Liste artık tıklama sayısını gösteriyor ve bir arama bölgesi ayarlanmış adımları işaretliyor",
        ],
    },
    "4.5": {
        "EN": [
            "🐛 Fixed automation never clicking anything for images with Turkish characters (ç, ı, ğ, ş, ö, ü) in their file name or path — a real OpenCV limitation on Windows. Target images are now loaded through Pillow instead, which handles these paths correctly",
            "⚡ Target images are now pre-loaded once when you hit Start instead of being re-read from disk every 0.2 seconds — faster and more reliable matching",
        ],
        "TR": [
            "🐛 Dosya adında veya yolunda Türkçe karakter (ç, ı, ğ, ş, ö, ü) olan görsellerde otomasyonun hiç tıklamaması sorunu düzeltildi — bu, Windows'ta gerçek bir OpenCV kısıtlamasıydı. Hedef görseller artık bu tür yolları doğru okuyan Pillow üzerinden yükleniyor",
            "⚡ Hedef görseller artık Başlat'a bastığında bir kez önceden yükleniyor, her 0.2 saniyede diskten tekrar okunmuyor — daha hızlı ve güvenilir eşleştirme",
        ],
    },
    "4.4": {
        "EN": [
            "🐛 Found the ACTUAL cause of 'Start/Pause/Cancel buttons are missing': the queue list was laid out before the bottom action bar, so it always claimed all remaining space first — regardless of window size. The action bar now reserves its space first, so it can never be pushed off-screen again",
            "⚡ OpenCV is no longer imported at startup at all — it's now loaded only the first time you press Start, so the splash screen appears immediately instead of waiting on a slow background import",
            "🎬 Added a native PyInstaller splash image (shown while the .exe unpacks itself, before Python even starts) so there's no more blank moment before our own splash takes over",
        ],
        "TR": [
            "🐛 'Başlat/Duraklat/İptal butonları yok' şikayetinin GERÇEK sebebi bulundu: işlem listesi, alt eylem çubuğundan önce yerleştiriliyordu, bu yüzden pencere boyutu ne olursa olsun kalan tüm alanı o kapıyordu. Artık eylem çubuğu yerini önce garantiliyor, bir daha ekranın dışına itilemez",
            "⚡ OpenCV artık açılışta hiç yüklenmiyor — sadece ilk kez Başlat'a bastığında yükleniyor, böylece splash ekranı yavaş bir arka plan yüklemesini beklemeden hemen beliriyor",
            "🎬 .exe kendini paketten çıkarırken (Python daha başlamadan önce) görünen native bir PyInstaller açılış görseli eklendi — artık kendi splash ekranımız devreye girene kadar boş bir an kalmıyor",
        ],
    },
    "4.3": {
        "EN": [
            "🐛 Fixed the real cause of 'Start/Pause/Cancel buttons are missing': the fixed 1000×920 window could be taller than smaller/laptop screens, pushing the bottom action bar off-screen. The window now sizes itself to fit your actual screen",
            "⚡ The splash screen now appears sooner — icon/logo file loading was moved to happen in the background instead of blocking it",
        ],
        "TR": [
            "🐛 'Başlat/Duraklat/İptal butonları yok' şikayetinin gerçek nedeni bulundu: sabit 1000×920 pencere, küçük/laptop ekranlarından daha uzun kalıp alt eylem çubuğunu ekranın dışına itiyordu. Pencere artık gerçek ekran boyutuna göre kendini ayarlıyor",
            "⚡ Açılış ekranı artık daha hızlı beliriyor — ikon/logo dosyası yükleme işlemi onu bloklamak yerine arka planda yapılıyor",
        ],
    },
    "4.2": {
        "EN": [
            "🐛 Rebuilt the Start/Pause/Cancel/Add buttons on a more reliable rendering engine — the previous version could fail to draw on some Windows/Tk setups, making them look 'missing'",
            "✨ Buttons now have a real smooth animated color fade on hover instead of an instant flat swap",
            "🎬 Splash screen loading indicator is back to a left-to-right sweeping line (looping 3 times), replacing the spinning ring",
            "🪟 Popup windows (warnings, changelog, terms) are now positioned relative to the app window and can be dragged by their title area",
            "🌫️ Smoothed out the theme/language/UI-mode transition — the window now dims instead of flashing fully transparent",
            "📋 You can now paste an image straight from the clipboard (Ctrl+V or the Paste button) instead of only Browse/drag & drop",
            "🎨 build.bat now prints colored, on-brand status messages instead of plain text",
        ],
        "TR": [
            "🐛 Başlat/Duraklat/İptal/Ekle butonları daha güvenilir bir render motoruna taşındı — önceki sürüm bazı Windows/Tk kurulumlarında hiç çizilmeyip 'kayıp' gibi görünebiliyordu",
            "✨ Butonlarda artık anlık renk değişimi yerine gerçek, akıcı bir hover geçiş animasyonu var",
            "🎬 Açılış ekranındaki yükleme göstergesi, dönen halka yerine soldan sağa akan (3 tur) çizgiye geri döndü",
            "🪟 Açılır pencereler (uyarı, yenilikler, kullanım şartları) artık ana pencereye göre konumlanıyor ve başlık kısmından sürüklenebiliyor",
            "🌫️ Tema/dil/arayüz geçişi yumuşatıldı — pencere artık tamamen saydamlaşıp masaüstünü göstermek yerine sadece hafifçe kararıyor",
            "📋 Artık panodaki bir görseli doğrudan yapıştırabiliyorsun (Ctrl+V ya da Yapıştır butonu), sadece Gözat/sürükle-bırak değil",
            "🎨 build.bat artık düz metin yerine markaya uygun renkli durum mesajları basıyor",
        ],
    },
    "4.1": {
        "EN": [
            "🐛 Found & fixed the real cause of 'adds fine but never clicks': OpenCV was missing, which silently broke all fuzzy image matching",
            "🧩 Added a full error code system (TRG-001…TRG-999) — see errors-code.txt. Any failure now shows a specific, explainable code instead of just doing nothing",
            "🛟 Missing target files, permission issues, and hotkey problems are now detected and explained instead of silently ignored",
        ],
        "TR": [
            "🐛 'Ekliyorum ama hiç tıklamıyor' şikayetinin asıl sebebi bulundu ve düzeltildi: OpenCV eksikti, bu da tüm yaklaşık görsel eşleştirmeyi sessizce bozuyordu",
            "🧩 Tam bir hata kodu sistemi eklendi (TRG-001…TRG-999) — bkz. errors-code.txt. Artık her hata 'hiçbir şey olmuyor' yerine açıklanabilir, spesifik bir kodla gösteriliyor",
            "🛟 Eksik hedef dosyalar, izin sorunları ve tuş kısayolu problemleri artık sessizce yutulmuyor, tespit edilip açıklanıyor",
        ],
    },
    "4.0": {
        "EN": [
            "🖼️ The queue now shows a small thumbnail preview of each step's target image",
            "✨ Smooth fade transitions when switching theme, language or UI mode",
            "📜 The terms of use screen now truly appears only once, on first launch",
            "🛡️ Unexpected errors no longer fail silently — they now show a clear message instead of the app just 'not responding'",
            "🎬 Redesigned splash screen: a spinning loader (3 full loops) with rotating status messages",
            "🎨 You can now pick your own accent color, independent of dark/light theme",
            "🧩 All warning/confirm/rename popups were rebuilt with our own modern look — no more plain Windows dialogs",
            "🔘 Core buttons (Add/Update, Start/Pause/Cancel) were redesigned as modern pill-shaped buttons",
        ],
        "TR": [
            "🖼️ Liste artık her adımın hedef görselinin küçük bir önizlemesini gösteriyor",
            "✨ Tema, dil ve arayüz modu değiştirirken artık yumuşak bir geçiş (fade) efekti var",
            "📜 Kullanım şartları ekranı artık gerçekten sadece ilk açılışta bir kez çıkıyor",
            "🛡️ Beklenmeyen hatalar artık sessizce kaybolmuyor — 'hiçbir şey olmuyor' yerine anlaşılır bir hata penceresi çıkıyor",
            "🎬 Açılış ekranı yenilendi: 3 tur dönen bir yükleme animasyonu ve değişen durum mesajları eklendi",
            "🎨 Artık koyu/açık temadan bağımsız olarak kendi vurgu rengini seçebiliyorsun",
            "🧩 Tüm uyarı/onay/yeniden adlandırma pencereleri kendi modern tasarımımıza geçirildi — düz Windows kutucukları kalmadı",
            "🔘 Ana butonlar (Ekle/Güncelle, Başlat/Duraklat/İptal) modern, yuvarlak hatlı butonlarla yeniden tasarlandı",
        ],
    },
    "3.2": {
        "EN": [
            "🐛 Fixed the 'What's New' and 'Terms of Use' windows sometimes getting stuck with the button pushed off-screen",
            "📜 The terms of use screen now uses the app's own modern theme instead of a plain system popup",
            "📐 These dialog windows now always open at a size that fits their content, with scrolling if needed",
        ],
        "TR": [
            "🐛 'Yenilikler' ve 'Kullanım Şartları' pencerelerinin buton görünmeden takılı kalma sorunu düzeltildi",
            "📜 Kullanım şartları ekranı artık düz sistem penceresi değil, uygulamanın kendi modern temasıyla gösteriliyor",
            "📐 Bu pencereler artık her zaman içeriğe uygun boyutta açılıyor, gerekirse kaydırılabiliyor",
        ],
    },
    "3.0": {
        "EN": [
            "🐛 Fixed a silent bug where adding a step (via Browse or drag & drop) could fail with no warning",
            "✏️ Select any step in the queue to edit its confidence, delay, unit or name — then hit Update",
            "🖱️ Fixed the invisible black text cursor in the confidence/delay fields",
            "📐 Bigger default window so labels like 'Confidence' never get clipped again",
            "💾 Your queue is now auto-saved — closing the app no longer wipes your steps",
            "🗂️ Language, theme and UI mode preferences are now remembered between launches",
            "🎬 New animated splash screen on startup",
            "🎨 General UI polish: status badge, cleaner spacing, refined layout",
        ],
        "TR": [
            "🐛 Adım eklerken (Gözat veya sürükle-bırak ile) sessizce başarısız olma hatası düzeltildi",
            "✏️ Listede bir adımı seçip hassasiyet/süre/birim/isim değerlerini düzenleyip Güncelle diyebilirsin",
            "🖱️ Hassasiyet/süre kutucuklarındaki görünmez siyah imleç sorunu giderildi",
            "📐 Varsayılan pencere büyütüldü, 'Hassasiyet' gibi yazılar artık kesilmiyor",
            "💾 Sıra listen artık otomatik kaydediliyor — programı kapatsan bile kaybolmuyor",
            "🗂️ Dil, tema ve arayüz modu tercihlerin artık hatırlanıyor",
            "🎬 Açılışta yeni bir animasyonlu karşılama ekranı eklendi",
            "🎨 Genel arayüz cilası: durum rozeti, daha temiz boşluklar, düzenli yerleşim",
        ],
    },
}

LANGUAGES = {
    "EN": {
        "title": "TRIGGER // Automation Engine",
        "idle": "IDLE",
        "armed": "RUNNING",
        "status_paused": "PAUSED",
        "disarmed": "STOPPED",
        "abort": "ABORT KEY: [Q]",
        "config_box": " ⚙ STEP EDITOR ",
        "target_lbl": "🎯 Target:",
        "name_lbl": "🏷 Step Name:",
        "browse": "📂 Browse",
        "confidence": "🎚 Confidence:",
        "delay": "⏱ Delay:",
        "add_btn": "➕ ADD STEP",
        "update_btn": "💾 UPDATE STEP",
        "cancel_edit": "✖",
        "queue_box": " 📋 SEQUENCE QUEUE ",
        "col_status": "●",
        "col_name": "NAME",
        "col_target": "TARGET FILE",
        "col_conf": "CONF",
        "col_delay": "DELAY",
        "col_unit": "UNIT",
        "col_clicks": "CLICKS",
        "click_count_lbl": "🔁 Click Count:",
        "region_lbl": "🎯 Search Area:",
        "select_region": "🎯 Select Area",
        "clear_region": "✖ Clear",
        "region_whole_screen": "Whole screen",
        "region_hint": "Drag to select the area to search in · Esc to cancel",
        "enable_sel": "✅ Enable",
        "disable_sel": "⛔ Disable",
        "rename_sel": "✏️ Rename",
        "remove": "🗑️ Remove",
        "import": "📥 Import Profile",
        "export": "💾 Export Profile",
        "start": "▶ START",
        "pause": "⏸ PAUSE",
        "resume": "▶ RESUME",
        "cancel": "⏹ CANCEL",
        "warn_empty": "Queue is empty or no step is enabled.",
        "warn_no_image": "Please select or drop a target image first.",
        "warn_bad_number": "Confidence/Delay must be a valid number. Fixed automatically — please check the values.",
        "unit_sec": "sec",
        "unit_ms": "ms",
        "unit_min": "min",
        "drop_hint": "📥 Drag & drop an image\nor click to browse\n(Ctrl+V to paste)",
        "no_dnd_hint": "⚠ Install 'tkinterdnd2' to enable drag & drop",
        "paste_btn": "Paste",
        "warn_no_clipboard_image": "No image found on the clipboard. Copy an image (e.g. a screenshot) first, then try again.",
        "clipboard_default_name": "Clipboard Image",
        "no_file": "— no file selected —",
        "confirm_remove_title": "Confirm Removal",
        "confirm_remove_msg": "Remove {n} selected step(s)?",
        "rename_title": "Rename Step",
        "rename_prompt": "Enter a new name for this step:",
        "no_selection": "Select at least one step in the queue first.",
        "no_selection_single": "Select exactly one step to rename.",
        "toggle_ui": "🎨 Classic UI",
        "toggle_ui_modern": "🎨 Modern UI",
        "editing_hint": "✏️ Editing \"{name}\" — change values and hit Update, or ✖ to cancel.",
        "changelog_title": "🎉 What's New — v{version}",
        "changelog_close": "Awesome, let's go! 🚀",
        "accept_btn": "I Accept",
        "decline_btn": "Decline & Quit",
        "modal_ok": "OK",
        "modal_cancel": "Cancel",
        "warn_title": "Warning",
        "info_title": "Info",
        "error_title": "Something went wrong",
        "disclaimer_title": "Legal Disclaimer & Terms of Use",
        "disclaimer_msg": (
            "LEGAL DISCLAIMER AND TERMS OF USE:\n\n"
            "1. This software is created solely for automation and testing purposes.\n"
            "2. The user assumes ALL responsibility for any actions performed using this software.\n"
            "3. The developer cannot be held liable for any system failures, account bans, "
            "data losses, or damages resulting from the use or misuse of this application.\n\n"
            "Do you accept these terms and conditions?"
        )
    },
    "TR": {
        "title": "TRIGGER // Otomasyon Motoru",
        "idle": "BOŞTA",
        "armed": "ÇALIŞIYOR",
        "status_paused": "DURAKLATILDI",
        "disarmed": "DURDURULDU",
        "abort": "İPTAL TUŞU: [Q]",
        "config_box": " ⚙ ADIM DÜZENLEYİCİ ",
        "target_lbl": "🎯 Hedef:",
        "name_lbl": "🏷 Adım Adı:",
        "browse": "📂 Gözat",
        "confidence": "🎚 Hassasiyet:",
        "delay": "⏱ Bekleme:",
        "add_btn": "➕ ADIM EKLE",
        "update_btn": "💾 GÜNCELLE",
        "cancel_edit": "✖",
        "queue_box": " 📋 İŞLEM LİSTESİ ",
        "col_status": "●",
        "col_name": "İSİM",
        "col_target": "HEDEF DOSYA",
        "col_conf": "HASSASİYET",
        "col_delay": "SÜRE",
        "col_unit": "BİRİM",
        "col_clicks": "TIKLAMA",
        "click_count_lbl": "🔁 Tıklama Sayısı:",
        "region_lbl": "🎯 Arama Bölgesi:",
        "select_region": "🎯 Bölge Seç",
        "clear_region": "✖ Temizle",
        "region_whole_screen": "Tüm ekran",
        "region_hint": "Aranacak alanı sürükleyerek seç · İptal: Esc",
        "enable_sel": "✅ Aktif Et",
        "disable_sel": "⛔ Deaktif Et",
        "rename_sel": "✏️ Yeniden Adlandır",
        "remove": "🗑️ Kaldır",
        "import": "📥 Profil Yükle",
        "export": "💾 Profil Kaydet",
        "start": "▶ BAŞLAT",
        "pause": "⏸ DURAKLAT",
        "resume": "▶ DEVAM ET",
        "cancel": "⏹ İPTAL ET",
        "warn_empty": "Liste boş ya da hiçbir adım aktif değil.",
        "warn_no_image": "Lütfen önce bir hedef görsel seçin veya sürükleyin.",
        "warn_bad_number": "Hassasiyet/Süre geçerli bir sayı olmalı. Otomatik düzeltildi — değerleri kontrol et.",
        "unit_sec": "sn",
        "unit_ms": "ms",
        "unit_min": "dk",
        "drop_hint": "📥 Görseli sürükleyip bırak\nya da tıklayıp seç\n(Yapıştırmak için Ctrl+V)",
        "no_dnd_hint": "⚠ Sürükle-bırak için 'tkinterdnd2' kurun",
        "paste_btn": "Yapıştır",
        "warn_no_clipboard_image": "Panoda bir görsel bulunamadı. Önce bir görseli (örn. ekran görüntüsü) kopyala, sonra tekrar dene.",
        "clipboard_default_name": "Pano Görseli",
        "no_file": "— dosya seçilmedi —",
        "confirm_remove_title": "Silme Onayı",
        "confirm_remove_msg": "{n} adım kaldırılsın mı?",
        "rename_title": "Adımı Yeniden Adlandır",
        "rename_prompt": "Bu adım için yeni bir isim girin:",
        "no_selection": "Önce listeden en az bir adım seç.",
        "no_selection_single": "Yeniden adlandırmak için tek bir adım seç.",
        "toggle_ui": "🎨 Klasik Arayüz",
        "toggle_ui_modern": "🎨 Modern Arayüz",
        "editing_hint": "✏️ \"{name}\" düzenleniyor — değerleri değiştir ve Güncelle'ye bas, ya da ✖ ile vazgeç.",
        "changelog_title": "🎉 Yenilikler — v{version}",
        "changelog_close": "Harika, başlayalım! 🚀",
        "accept_btn": "Kabul Ediyorum",
        "decline_btn": "Reddet ve Çık",
        "modal_ok": "Tamam",
        "modal_cancel": "Vazgeç",
        "warn_title": "Uyarı",
        "info_title": "Bilgi",
        "error_title": "Bir şeyler ters gitti",
        "disclaimer_title": "Yasal Sorumluluk Reddi ve Kullanım Şartları",
        "disclaimer_msg": (
            "YASAL UYARI VE SORUMLULUK REDDİ:\n\n"
            "1. Bu yazılım sadece otomasyon ve kişisel test amaçlı geliştirilmiştir.\n"
            "2. Bu programın kullanımıyla gerçekleştirilen tüm eylemlerin sorumluluğu tamamen KULLANICIYA aittir.\n"
            "3. Yazılımın kullanımı sonucu doğabilecek herhangi bir veri kaybı, hesap engellenmesi veya "
            "sistem hasarlarından geliştirici sorumlu tutulamaz.\n\n"
            "Şartları okudunuz ve kabul ediyor musunuz?"
        )
    }
}

THEMES = {
    "DARK": {
        "bg": "#121212", "frame_bg": "#1e1e1e", "text": "#FFFFFF", "text_muted": "#888888",
        "border": "#2c2c2c", "red": "#CF6679", "green": "#4CAF50", "entry_bg": "#2A2A2A",
        "tree_bg": "#181818", "tree_sel": "#333333", "btn_face": "#242424",
    },
    "LIGHT": {
        "bg": "#F5F5F5", "frame_bg": "#FFFFFF", "text": "#121212", "text_muted": "#666666",
        "border": "#CCCCCC", "red": "#D32F2F", "green": "#2E7D32", "entry_bg": "#EEEEEE",
        "tree_bg": "#FAFAFA", "tree_sel": "#E0E0E0", "btn_face": "#EAEAEA",
    },
    "CLASSIC": {
        "bg": "#F0F0F0", "frame_bg": "#FFFFFF", "text": "#000000", "text_muted": "#555555",
        "border": "#ADADAD", "red": "#C42B1C", "green": "#107C10", "entry_bg": "#FFFFFF",
        "tree_bg": "#FFFFFF", "tree_sel": "#CCE4F7", "btn_face": "#E1E1E1",
    },
}

PREVIEW_W, PREVIEW_H = 200, 160
THUMB_SIZE = 30


class TriggerApp:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()
        self.root.report_callback_exception = self._handle_uncaught_exception

        self._startup_warnings = []
        self._warned_once = set()
        self._notify_queue = []
        self._notify_active = False

        self.settings = self._load_settings_dict()
        self.current_lang = self.settings.get("lang", "EN")
        self.current_theme = self.settings.get("theme", "DARK")
        self.ui_mode = self.settings.get("ui_mode", "MODERN")
        self.accent_key = self.settings.get("accent", "orange")

        self.steps = self._normalize_steps(self.settings.get("queue", []))
        self.editing_id = None
        self.is_running = False
        self.is_paused = False
        self.worker_thread = None
        self._preview_photo = None
        self._splash_photo = None
        self._tree_thumbs = {}

        self.name_var = tk.StringVar()
        self.img_path_var = tk.StringVar()
        self.img_display_var = tk.StringVar(value=self._get_t("no_file"))
        self.conf_var = tk.StringVar(value="0.80")
        self.delay_val_var = tk.StringVar(value="1.5")
        self.click_count_var = tk.StringVar(value="1")
        self.region_var = tk.StringVar(value="")

        self.root.title(self._get_t("title"))
        self.header_logo_photo = None
        self._app_icon_photo = None
        self._show_splash(on_done=self._post_splash)
        # Icon file I/O is deferred until after the splash is already showing,
        # so the splash appears as fast as possible instead of waiting on it.
        self.root.after(10, self._load_icons_deferred)

    def _load_icons_deferred(self):
        self._set_app_icon()
        self.header_logo_photo = self._load_header_logo(44)

    # ---------- global error safety net ----------

    def _handle_uncaught_exception(self, exc_type, exc_value, exc_tb):
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(details, file=sys.stderr)
        try:
            self._show_modal(self._get_t("error_title"), str(exc_value) or exc_type.__name__, mode="error")
        except Exception:
            pass

    def _error_text(self, code):
        info = ERROR_CODES.get(code, {}).get(self.current_lang) or ERROR_CODES.get(code, {}).get("EN")
        if not info:
            return code, ""
        title, hint = info
        return f"{code} — {title}", hint

    def _show_error_modal(self, code, detail="", mode="error"):
        title, hint = self._error_text(code)
        msg = hint + (f"\n\n{detail}" if detail else "") + "\n\nerrors-code.txt → " + code
        return self._show_modal(title, msg, mode=mode, show_copy=True)

    def _warn_once(self, key, code, detail="", mode="warning"):
        """Queues a background-triggered notification so at most ONE such dialog is
        ever alive at a time — showing several simultaneously (e.g. multiple failing
        steps during automation) previously caused overlapping grabs where dialogs
        looked 'stuck' and stopped responding to clicks."""
        if key in self._warned_once:
            return
        self._warned_once.add(key)
        self._notify_queue.append((code, detail, mode))
        self._process_notify_queue()

    def _process_notify_queue(self):
        if self._notify_active or not self._notify_queue:
            return
        self._notify_active = True
        code, detail, mode = self._notify_queue.pop(0)
        try:
            self._show_error_modal(code, detail=detail, mode=mode)
        finally:
            self._notify_active = False
            if self._notify_queue:
                self.root.after(30, self._process_notify_queue)

    # ---------- settings / persistence ----------

    def _settings_path(self):
        d = os.path.join(os.path.expanduser("~"), ".trigger")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, "settings.json")

    def _load_settings_dict(self):
        path = self._settings_path()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            self._startup_warnings.append("TRG-006")
            return {}

    def _save_settings_dict(self):
        self.settings["lang"] = self.current_lang
        self.settings["theme"] = self.current_theme
        self.settings["ui_mode"] = self.ui_mode
        self.settings["accent"] = self.accent_key
        self.settings["queue"] = self.steps
        try:
            with open(self._settings_path(), "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception:
            self.root.after(0, lambda: self._warn_once("save_settings", "TRG-007"))

    def _normalize_steps(self, loaded):
        normalized = []
        for s in loaded:
            path = s.get("path", "")
            region = s.get("region")
            if region and (not isinstance(region, (list, tuple)) or len(region) != 4):
                region = None
            normalized.append({
                "id": s.get("id") or uuid.uuid4().hex,
                "name": s.get("name") or os.path.splitext(os.path.basename(path))[0] or "Step",
                "path": path,
                "confidence": float(s.get("confidence", 0.8)),
                "delay": float(s.get("delay", 1.0)),
                "unit": canon_unit(s.get("unit", "sec")),
                "enabled": bool(s.get("enabled", True)),
                "click_count": max(1, int(s.get("click_count", 1))),
                "region": list(region) if region else None,
            })
        return normalized

    # ---------- startup sequence ----------

    def _asset_path(self, *names):
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        for name in names:
            p = os.path.join(base_path, name)
            if os.path.exists(p):
                return p
        return None

    def _show_splash(self, on_done):
        c = self._colors()
        splash = tk.Toplevel(self.root)
        self._splash = splash
        splash.overrideredirect(True)
        splash.configure(bg="#0d0d0d")
        w, h = 420, 480
        sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
        x, y = (sw - w) // 2, (sh - h) // 2
        splash.geometry(f"{w}x{h}+{x}+{y}")
        try:
            splash.attributes("-topmost", True)
            splash.attributes("-alpha", 0.0)
        except tk.TclError:
            pass

        icon_path = self._asset_path("icon.png", "logo.png")
        if icon_path:
            try:
                img = Image.open(icon_path).convert("RGBA")
                img.thumbnail((136, 136), Image.LANCZOS)
                self._splash_photo = ImageTk.PhotoImage(img)
            except Exception:
                self._splash_photo = None

        tk.Frame(splash, bg="#0d0d0d", height=46).pack()
        if self._splash_photo:
            tk.Label(splash, image=self._splash_photo, bg="#0d0d0d").pack()
        else:
            tk.Label(splash, text="⚡", font=("Segoe UI Emoji", 44), bg="#0d0d0d", fg=c["accent"]).pack()

        tk.Label(splash, text="TRIGGER", font=("Segoe UI", 23, "bold"),
                 fg=c["accent"], bg="#0d0d0d").pack(pady=(14, 0))
        tk.Label(splash, text="A U T O M A T I O N   E N G I N E", font=("Segoe UI", 8),
                 fg="#888888", bg="#0d0d0d").pack(pady=(4, 22))

        bar_w, bar_h = 260, 5
        bar_canvas = tk.Canvas(splash, width=bar_w, height=bar_h, bg="#0d0d0d", highlightthickness=0)
        bar_canvas.pack(pady=(30, 0))
        bar_canvas.create_rectangle(0, 0, bar_w, bar_h, fill="#232323", outline="", tags="track")

        msgs = SPLASH_MESSAGES.get(self.current_lang, SPLASH_MESSAGES["EN"])
        status_var = tk.StringVar(value=msgs[0])
        tk.Label(splash, textvariable=status_var, font=("Segoe UI", 9),
                 fg="#999999", bg="#0d0d0d").pack(pady=(16, 0))

        state = {"alpha": 0.0, "loop": 0, "bar_t": 0.0}
        highlight_w = 90

        def draw_bar():
            bar_canvas.delete("hl")
            frac = _ease_in_out(state["bar_t"])
            x = -highlight_w + frac * (bar_w + highlight_w)
            segs = 18
            for i in range(segs):
                seg_x0 = x + (highlight_w / segs) * i
                seg_x1 = seg_x0 + (highlight_w / segs) + 1
                t = i / (segs - 1)
                bright = 1 - abs(t - 0.5) * 2
                color = _lerp_color("#232323", c["accent"], bright)
                bar_canvas.create_rectangle(seg_x0, 0, seg_x1, bar_h, fill=color, outline="", tags="hl")

        def fade_in():
            state["alpha"] = min(1.0, state["alpha"] + 0.09)
            try:
                splash.attributes("-alpha", state["alpha"])
            except tk.TclError:
                pass
            if state["alpha"] < 1.0:
                splash.after(14, fade_in)
            else:
                sweep()

        def sweep():
            state["bar_t"] += 0.028
            if state["bar_t"] >= 1.0:
                state["bar_t"] = 0.0
                state["loop"] += 1
                if state["loop"] < len(msgs):
                    status_var.set(msgs[state["loop"]])
            draw_bar()
            if state["loop"] < 3:
                splash.after(14, sweep)
            else:
                fade_out()

        def fade_out():
            state["alpha"] = max(0.0, state["alpha"] - 0.09)
            try:
                splash.attributes("-alpha", state["alpha"])
            except tk.TclError:
                pass
            if state["alpha"] > 0.0:
                splash.after(14, fade_out)
            else:
                splash.destroy()
                on_done()

        splash.after(50, fade_in)

    def _post_splash(self):
        if not self.settings.get("terms_accepted", False):
            if not self._show_disclaimer():
                self.root.destroy()
                sys.exit()
            self.settings["terms_accepted"] = True
            self._save_settings_dict()

        self._maybe_show_changelog()

        # Size the window to fit the actual screen instead of a fixed 1000x920 —
        # on smaller/laptop screens the old fixed size could push the bottom
        # action bar (Start/Pause/Cancel) below the visible desktop area.
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        win_w = min(1000, sw - 60)
        win_h = min(920, sh - 90)  # leaves room for the taskbar
        min_w, min_h = min(900, win_w), min(760, win_h)
        x = max((sw - win_w) // 2, 0)
        y = max((sh - win_h) // 2 - 15, 0)
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.root.minsize(min_w, min_h)
        self._apply_styles()
        self._build_interface()
        self.root.bind("<Control-v>", self._paste_from_clipboard)
        self.root.bind("<Control-V>", self._paste_from_clipboard)
        self.root.deiconify()
        try:
            self.root.attributes("-alpha", 1.0)
        except tk.TclError:
            pass

        for code in self._startup_warnings:
            self.root.after(300, lambda c=code: self._warn_once(f"startup_{c}", c, mode="warning"))
        self._startup_warnings = []

    def _show_disclaimer(self):
        c = self._colors()
        f = self._fonts()
        dlg = tk.Toplevel(self.root)
        dlg.overrideredirect(True)
        dlg.configure(bg=c["frame_bg"], highlightthickness=1, highlightbackground=c["accent"])
        try:
            dlg.attributes("-topmost", True)
        except tk.TclError:
            pass

        result = {"accepted": False}

        def accept():
            result["accepted"] = True
            dlg.destroy()

        def decline():
            result["accepted"] = False
            dlg.destroy()

        title_row = tk.Frame(dlg, bg=c["frame_bg"])
        title_row.pack(fill="x", padx=24, pady=(24, 14))
        if self.header_logo_photo is not None:
            tk.Label(title_row, image=self.header_logo_photo, bg=c["frame_bg"]).pack(side="left", padx=(0, 10))
        tk.Label(title_row, text=self._get_t("disclaimer_title"), font=f["header"],
                 bg=c["frame_bg"], fg=c["accent"], wraplength=430, justify="left").pack(side="left")

        tk.Label(dlg, text=self._get_t("disclaimer_msg"), font=f["main"], bg=c["frame_bg"],
                 fg=c["text"], wraplength=470, justify="left").pack(fill="x", padx=24, pady=(0, 20))

        btn_row = tk.Frame(dlg, bg=c["frame_bg"])
        btn_row.pack(fill="x", padx=24, pady=(0, 24))
        self._btn(btn_row, "✖ " + self._get_t("decline_btn"), decline, kind="danger").pack(
            side="left", fill="x", expand=True, ipady=9, padx=(0, 6))
        self._btn(btn_row, "✅ " + self._get_t("accept_btn"), accept, kind="accent").pack(
            side="left", fill="x", expand=True, ipady=9, padx=(6, 0))

        dlg.update_idletasks()
        w = 520
        h = min(dlg.winfo_reqheight(), int(dlg.winfo_screenheight() * 0.85))
        self._center_on_root(dlg, w, h)
        self._make_draggable(dlg, title_row)

        dlg.bind("<Escape>", lambda e: decline())
        dlg.lift()
        dlg.focus_force()
        dlg.grab_set()
        self.root.wait_window(dlg)
        return result["accepted"]

    def _maybe_show_changelog(self):
        last_seen = self.settings.get("last_seen_version", "")
        if last_seen == APP_VERSION or APP_VERSION not in CHANGELOG:
            return
        self._show_changelog_dialog()
        self.settings["last_seen_version"] = APP_VERSION
        self._save_settings_dict()

    def _show_changelog_dialog(self):
        c = self._colors()
        f = self._fonts()
        dlg = tk.Toplevel(self.root)
        dlg.overrideredirect(True)
        dlg.configure(bg=c["frame_bg"], highlightthickness=1, highlightbackground=c["accent"])
        try:
            dlg.attributes("-topmost", True)
        except tk.TclError:
            pass

        title_row = tk.Frame(dlg, bg=c["frame_bg"])
        title_row.pack(anchor="w", padx=24, pady=(24, 12), fill="x")
        if self.header_logo_photo is not None:
            tk.Label(title_row, image=self.header_logo_photo, bg=c["frame_bg"]).pack(side="left", padx=(0, 10))
        tk.Label(title_row, text=self._get_t("changelog_title").format(version=APP_VERSION),
                 font=f["header"], bg=c["frame_bg"], fg=c["accent"], wraplength=380,
                 justify="left").pack(side="left", anchor="w")

        btn = self._btn(dlg, self._get_t("changelog_close"), dlg.destroy, kind="accent")
        btn.pack(side="bottom", pady=20, ipadx=16, ipady=8)

        body_text = "\n\n".join(CHANGELOG[APP_VERSION].get(self.current_lang, []))
        self._build_scrollable_dialog_body(dlg, body_text, c, f, width=520, height=680)
        self._make_draggable(dlg, title_row)

        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.lift()
        dlg.focus_force()
        dlg.grab_set()
        self.root.wait_window(dlg)

    def _build_scrollable_dialog_body(self, dlg, text, c, f, width=480, height=620):
        h = min(height, int(dlg.winfo_screenheight() * 0.85))
        self._center_on_root(dlg, width, h)

        body_wrap = tk.Frame(dlg, bg=c["frame_bg"])
        body_wrap.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        canvas = tk.Canvas(body_wrap, bg=c["frame_bg"], highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(body_wrap, orient="vertical", command=canvas.yview,
                                  bg=c["btn_face"], troughcolor=c["frame_bg"],
                                  activebackground=c["accent"], highlightthickness=0,
                                  bd=0, width=10, relief="flat", elementborderwidth=0)
        body = tk.Frame(canvas, bg=c["frame_bg"])
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=body, anchor="nw", width=width - 48 - 18)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for line in text.split("\n\n"):
            tk.Label(body, text=line, font=f["main"], bg=c["frame_bg"], fg=c["text"],
                     wraplength=width - 80, justify="left", anchor="w").pack(anchor="w", pady=4, fill="x")

        def _wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<MouseWheel>", _wheel)
        body.bind("<MouseWheel>", _wheel)

    # ---------- custom modal (replaces messagebox / simpledialog entirely) ----------

    def _show_modal(self, title, message, mode="info", initial_value="", show_copy=False):
        c = self._colors()
        f = self._fonts()
        icons = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "confirm": "❓", "prompt": "✏️"}

        dlg = tk.Toplevel(self.root)
        dlg.overrideredirect(True)
        dlg.configure(bg=c["frame_bg"], highlightthickness=1, highlightbackground=c["accent"])
        try:
            dlg.attributes("-topmost", True)
        except tk.TclError:
            pass

        result = {"value": None}

        title_row = tk.Frame(dlg, bg=c["frame_bg"])
        title_row.pack(fill="x", padx=22, pady=(22, 10))
        tk.Label(title_row, text=icons.get(mode, "ℹ️"), font=("Segoe UI Emoji", 17),
                 bg=c["frame_bg"], fg=c["accent"]).pack(side="left", padx=(0, 10))
        tk.Label(title_row, text=title, font=f["header"], bg=c["frame_bg"], fg=c["accent"],
                 wraplength=360, justify="left").pack(side="left")

        tk.Label(dlg, text=message, font=f["main"], bg=c["frame_bg"], fg=c["text"],
                 wraplength=380, justify="left").pack(fill="x", padx=22, pady=(0, 14))

        entry_var = None
        if mode == "prompt":
            entry_var = tk.StringVar(value=initial_value)
            e = tk.Entry(dlg, textvariable=entry_var, bg=c["entry_bg"], fg=c["text"],
                         insertbackground=c["accent"], relief="flat", bd=1, font=f["main"])
            e.pack(fill="x", padx=22, pady=(0, 16), ipady=7)
            e.focus_set()
            e.select_range(0, "end")

        def close(val):
            result["value"] = val
            dlg.destroy()

        if show_copy:
            copy_row = tk.Frame(dlg, bg=c["frame_bg"])
            copy_row.pack(fill="x", padx=22, pady=(0, 6))
            copy_lbl = tk.Label(copy_row, text="", font=("Segoe UI", 8), bg=c["frame_bg"], fg=c["text_muted"])
            copy_lbl.pack(side="left")

            def do_copy():
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(f"{title}\n\n{message}")
                    self.root.update()
                    copy_lbl.config(text=self._get_t("copied_hint"), fg=c["accent"])
                    dlg.after(1400, lambda: copy_lbl.config(text=""))
                except Exception:
                    pass

            self._btn(copy_row, "📋 " + self._get_t("copy_btn"), do_copy).pack(side="right")

        btn_row = tk.Frame(dlg, bg=c["frame_bg"])
        btn_row.pack(fill="x", padx=22, pady=(0, 22))

        if mode == "confirm":
            self._btn(btn_row, "✖ " + self._get_t("modal_cancel"), lambda: close(False), kind="danger").pack(
                side="left", fill="x", expand=True, ipady=8, padx=(0, 6))
            self._btn(btn_row, "✅ " + self._get_t("modal_ok"), lambda: close(True), kind="accent").pack(
                side="left", fill="x", expand=True, ipady=8, padx=(6, 0))
        elif mode == "prompt":
            self._btn(btn_row, "✖ " + self._get_t("modal_cancel"), lambda: close(None), kind="danger").pack(
                side="left", fill="x", expand=True, ipady=8, padx=(0, 6))
            self._btn(btn_row, "✅ " + self._get_t("modal_ok"), lambda: close(entry_var.get()), kind="accent").pack(
                side="left", fill="x", expand=True, ipady=8, padx=(6, 0))
            dlg.bind("<Return>", lambda e: close(entry_var.get()))
        else:
            self._btn(btn_row, self._get_t("modal_ok"), lambda: close(True), kind="accent").pack(fill="x", ipady=8)

        dlg.bind("<Escape>", lambda e: close(False if mode == "confirm" else None))
        dlg.update_idletasks()
        w = max(420, dlg.winfo_reqwidth())
        h = dlg.winfo_reqheight()
        self._center_on_root(dlg, w, h)
        self._make_draggable(dlg, title_row)
        dlg.lift()
        dlg.grab_set()
        dlg.focus_force()
        self.root.wait_window(dlg)
        return result["value"]

    # ---------- helpers ----------

    def _colors(self):
        base = THEMES["CLASSIC"] if self.ui_mode == "CLASSIC" else THEMES[self.current_theme]
        c = dict(base)
        accent, accent_active = ACCENT_PRESETS.get(self.accent_key, ACCENT_PRESETS["orange"])
        c["accent"] = accent
        c["accent_active"] = accent_active
        return c

    def _fonts(self):
        if self.ui_mode == "CLASSIC":
            return {
                "header": ("Segoe UI", 13, "bold"),
                "bold": ("Segoe UI", 9, "bold"),
                "main": ("Segoe UI", 9),
            }
        return {
            "header": ("Segoe UI", 15, "bold"),
            "bold": ("Segoe UI", 10, "bold"),
            "main": ("Segoe UI", 9, "bold"),
        }

    def _get_t(self, key):
        return LANGUAGES[self.current_lang].get(key, "")

    def _to_float(self, text, default):
        try:
            return float(str(text).strip().replace(",", "."))
        except (ValueError, TypeError):
            return default

    def _set_app_icon(self):
        icon_names = ["icon.ico", "icon.png", "logo.ico", "logo.png"]
        self._app_icon_photo = None
        for icon_name in icon_names:
            p = self._asset_path(icon_name)
            if p:
                try:
                    img = Image.open(p)
                    photo = ImageTk.PhotoImage(img)
                    self.root.iconphoto(True, photo)
                    self._app_icon_photo = photo
                    break
                except Exception:
                    pass

    def _load_header_logo(self, size=44):
        p = self._asset_path("icon.png", "logo.png")
        if not p:
            return None
        try:
            img = Image.open(p).convert("RGBA")
            img.thumbnail((size, size), Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    def _make_thumb(self, path, size=THUMB_SIZE):
        try:
            img = Image.open(path).convert("RGBA")
            img.thumbnail((size, size), Image.LANCZOS)
            square = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            offset = ((size - img.width) // 2, (size - img.height) // 2)
            square.paste(img, offset, img)
            return ImageTk.PhotoImage(square)
        except Exception:
            return None

    # ---------- styling ----------

    def _apply_styles(self):
        c = self._colors()
        f = self._fonts()
        self.root.configure(bg=c["bg"])

        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=c["bg"], foreground=c["text"], font=f["main"])
        style.configure("TFrame", background=c["bg"])
        style.configure("TLabelframe", background=c["bg"], foreground=c["accent"],
                         borderwidth=1, relief=("groove" if self.ui_mode == "CLASSIC" else "solid"))
        style.configure("TLabelframe.Label", background=c["bg"], foreground=c["accent"], font=f["bold"])
        style.configure("TLabel", background=c["bg"], foreground=c["text"], font=f["main"])

        style.configure("TCombobox", fieldbackground=c["entry_bg"], background=c["frame_bg"],
                         foreground=c["text"], arrowcolor=c["accent"], bordercolor=c["border"],
                         darkcolor=c["entry_bg"], lightcolor=c["entry_bg"])
        style.map("TCombobox", fieldbackground=[("readonly", c["entry_bg"])],
                  foreground=[("readonly", c["text"])])

        style.configure("Treeview", background=c["tree_bg"], foreground=c["text"],
                         fieldbackground=c["tree_bg"],
                         rowheight=(32 if self.ui_mode == "CLASSIC" else 44),
                         borderwidth=0, font=f["main"])
        style.configure("Treeview.Heading", background=c["frame_bg"], foreground=c["accent"],
                         font=f["bold"], relief="flat")
        style.map("Treeview", background=[("selected", c["tree_sel"])])

    def _btn(self, parent, text, command, kind="normal", **kw):
        c = self._colors()
        f = self._fonts()
        classic = self.ui_mode == "CLASSIC"

        if kind == "accent":
            bg, fg, active = c["accent"], "#FFFFFF", c["accent_active"]
        elif kind == "danger":
            bg, fg, active = (c["btn_face"] if classic else c["frame_bg"]), c["red"], c["border"]
        else:
            bg, fg, active = (c["btn_face"] if classic else c["frame_bg"]), c["text"], c["border"]

        b = tk.Button(
            parent, text=text, command=command, bg=bg, fg=fg, activebackground=active,
            activeforeground=fg, relief=("raised" if classic else "flat"),
            bd=(1 if classic else 0), font=f["bold"] if kind == "accent" else f["main"],
            cursor="hand2", **kw
        )
        self._attach_hover_animation(b, bg, active)
        return b

    def _attach_hover_animation(self, widget, bg_hex, hover_hex, steps=6, delay=12):
        """Animates a widget's bg color smoothly between two hex colors on
        hover, instead of relying on Tk's instant activebackground swap."""
        state = {"job": None}

        def animate(target_hex):
            if state["job"]:
                try:
                    widget.after_cancel(state["job"])
                except Exception:
                    pass
            try:
                start_hex = widget.cget("bg")
                if not str(start_hex).startswith("#"):
                    start_hex = bg_hex
            except Exception:
                start_hex = bg_hex

            def step(i=0):
                if not widget.winfo_exists():
                    return
                t = i / steps
                col = _lerp_color(start_hex, target_hex, t)
                try:
                    widget.config(bg=col)
                except tk.TclError:
                    return
                if i < steps:
                    state["job"] = widget.after(delay, lambda: step(i + 1))
                else:
                    state["job"] = None

            step()

        widget.bind("<Enter>", lambda e: animate(hover_hex))
        widget.bind("<Leave>", lambda e: animate(bg_hex))

    def _pill(self, parent, text, command, kind="accent", width=180, height=44):
        c = self._colors()
        f = self._fonts()
        if kind == "accent":
            colors = {"bg": c["accent"], "hover": c["accent_active"], "fg": "#FFFFFF",
                      "disabled_bg": c["btn_face"], "disabled_fg": c["text_muted"],
                      "outline": c["accent_active"], "outline_disabled": c["border"]}
        elif kind == "danger":
            # fg is always white (not red-on-red) so the label stays legible on hover,
            # while the red OUTLINE gives the "danger" cue even before hovering.
            colors = {"bg": c["btn_face"], "hover": c["red"], "fg": "#FFFFFF",
                      "disabled_bg": c["btn_face"], "disabled_fg": c["text_muted"],
                      "outline": c["red"], "outline_disabled": c["border"]}
        else:
            colors = {"bg": c["btn_face"], "hover": c["border"], "fg": c["text"],
                      "disabled_bg": c["btn_face"], "disabled_fg": c["text_muted"],
                      "outline": c["border"], "outline_disabled": c["border"]}
        radius = 10 if self.ui_mode == "CLASSIC" else height // 2
        return ImageButton(parent, text, command, colors, f["bold"], width=width, height=height, radius=radius)

    def _center_on_root(self, win, w, h):
        """Positions a Toplevel relative to the MAIN app window's current location
        (falling back to screen-center only if root has no real geometry yet, e.g.
        during the very first splash/disclaimer). This is what makes popups feel
        attached to the app instead of stranded in the middle of the screen."""
        self.root.update_idletasks()
        rw, rh = self.root.winfo_width(), self.root.winfo_height()
        if rw > 10 and rh > 10 and self.root.winfo_viewable():
            rx, ry = self.root.winfo_x(), self.root.winfo_y()
            x = rx + (rw - w) // 2
            y = ry + (rh - h) // 2
        else:
            sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
            x, y = (sw - w) // 2, (sh - h) // 2
        win.geometry(f"{w}x{h}+{max(x,0)}+{max(y,0)}")

    def _make_draggable(self, win, *handles):
        """Lets a chrome-less (overrideredirect) Toplevel be dragged by its
        title area, since it has no native title bar to grab."""
        state = {"x": 0, "y": 0}

        def start(e):
            state["x"], state["y"] = e.x, e.y

        def move(e):
            win.geometry(f"+{win.winfo_x() + e.x - state['x']}+{win.winfo_y() + e.y - state['y']}")

        for h in handles:
            h.bind("<Button-1>", start)
            h.bind("<B1-Motion>", move)

    # ---------- fade transition ----------

    def _fade_transition(self, mid_callback, steps=16, delay=10, min_alpha=0.35):
        """Dims the window rather than making it fully transparent (which briefly
        reveals the desktop behind it and looks like a glitch), then swaps content
        and eases back in — a much steadier, more premium-feeling transition."""
        def fade_out(i=0):
            try:
                t = _ease_in_out(i / steps)
                alpha = 1.0 - t * (1.0 - min_alpha)
                self.root.attributes("-alpha", max(alpha, min_alpha))
            except tk.TclError:
                mid_callback()
                return
            if i < steps:
                self.root.after(delay, lambda: fade_out(i + 1))
            else:
                mid_callback()
                fade_in(0)

        def fade_in(i=0):
            try:
                t = _ease_in_out(i / steps)
                alpha = min_alpha + t * (1.0 - min_alpha)
                self.root.attributes("-alpha", min(alpha, 1.0))
            except tk.TclError:
                pass
            if i < steps:
                self.root.after(delay, lambda: fade_in(i + 1))
            else:
                try:
                    self.root.attributes("-alpha", 1.0)
                except tk.TclError:
                    pass

        fade_out()

    # ---------- interface ----------

    def _build_interface(self):
        c = self._colors()
        f = self._fonts()

        # ----- header -----
        header = tk.Frame(self.root, bg=c["frame_bg"], height=64,
                           highlightthickness=1, highlightbackground=c["border"])
        header.pack(fill="x", padx=16, pady=(16, 8))
        header.pack_propagate(False)

        title_wrap = tk.Frame(header, bg=c["frame_bg"])
        title_wrap.pack(side="left", padx=16)
        if self.header_logo_photo is not None:
            tk.Label(title_wrap, image=self.header_logo_photo, bg=c["frame_bg"]).pack(side="left", padx=(0, 8))
            self.title_lbl = tk.Label(title_wrap, text="TRIGGER", font=f["header"],
                                       bg=c["frame_bg"], fg=c["accent"])
        else:
            self.title_lbl = tk.Label(title_wrap, text="⚡ TRIGGER", font=f["header"],
                                       bg=c["frame_bg"], fg=c["accent"])
        self.title_lbl.pack(side="left")

        self.status_lbl = tk.Label(header, text="", font=f["bold"], bg=c["btn_face"],
                                    fg=c["text_muted"], padx=10, pady=3)
        self.status_lbl.pack(side="left", padx=10)

        self.abort_lbl = tk.Label(header, text=self._get_t("abort"), font=f["bold"],
                                   bg=c["frame_bg"], fg=c["red"])
        self.abort_lbl.pack(side="right", padx=16)

        self.btn_color = tk.Button(
            header, text="🌈", command=self._show_color_picker, bg=c["bg"], fg=c["text"],
            relief="flat", padx=8, font=("Segoe UI Emoji", 10), cursor="hand2"
        )
        self.btn_color.pack(side="right", padx=4)

        self.btn_ui_mode = tk.Button(
            header, text=self._get_t("toggle_ui" if self.ui_mode == "MODERN" else "toggle_ui_modern"),
            command=self._toggle_ui_mode, bg=c["bg"], fg=c["text"], relief="flat",
            padx=8, font=f["main"], cursor="hand2"
        )
        self.btn_ui_mode.pack(side="right", padx=4)

        if self.ui_mode == "MODERN":
            self.btn_theme = tk.Button(
                header, text="🌙" if self.current_theme == "DARK" else "☀️",
                command=self._toggle_theme, bg=c["bg"], fg=c["text"], relief="flat",
                padx=8, font=("Segoe UI Emoji", 10), cursor="hand2"
            )
            self.btn_theme.pack(side="right", padx=4)

        self.btn_lang = tk.Button(header, text=self.current_lang, command=self._toggle_language,
                                   bg=c["bg"], fg=c["accent"], relief="flat", padx=10,
                                   font=f["bold"], cursor="hand2")
        self.btn_lang.pack(side="right", padx=4)

        # ----- config box -----
        self.box_config = ttk.LabelFrame(self.root, text=self._get_t("config_box"), padding=12)
        self.box_config.pack(fill="x", padx=16, pady=8)

        self.editing_hint_lbl = tk.Label(self.box_config, text="", font=f["main"],
                                          bg=c["bg"], fg=c["accent"], wraplength=900, justify="left")
        self.editing_hint_lbl.pack(fill="x", pady=(0, 8))

        form_row = tk.Frame(self.box_config, bg=c["bg"])
        form_row.pack(fill="x")

        left = tk.Frame(form_row, bg=c["bg"])
        left.pack(side="left", padx=(0, 16))

        self.drop_zone = tk.Label(
            left, text=self._get_t("drop_hint"), bg=c["entry_bg"], fg=c["text_muted"],
            width=24, height=8, relief=("ridge" if self.ui_mode == "CLASSIC" else "flat"),
            bd=2 if self.ui_mode == "CLASSIC" else 1,
            highlightthickness=(0 if self.ui_mode == "CLASSIC" else 1),
            highlightbackground=c["border"], font=f["main"], justify="center", cursor="hand2"
        )
        self.drop_zone.pack()
        self.drop_zone.bind("<Button-1>", lambda e: self._select_image())

        if HAS_DND:
            try:
                self.drop_zone.drop_target_register(DND_FILES)
                self.drop_zone.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass
        else:
            tk.Label(left, text=self._get_t("no_dnd_hint"), bg=c["bg"], fg=c["text_muted"],
                     font=("Segoe UI", 7), wraplength=190, justify="center").pack(pady=(4, 0))

        self.lbl_filename = tk.Label(left, textvariable=self.img_display_var, bg=c["bg"],
                                      fg=c["text_muted"], font=("Segoe UI", 8), wraplength=190)
        self.lbl_filename.pack(pady=(6, 0))

        self._update_preview(self.img_path_var.get())

        right = tk.Frame(form_row, bg=c["bg"])
        right.pack(side="left", fill="both", expand=True)
        right.columnconfigure(0, minsize=150)
        right.columnconfigure(1, weight=1)

        row = 0
        tk.Label(right, text=self._get_t("name_lbl"), anchor="w", bg=c["bg"], fg=c["text"],
                 font=f["main"]).grid(row=row, column=0, sticky="w", pady=5)
        self.entry_name = tk.Entry(right, textvariable=self.name_var, bg=c["entry_bg"], fg=c["text"],
                                    insertbackground=c["accent"], relief="flat", bd=1)
        self.entry_name.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=5, ipady=5)

        row += 1
        tk.Label(right, text=self._get_t("target_lbl"), anchor="w", bg=c["bg"], fg=c["text"],
                 font=f["main"]).grid(row=row, column=0, sticky="w", pady=5)
        self.lbl_target_path = tk.Label(right, textvariable=self.img_display_var, bg=c["entry_bg"],
                                         fg=c["text"], anchor="w", font=f["main"])
        self.lbl_target_path.grid(row=row, column=1, sticky="ew", padx=(8, 4), pady=5, ipady=5)
        target_btns = tk.Frame(right, bg=c["bg"])
        target_btns.grid(row=row, column=2, pady=5)
        self._btn(target_btns, self._get_t("browse"), self._select_image).pack(side="left")
        self._btn(target_btns, "📋 " + self._get_t("paste_btn"), self._paste_from_clipboard).pack(side="left", padx=(4, 0))

        row += 1
        tk.Label(right, text=self._get_t("confidence"), anchor="w", bg=c["bg"], fg=c["text"],
                 font=f["main"]).grid(row=row, column=0, sticky="w", pady=5)
        self.sp_conf = tk.Spinbox(right, from_=0.10, to=1.00, increment=0.05, textvariable=self.conf_var,
                                   width=8, format="%.2f", bg=c["entry_bg"], fg=c["text"],
                                   insertbackground=c["accent"], buttonbackground=c["btn_face"],
                                   relief="flat", bd=1, justify="center")
        self.sp_conf.grid(row=row, column=1, sticky="w", padx=(8, 0), pady=5, ipady=3)

        row += 1
        tk.Label(right, text=self._get_t("delay"), anchor="w", bg=c["bg"], fg=c["text"],
                 font=f["main"]).grid(row=row, column=0, sticky="w", pady=5)
        delay_frame = tk.Frame(right, bg=c["bg"])
        delay_frame.grid(row=row, column=1, columnspan=2, sticky="w", padx=(8, 0), pady=5)
        self.sp_delay = tk.Spinbox(delay_frame, from_=0.0, to=3600.0, increment=0.5,
                                    textvariable=self.delay_val_var, width=10, bg=c["entry_bg"],
                                    fg=c["text"], insertbackground=c["accent"],
                                    buttonbackground=c["btn_face"], relief="flat", bd=1, justify="center")
        self.sp_delay.pack(side="left", ipady=3)
        self.unit_display_map = {
            "ms": self._get_t("unit_ms"), "sec": self._get_t("unit_sec"), "min": self._get_t("unit_min")
        }
        self.delay_unit_var = tk.StringVar(value=self.unit_display_map["sec"])
        self.cb_unit = ttk.Combobox(delay_frame, textvariable=self.delay_unit_var,
                                     values=list(self.unit_display_map.values()), width=8, state="readonly")
        self.cb_unit.pack(side="left", padx=(6, 0))

        row += 1
        tk.Label(right, text=self._get_t("click_count_lbl"), anchor="w", bg=c["bg"], fg=c["text"],
                 font=f["main"]).grid(row=row, column=0, sticky="w", pady=5)
        self.sp_clicks = tk.Spinbox(right, from_=1, to=999, increment=1, textvariable=self.click_count_var,
                                     width=8, bg=c["entry_bg"], fg=c["text"], insertbackground=c["accent"],
                                     buttonbackground=c["btn_face"], relief="flat", bd=1, justify="center")
        self.sp_clicks.grid(row=row, column=1, sticky="w", padx=(8, 0), pady=5, ipady=3)

        row += 1
        tk.Label(right, text=self._get_t("region_lbl"), anchor="w", bg=c["bg"], fg=c["text"],
                 font=f["main"]).grid(row=row, column=0, sticky="w", pady=5)
        region_frame = tk.Frame(right, bg=c["bg"])
        region_frame.grid(row=row, column=1, columnspan=2, sticky="w", padx=(8, 0), pady=5)
        self._btn(region_frame, self._get_t("select_region"), self._select_region).pack(side="left")
        self._btn(region_frame, self._get_t("clear_region"),
                   lambda: (self.region_var.set(""), self._update_region_label())).pack(side="left", padx=(4, 0))
        self.region_status_lbl = tk.Label(region_frame, text="", bg=c["bg"], fg=c["text_muted"],
                                           font=("Segoe UI", 8))
        self.region_status_lbl.pack(side="left", padx=(10, 0))
        self._update_region_label()

        row += 1
        btn_row = tk.Frame(right, bg=c["bg"])
        btn_row.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(14, 2))
        self.btn_add = self._pill(btn_row, self._get_t("add_btn"), self._save_step, kind="accent", width=260, height=46)
        self.btn_add.pack(side="left")
        self.btn_cancel_edit = self._pill(btn_row, self._get_t("cancel_edit"), self._clear_form,
                                           kind="danger", width=46, height=46)

        # ----- bottom bar & footer are packed BEFORE the queue box, with side="bottom".
        # Tk's pack() reserves space in the order widgets are packed — if the queue box
        # (which uses expand=True) were packed first, it would claim all remaining space
        # and push these controls below the visible window on short screens. Packing them
        # first guarantees Start/Pause/Cancel/Import/Export are always visible, and the
        # queue list simply shrinks (it has its own internal scrollbar) instead. -----
        footer = tk.Label(self.root, text=f"TRIGGER v{APP_VERSION}", font=("Segoe UI", 8),
                           bg=c["bg"], fg=c["text_muted"])
        footer.pack(side="bottom", pady=(0, 10))

        bottom_bar = tk.Frame(self.root, bg=c["bg"])
        bottom_bar.pack(side="bottom", fill="x", padx=16, pady=(4, 4))

        self._btn(bottom_bar, self._get_t("import"), self._load_profile).pack(side="left", padx=(0, 6))
        self._btn(bottom_bar, self._get_t("export"), self._save_profile).pack(side="left")

        action_frame = tk.Frame(bottom_bar, bg=c["bg"])
        action_frame.pack(side="right")
        self.btn_cancel = self._pill(action_frame, self._get_t("cancel"), self._cancel_engine,
                                      kind="danger", width=130, height=42)
        self.btn_cancel.pack(side="right", padx=(6, 0))
        self.btn_pause = self._pill(action_frame, self._get_t("pause"), self._toggle_pause,
                                     kind="normal", width=140, height=42)
        self.btn_pause.pack(side="right", padx=(6, 0))
        self.btn_start = self._pill(action_frame, self._get_t("start"), self._start_engine,
                                     kind="accent", width=130, height=42)
        self.btn_start.pack(side="right")

        # ----- queue box (packed LAST so it fills whatever space remains) -----
        self.box_queue = ttk.LabelFrame(self.root, text=self._get_t("queue_box"), padding=12)
        self.box_queue.pack(fill="both", expand=True, padx=16, pady=8)

        cols = ("#1", "#2", "#3", "#4", "#5", "#6", "#7")
        self.tree = ttk.Treeview(self.box_queue, columns=cols, show="tree headings")
        self.tree.column("#0", width=54, minwidth=54, anchor="center", stretch=False)
        self.tree.heading("#0", text="🖼")
        self._update_table_headings()
        self.tree.column("#1", width=36, anchor="center")
        self.tree.column("#2", width=150)
        self.tree.column("#3", width=150)
        self.tree.column("#4", width=64, anchor="center")
        self.tree.column("#5", width=64, anchor="center")
        self.tree.column("#6", width=54, anchor="center")
        self.tree.column("#7", width=50, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Button-2>", self._show_context_menu)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        tree_btns = tk.Frame(self.box_queue, bg=c["bg"])
        tree_btns.pack(fill="x", pady=(8, 0))
        self._btn(tree_btns, self._get_t("enable_sel"),
                  lambda: self._set_selected_enabled(True)).pack(side="left", padx=(0, 6))
        self._btn(tree_btns, self._get_t("disable_sel"),
                  lambda: self._set_selected_enabled(False)).pack(side="left", padx=(0, 6))
        self._btn(tree_btns, self._get_t("rename_sel"), self._rename_selected).pack(side="left", padx=(0, 6))
        self._btn(tree_btns, self._get_t("remove"), self._remove_selected, kind="danger").pack(side="right")

        self._refresh_tree()
        self._sync_status_ui()
        self._sync_edit_ui()

    def _update_table_headings(self):
        self.tree.heading("#1", text=self._get_t("col_status"))
        self.tree.heading("#2", text=self._get_t("col_name"))
        self.tree.heading("#3", text=self._get_t("col_target"))
        self.tree.heading("#4", text=self._get_t("col_conf"))
        self.tree.heading("#5", text=self._get_t("col_delay"))
        self.tree.heading("#6", text=self._get_t("col_unit"))
        self.tree.heading("#7", text=self._get_t("col_clicks"))

    # ---------- toggles (rebuild-safe, with fade transition) ----------

    def _do_rebuild(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self._apply_styles()
        self._build_interface()

    def _rebuild(self):
        self._fade_transition(self._do_rebuild)

    def _toggle_language(self):
        self.current_lang = "TR" if self.current_lang == "EN" else "EN"
        self.root.title(self._get_t("title"))
        self._save_settings_dict()
        self._rebuild()

    def _toggle_theme(self):
        self.current_theme = "LIGHT" if self.current_theme == "DARK" else "DARK"
        self._save_settings_dict()
        self._rebuild()

    def _toggle_ui_mode(self):
        self.ui_mode = "CLASSIC" if self.ui_mode == "MODERN" else "MODERN"
        self._save_settings_dict()
        self._rebuild()

    def _show_color_picker(self):
        c = self._colors()
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.configure(bg=c["frame_bg"], highlightthickness=1, highlightbackground=c["border"])
        try:
            popup.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.root.update_idletasks()
        x = self.btn_color.winfo_rootx()
        y = self.btn_color.winfo_rooty() + self.btn_color.winfo_height() + 4
        popup.geometry(f"+{x}+{y}")

        grid = tk.Frame(popup, bg=c["frame_bg"])
        grid.pack(padx=10, pady=10)
        cols = 4
        for i, (key, (hexcolor, _)) in enumerate(ACCENT_PRESETS.items()):
            swatch = tk.Canvas(grid, width=30, height=30, bg=c["frame_bg"], highlightthickness=0, cursor="hand2")
            outline = c["text"] if key == self.accent_key else c["frame_bg"]
            swatch.create_oval(3, 3, 27, 27, fill=hexcolor, outline=outline, width=2)
            swatch.grid(row=i // cols, column=i % cols, padx=4, pady=4)
            swatch.bind("<Button-1>", lambda e, k=key: self._pick_accent(k, popup))
        popup.bind("<FocusOut>", lambda e: popup.destroy())
        popup.focus_force()

    def _pick_accent(self, key, popup):
        self.accent_key = key
        self._save_settings_dict()
        try:
            popup.destroy()
        except Exception:
            pass
        self._rebuild()

    # ---------- preview / drag&drop ----------

    def _set_image_path(self, path):
        self.img_path_var.set(path)
        self.img_display_var.set(os.path.basename(path) if path else self._get_t("no_file"))

    def _update_preview(self, path):
        if not path or not os.path.exists(path):
            self.drop_zone.config(image="", text=self._get_t("drop_hint"))
            self._preview_photo = None
            return
        try:
            img = Image.open(path)
            img.thumbnail((PREVIEW_W, PREVIEW_H))
            photo = ImageTk.PhotoImage(img)
            self._preview_photo = photo
            self.drop_zone.config(image=photo, text="")
        except Exception:
            self.drop_zone.config(image="", text="⚠️")
            self._preview_photo = None

    def _on_drop(self, event):
        try:
            paths = self.root.tk.splitlist(event.data)
        except Exception:
            paths = [event.data]
        for p in paths:
            p = p.strip("{}")
            if p.lower().endswith(IMAGE_EXTS) and os.path.exists(p):
                self._set_image_path(p)
                if not self.name_var.get().strip():
                    self.name_var.set(os.path.splitext(os.path.basename(p))[0])
                self._update_preview(p)
                return

    def _select_image(self):
        f = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif")])
        if f:
            self._set_image_path(f)
            if not self.name_var.get().strip():
                self.name_var.set(os.path.splitext(os.path.basename(f))[0])
            self._update_preview(f)

    def _parse_region(self, region_str):
        """'left,top,w,h' -> [left, top, w, h] or None if empty/invalid."""
        region_str = (region_str or "").strip()
        if not region_str:
            return None
        try:
            parts = [int(round(float(p))) for p in region_str.split(",")]
            if len(parts) == 4 and parts[2] > 0 and parts[3] > 0:
                return parts
        except (ValueError, TypeError):
            pass
        return None

    def _update_region_label(self):
        region = self._parse_region(self.region_var.get())
        if region:
            self.region_status_lbl.config(text=f"{region[0]},{region[1]} · {region[2]}×{region[3]}")
        else:
            self.region_status_lbl.config(text=self._get_t("region_whole_screen"))

    def _select_region(self):
        """Full-screen click-and-drag rectangle picker. The main window hides itself
        so it isn't in the way, then a transparent full-screen overlay lets the user
        drag a box around the exact area to search in — this is what actually solves
        'it clicked the wrong lookalike file': restricting the search area means a
        similar-looking icon elsewhere on screen can never match."""
        c = self._colors()
        self.root.withdraw()

        overlay = tk.Toplevel(self.root)
        overlay.attributes("-fullscreen", True)
        try:
            overlay.attributes("-alpha", 0.30)
            overlay.attributes("-topmost", True)
        except tk.TclError:
            pass
        overlay.configure(bg="black", cursor="crosshair")

        canvas = tk.Canvas(overlay, bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.create_text(overlay.winfo_screenwidth() // 2, 36, text=self._get_t("region_hint"),
                            fill="white", font=("Segoe UI", 13, "bold"))

        state = {"x0": 0, "y0": 0, "rect": None}

        def on_press(e):
            state["x0"], state["y0"] = e.x, e.y
            if state["rect"]:
                canvas.delete(state["rect"])
            state["rect"] = canvas.create_rectangle(e.x, e.y, e.x, e.y, outline=c["accent"], width=2)

        def on_drag(e):
            if state["rect"]:
                canvas.coords(state["rect"], state["x0"], state["y0"], e.x, e.y)

        def finish(save):
            x0, y0 = state["x0"], state["y0"]
            x1 = canvas.winfo_pointerx() - canvas.winfo_rootx()
            y1 = canvas.winfo_pointery() - canvas.winfo_rooty()
            overlay.destroy()
            self.root.deiconify()
            if save:
                left, top = min(x0, x1), min(y0, y1)
                w, h = abs(x1 - x0), abs(y1 - y0)
                if w > 5 and h > 5:
                    self.region_var.set(f"{left},{top},{w},{h}")
                    self._update_region_label()

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", lambda e: finish(True))
        overlay.bind("<Escape>", lambda e: finish(False))
        overlay.focus_force()

    def _paste_from_clipboard(self, event=None):
        try:
            from PIL import ImageGrab
            img = ImageGrab.grabclipboard()
        except Exception:
            img = None

        if img is None or not hasattr(img, "save"):
            self._show_modal(self._get_t("warn_title"), self._get_t("warn_no_clipboard_image"), mode="warning")
            return

        save_dir = os.path.join(os.path.expanduser("~"), ".trigger", "clipboard_images")
        try:
            os.makedirs(save_dir, exist_ok=True)
            path = os.path.join(save_dir, f"clipboard_{uuid.uuid4().hex[:8]}.png")
            img.convert("RGB").save(path, "PNG")
        except Exception as e:
            self._show_error_modal("TRG-999", detail=str(e))
            return

        self._set_image_path(path)
        if not self.name_var.get().strip():
            self.name_var.set(self._get_t("clipboard_default_name"))
        self._update_preview(path)

    # ---------- queue management ----------

    def _find_step(self, iid):
        return next((s for s in self.steps if s["id"] == iid), None)

    def _refresh_tree(self):
        c = self._colors()
        self.tree.delete(*self.tree.get_children())
        self._tree_thumbs = {}
        unit_display = {
            "ms": self._get_t("unit_ms"), "sec": self._get_t("unit_sec"), "min": self._get_t("unit_min")
        }
        for s in self.steps:
            icon = "✅" if s.get("enabled", True) else "⛔"
            thumb = self._make_thumb(s["path"])
            self._tree_thumbs[s["id"]] = thumb
            region_mark = "🎯" if s.get("region") else ""
            self.tree.insert(
                "", "end", iid=s["id"], text="", image=thumb if thumb else "",
                values=(icon, s.get("name", "Step") + (" " + region_mark if region_mark else ""),
                        os.path.basename(s["path"]), f'{s["confidence"]:.2f}', s["delay"],
                        unit_display.get(canon_unit(s.get("unit", "sec")), "sec"),
                        f'×{s.get("click_count", 1)}'),
                tags=() if s.get("enabled", True) else ("disabled",)
            )
        self.tree.tag_configure("disabled", foreground=c["text_muted"])

    def _center_tree_item(self, iid):
        self.tree.update_idletasks()
        children = self.tree.get_children()
        if iid in children and len(children) > 0:
            idx = children.index(iid)
            frac = max(0.0, (idx - 3) / max(len(children), 1))
            self.tree.yview_moveto(frac)
        self.tree.selection_set(iid)
        self.tree.see(iid)

    def _collect_form_step(self, existing_id=None):
        path = self.img_path_var.get().strip()
        if not path:
            self._show_modal(self._get_t("warn_title"), self._get_t("warn_no_image"), mode="warning")
            return None

        name = self.name_var.get().strip() or os.path.splitext(os.path.basename(path))[0]

        raw_conf = self.conf_var.get()
        raw_delay = self.delay_val_var.get()
        raw_clicks = self.click_count_var.get()
        bad_input = (self._to_float(raw_conf, None) is None) or (self._to_float(raw_delay, None) is None)

        conf = self._to_float(raw_conf, 0.8)
        conf = min(max(conf, 0.1), 1.0)
        delay = max(self._to_float(raw_delay, 1.0), 0.0)
        click_count = max(1, int(self._to_float(raw_clicks, 1)))

        display_unit = self.delay_unit_var.get()
        reverse_map = {v: k for k, v in self.unit_display_map.items()}
        unit = reverse_map.get(display_unit, "sec")

        region = self._parse_region(self.region_var.get())

        if bad_input:
            self._show_modal(self._get_t("warn_title"), self._get_t("warn_bad_number"), mode="warning")

        return {
            "id": existing_id or uuid.uuid4().hex,
            "name": name, "path": path,
            "confidence": round(conf, 2), "delay": delay, "unit": unit,
            "click_count": click_count, "region": region,
        }

    def _save_step(self):
        step_data = self._collect_form_step(existing_id=self.editing_id)
        if step_data is None:
            return

        if self.editing_id:
            existing = self._find_step(self.editing_id)
            if existing:
                step_data["enabled"] = existing.get("enabled", True)
                existing.update(step_data)
            new_id = self.editing_id
        else:
            step_data["enabled"] = True
            self.steps.append(step_data)
            new_id = step_data["id"]

        self._refresh_tree()
        self._center_tree_item(new_id)
        self._save_settings_dict()
        self._clear_form()

    def _clear_form(self):
        self.editing_id = None
        self.name_var.set("")
        self._set_image_path("")
        self.conf_var.set("0.80")
        self.delay_val_var.set("1.5")
        self.delay_unit_var.set(self.unit_display_map["sec"])
        self.click_count_var.set("1")
        self.region_var.set("")
        self._update_region_label()
        self._update_preview("")
        self.tree.selection_remove(*self.tree.selection())
        self._sync_edit_ui()

    def _load_step_into_form(self, step):
        self.editing_id = step["id"]
        self.name_var.set(step.get("name", ""))
        self._set_image_path(step.get("path", ""))
        self.conf_var.set(f'{step.get("confidence", 0.8):.2f}')
        self.delay_val_var.set(str(step.get("delay", 1.0)))
        unit_disp = self.unit_display_map.get(canon_unit(step.get("unit", "sec")), self.unit_display_map["sec"])
        self.delay_unit_var.set(unit_disp)
        self.click_count_var.set(str(step.get("click_count", 1)))
        region = step.get("region")
        self.region_var.set(",".join(str(x) for x in region) if region else "")
        self._update_region_label()
        self._sync_edit_ui()

    def _sync_edit_ui(self):
        if self.editing_id:
            step = self._find_step(self.editing_id)
            name = step.get("name", "") if step else ""
            self.editing_hint_lbl.config(text=self._get_t("editing_hint").format(name=name))
            self.btn_add.set_text(self._get_t("update_btn"))
            self.btn_cancel_edit.pack(side="left", padx=(6, 0))
        else:
            self.editing_hint_lbl.config(text="")
            self.btn_add.set_text(self._get_t("add_btn"))
            self.btn_cancel_edit.pack_forget()

    def _on_tree_select(self, event=None):
        sel = self.tree.selection()
        if len(sel) == 1:
            step = self._find_step(sel[0])
            if step:
                self._update_preview(step["path"])
                self._load_step_into_form(step)

    def _on_tree_double_click(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return
        step = self._find_step(row)
        if step:
            step["enabled"] = not step.get("enabled", True)
            self._refresh_tree()
            self.tree.selection_set(row)
            self._save_settings_dict()

    def _set_selected_enabled(self, value):
        sel = self.tree.selection()
        if not sel:
            self._show_modal(self._get_t("info_title"), self._get_t("no_selection"), mode="info")
            return
        for iid in sel:
            step = self._find_step(iid)
            if step:
                step["enabled"] = value
        self._refresh_tree()
        for iid in sel:
            self.tree.selection_add(iid)
        self._save_settings_dict()

    def _rename_selected(self):
        sel = self.tree.selection()
        if len(sel) != 1:
            self._show_modal(self._get_t("info_title"), self._get_t("no_selection_single"), mode="info")
            return
        step = self._find_step(sel[0])
        if not step:
            return
        new_name = self._show_modal(self._get_t("rename_title"), self._get_t("rename_prompt"),
                                     mode="prompt", initial_value=step.get("name", ""))
        if new_name and new_name.strip():
            step["name"] = new_name.strip()
            self._refresh_tree()
            self.tree.selection_set(sel[0])
            self._save_settings_dict()

    def _remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            self._show_modal(self._get_t("info_title"), self._get_t("no_selection"), mode="info")
            return
        confirmed = self._show_modal(
            self._get_t("confirm_remove_title"),
            self._get_t("confirm_remove_msg").format(n=len(sel)),
            mode="confirm"
        )
        if not confirmed:
            return
        ids_to_remove = set(sel)
        if self.editing_id in ids_to_remove:
            self._clear_form()
        self.steps = [s for s in self.steps if s["id"] not in ids_to_remove]
        self._refresh_tree()
        self._save_settings_dict()

    def _show_context_menu(self, event):
        row = self.tree.identify_row(event.y)
        if row and row not in self.tree.selection():
            self.tree.selection_set(row)
        c = self._colors()
        menu = tk.Menu(self.root, tearoff=0, bg=c["frame_bg"], fg=c["text"])
        menu.add_command(label=self._get_t("enable_sel"), command=lambda: self._set_selected_enabled(True))
        menu.add_command(label=self._get_t("disable_sel"), command=lambda: self._set_selected_enabled(False))
        menu.add_separator()
        menu.add_command(label=self._get_t("rename_sel"), command=self._rename_selected)
        menu.add_command(label=self._get_t("remove"), command=self._remove_selected)
        menu.tk_popup(event.x_root, event.y_root)

    # ---------- profiles ----------

    def _save_profile(self):
        if not self.steps:
            return
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Config", "*.json")])
        if f:
            with open(f, "w", encoding="utf-8") as out:
                json.dump(self.steps, out, indent=2, ensure_ascii=False)

    def _load_profile(self):
        f = filedialog.askopenfilename(filetypes=[("JSON Config", "*.json")])
        if not f:
            return
        try:
            with open(f, "r", encoding="utf-8") as inp:
                loaded = json.load(inp)
        except Exception as e:
            self._show_modal(self._get_t("error_title"), str(e), mode="error")
            return
        self.steps = self._normalize_steps(loaded)
        self._refresh_tree()
        self._save_settings_dict()

    # ---------- engine ----------

    def _parse_delay_canon(self, val, unit):
        unit = canon_unit(unit)
        if unit == "ms":
            return val / 1000.0
        elif unit == "min":
            return val * 60.0
        return val

    def _sync_status_ui(self):
        c = self._colors()
        if self.is_running and not self.is_paused:
            self.status_lbl.config(text="● " + self._get_t("armed"), bg=c["accent"], fg="#FFFFFF")
            self.btn_start.set_enabled(False)
            self.btn_pause.set_enabled(True)
            self.btn_pause.set_text(self._get_t("pause"))
            self.btn_cancel.set_enabled(True)
        elif self.is_running and self.is_paused:
            self.status_lbl.config(text="⏸ " + self._get_t("status_paused"), bg=c["entry_bg"], fg=c["accent"])
            self.btn_start.set_enabled(False)
            self.btn_pause.set_enabled(True)
            self.btn_pause.set_text(self._get_t("resume"))
            self.btn_cancel.set_enabled(True)
        else:
            self.status_lbl.config(text="○ " + self._get_t("idle"), bg=c["btn_face"], fg=c["text_muted"])
            self.btn_start.set_enabled(True)
            self.btn_pause.set_enabled(False)
            self.btn_pause.set_text(self._get_t("pause"))
            self.btn_cancel.set_enabled(False)

    def _start_engine(self):
        if not any(s.get("enabled", True) for s in self.steps):
            self._show_modal(self._get_t("warn_title"), self._get_t("warn_empty"), mode="warning")
            return

        needs_fuzzy = any(s.get("enabled", True) and s.get("confidence", 1.0) < 0.999 for s in self.steps)
        self.use_confidence = True
        if needs_fuzzy and not _ensure_cv2_checked():
            proceed = self._show_error_modal("TRG-002", mode="confirm")
            if not proceed:
                return
            self.use_confidence = False  # fall back to exact pixel matching (no OpenCV needed)

        # Pre-load every enabled step's target image via PIL, once, instead of handing
        # raw file paths to pyautogui/OpenCV every 0.2s. This fixes a real OpenCV bug on
        # Windows where cv2.imread() silently returns None for paths containing non-ASCII
        # characters (Turkish letters like ç/ı/ğ/ş/ö/ü, common in filenames like
        # screenshots) — PIL reads these paths correctly, so loading through PIL and
        # passing the already-decoded image to pyautogui sidesteps the bug entirely.
        self._step_images = {}
        load_errors = []
        for step in self.steps:
            if not step.get("enabled", True):
                continue
            try:
                img = Image.open(step["path"])
                img.load()
                self._step_images[step["id"]] = img
            except Exception as e:
                load_errors.append(f"{step.get('name', '?')}: {e}")

        if load_errors:
            self._show_error_modal("TRG-003", detail="\n".join(load_errors[:6]), mode="warning")
        if not self._step_images:
            return  # nothing loadable — don't start a loop that can never click anything

        self.is_running = True
        self.is_paused = False
        self._sync_status_ui()
        self.worker_thread = threading.Thread(target=self._loop, daemon=True)
        self.worker_thread.start()

    def _toggle_pause(self):
        if not self.is_running:
            return
        self.is_paused = not self.is_paused
        self._sync_status_ui()

    def _cancel_engine(self):
        self.is_running = False
        self.is_paused = False
        self._sync_status_ui()

    def _loop(self):
        while self.is_running:
            try:
                aborted = keyboard.is_pressed("q")
            except Exception:
                aborted = False
                self.root.after(0, lambda: self._warn_once("hotkey", "TRG-005", mode="warning"))

            if aborted:
                self.root.after(0, self._cancel_engine)
                break

            if self.is_paused:
                time.sleep(0.15)
                continue

            for step in list(self.steps):
                if not self.is_running or self.is_paused:
                    break
                if not step.get("enabled", True):
                    continue
                img = self._step_images.get(step["id"])
                if img is None:
                    continue  # failed to load — already reported once at Start
                try:
                    conf = step["confidence"] if self.use_confidence else None
                    region = step.get("region")
                    region_arg = tuple(region) if region else None
                    pos = pyautogui.locateOnScreen(img, confidence=conf, region=region_arg)
                    if pos:
                        center = pyautogui.center(pos)
                        clicks = max(1, int(step.get("click_count", 1)))
                        for i in range(clicks):
                            if not self.is_running or self.is_paused:
                                break
                            pyautogui.click(center)
                            if i < clicks - 1:
                                time.sleep(0.12)
                        time.sleep(self._parse_delay_canon(step["delay"], step["unit"]))
                except Exception as e:
                    self.root.after(0, lambda err=str(e), sid=step["id"]:
                                     self._warn_once(f"step_err_{sid}", "TRG-999", detail=err, mode="warning"))

            time.sleep(0.2)


if __name__ == "__main__":
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = TriggerApp(root)
    root.mainloop()
