import os
import sys
import json
import time
import uuid
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk

import pyautogui
import keyboard

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

pyautogui.PAUSE = 0.15
pyautogui.FAILSAFE = True

APP_VERSION = "3.2"

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif")

UNIT_ALIASES = {
    "ms": "ms", "milisaniye": "ms",
    "sec": "sec", "saniye": "sec", "sn": "sec",
    "min": "min", "dakika": "min", "dk": "min",
}


def canon_unit(u):
    return UNIT_ALIASES.get(str(u).strip().lower(), "sec")


CHANGELOG = {
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
    }
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
        "drop_hint": "📥 Drag & drop\nan image here\nor click to browse",
        "no_dnd_hint": "⚠ Install 'tkinterdnd2' to enable drag & drop",
        "no_file": "— no file selected —",
        "confirm_remove_title": "Confirm Removal",
        "confirm_remove_msg": "Remove {n} selected step(s)?",
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
        "drop_hint": "📥 Görseli buraya\nsürükleyip bırakın\nya da tıklayıp seçin",
        "no_dnd_hint": "⚠ Sürükle-bırak için 'tkinterdnd2' kurun",
        "no_file": "— dosya seçilmedi —",
        "confirm_remove_title": "Silme Onayı",
        "confirm_remove_msg": "{n} adım kaldırılsın mı?",
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
        "bg": "#121212", "frame_bg": "#1e1e1e", "accent": "#FF5722",
        "accent_active": "#E64A19", "text": "#FFFFFF", "text_muted": "#888888",
        "border": "#2c2c2c", "red": "#CF6679", "green": "#4CAF50", "entry_bg": "#2A2A2A",
        "tree_bg": "#181818", "tree_sel": "#333333", "btn_face": "#242424",
    },
    "LIGHT": {
        "bg": "#F5F5F5", "frame_bg": "#FFFFFF", "accent": "#FF5722",
        "accent_active": "#E64A19", "text": "#121212", "text_muted": "#666666",
        "border": "#CCCCCC", "red": "#D32F2F", "green": "#2E7D32", "entry_bg": "#EEEEEE",
        "tree_bg": "#FAFAFA", "tree_sel": "#E0E0E0", "btn_face": "#EAEAEA",
    },
    "CLASSIC": {
        "bg": "#F0F0F0", "frame_bg": "#FFFFFF", "accent": "#0078D7",
        "accent_active": "#005A9E", "text": "#000000", "text_muted": "#555555",
        "border": "#ADADAD", "red": "#C42B1C", "green": "#107C10", "entry_bg": "#FFFFFF",
        "tree_bg": "#FFFFFF", "tree_sel": "#CCE4F7", "btn_face": "#E1E1E1",
    },
}

PREVIEW_W, PREVIEW_H = 200, 160


class TriggerApp:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()

        self.settings = self._load_settings_dict()
        self.current_lang = self.settings.get("lang", "EN")
        self.current_theme = self.settings.get("theme", "DARK")
        self.ui_mode = self.settings.get("ui_mode", "MODERN")

        self.steps = self._normalize_steps(self.settings.get("queue", []))
        self.editing_id = None
        self.is_running = False
        self.is_paused = False
        self.worker_thread = None
        self._preview_photo = None
        self._splash_photo = None

        self.name_var = tk.StringVar()
        self.img_path_var = tk.StringVar()
        self.img_display_var = tk.StringVar(value=self._get_t("no_file"))
        self.conf_var = tk.StringVar(value="0.80")
        self.delay_val_var = tk.StringVar(value="1.5")

        self.root.title(self._get_t("title"))
        self._set_app_icon()
        self.header_logo_photo = self._load_header_logo(44)

        self._show_splash(on_done=self._post_splash)

    # ---------- settings / persistence ----------

    def _settings_path(self):
        d = os.path.join(os.path.expanduser("~"), ".trigger")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, "settings.json")

    def _load_settings_dict(self):
        try:
            with open(self._settings_path(), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_settings_dict(self):
        self.settings["lang"] = self.current_lang
        self.settings["theme"] = self.current_theme
        self.settings["ui_mode"] = self.ui_mode
        self.settings["queue"] = self.steps
        try:
            with open(self._settings_path(), "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _normalize_steps(self, loaded):
        normalized = []
        for s in loaded:
            path = s.get("path", "")
            normalized.append({
                "id": s.get("id") or uuid.uuid4().hex,
                "name": s.get("name") or os.path.splitext(os.path.basename(path))[0] or "Step",
                "path": path,
                "confidence": float(s.get("confidence", 0.8)),
                "delay": float(s.get("delay", 1.0)),
                "unit": canon_unit(s.get("unit", "sec")),
                "enabled": bool(s.get("enabled", True)),
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
        splash = tk.Toplevel(self.root)
        self._splash = splash
        splash.overrideredirect(True)
        splash.configure(bg="#0d0d0d")
        w, h = 420, 460
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
                img.thumbnail((150, 150), Image.LANCZOS)
                self._splash_photo = ImageTk.PhotoImage(img)
            except Exception:
                self._splash_photo = None

        tk.Frame(splash, bg="#0d0d0d", height=64).pack()
        if self._splash_photo:
            tk.Label(splash, image=self._splash_photo, bg="#0d0d0d").pack()
        else:
            tk.Label(splash, text="⚡", font=("Segoe UI Emoji", 48), bg="#0d0d0d", fg="#FF5722").pack()

        tk.Label(splash, text="TRIGGER", font=("Segoe UI", 24, "bold"),
                 fg="#FF5722", bg="#0d0d0d").pack(pady=(18, 0))
        tk.Label(splash, text="A U T O M A T I O N   E N G I N E", font=("Segoe UI", 8),
                 fg="#888888", bg="#0d0d0d").pack(pady=(4, 30))

        bar_bg = tk.Canvas(splash, width=260, height=4, bg="#232323", highlightthickness=0)
        bar_bg.pack()
        bar_fill = bar_bg.create_rectangle(0, 0, 0, 4, fill="#FF5722", width=0)

        state = {"alpha": 0.0, "tick": 0}

        def fade_in():
            state["alpha"] = min(1.0, state["alpha"] + 0.08)
            try:
                splash.attributes("-alpha", state["alpha"])
            except tk.TclError:
                pass
            if state["alpha"] < 1.0:
                splash.after(15, fade_in)
            else:
                animate_bar()

        def animate_bar():
            state["tick"] += 1
            pos = (state["tick"] * 7) % 340 - 80
            bar_bg.coords(bar_fill, pos, 0, pos + 80, 4)
            if state["tick"] < 42:
                splash.after(16, animate_bar)
            else:
                fade_out()

        def fade_out():
            state["alpha"] = max(0.0, state["alpha"] - 0.09)
            try:
                splash.attributes("-alpha", state["alpha"])
            except tk.TclError:
                pass
            if state["alpha"] > 0.0:
                splash.after(15, fade_out)
            else:
                splash.destroy()
                on_done()

        splash.after(50, fade_in)

    def _post_splash(self):
        if not self._show_disclaimer():
            self.root.destroy()
            sys.exit()

        self._maybe_show_changelog()

        self.root.geometry("1000x920")
        self.root.minsize(900, 820)
        self._apply_styles()
        self._build_interface()
        self.root.deiconify()

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
        title_row.pack(anchor="w", padx=24, pady=(24, 12), fill="x")
        if self.header_logo_photo is not None:
            tk.Label(title_row, image=self.header_logo_photo, bg=c["frame_bg"]).pack(side="left", padx=(0, 10))
        tk.Label(title_row, text=self._get_t("disclaimer_title"), font=f["header"],
                 bg=c["frame_bg"], fg=c["accent"], wraplength=440, justify="left") \
            .pack(side="left", anchor="w")

        btn_row = tk.Frame(dlg, bg=c["frame_bg"])
        btn_row.pack(side="bottom", fill="x", padx=24, pady=(8, 20))
        self._btn(btn_row, "✅ " + self._get_t("accept_btn"), accept, kind="accent").pack(
            side="left", fill="x", expand=True, ipady=8, padx=(0, 6))
        self._btn(btn_row, "✖ " + self._get_t("decline_btn"), decline, kind="danger").pack(
            side="left", fill="x", expand=True, ipady=8, padx=(6, 0))

        self._build_scrollable_dialog_body(dlg, self._get_t("disclaimer_msg"), c, f, width=560, height=580)

        dlg.bind("<Escape>", lambda e: decline())
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

        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.focus_force()
        dlg.grab_set()
        self.root.wait_window(dlg)

    def _build_scrollable_dialog_body(self, dlg, text, c, f, width=480, height=620):
        """Packs a scrollable text body into dlg. The window is given a fixed, generous
        size UP FRONT (rather than trying to measure the content's natural height, which
        is unreliable for canvas-based scroll areas and previously left the bottom button
        pushed outside the visible window). Content that doesn't fit simply scrolls, so
        the OK/Accept button is always guaranteed to be visible."""
        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        h = min(height, int(sh * 0.85))
        x, y = (sw - width) // 2, (sh - h) // 2
        dlg.geometry(f"{width}x{h}+{x}+{y}")

        body_wrap = tk.Frame(dlg, bg=c["frame_bg"])
        body_wrap.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        canvas = tk.Canvas(body_wrap, bg=c["frame_bg"], highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(body_wrap, orient="vertical", command=canvas.yview)
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

    # ---------- helpers ----------

    def _colors(self):
        if self.ui_mode == "CLASSIC":
            return THEMES["CLASSIC"]
        return THEMES[self.current_theme]

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
                         rowheight=(24 if self.ui_mode == "CLASSIC" else 32),
                         borderwidth=0, font=f["main"])
        style.configure("Treeview.Heading", background=c["frame_bg"], foreground=c["accent"],
                         font=f["bold"], relief="flat")
        style.map("Treeview", background=[("selected", c["tree_sel"])])

    def _btn(self, parent, text, command, kind="normal", **kw):
        c = self._colors()
        f = self._fonts()
        classic = self.ui_mode == "CLASSIC"

        if kind == "accent":
            bg, fg, active = c["accent"], ("#FFFFFF" if classic else "#000000"), c["accent_active"]
        elif kind == "danger":
            bg, fg, active = c["entry_bg"], c["red"], c["border"]
        else:
            bg, fg, active = (c["btn_face"] if classic else c["frame_bg"]), c["text"], c["border"]

        b = tk.Button(
            parent, text=text, command=command, bg=bg, fg=fg, activebackground=active,
            activeforeground=fg, relief=("raised" if classic else "flat"),
            bd=(1 if classic else 0), font=f["bold"] if kind == "accent" else f["main"],
            cursor="hand2", **kw
        )
        return b

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
        self._btn(right, self._get_t("browse"), self._select_image).grid(row=row, column=2, pady=5)

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
        btn_row = tk.Frame(right, bg=c["bg"])
        btn_row.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(14, 2))
        self.btn_add = self._btn(btn_row, self._get_t("add_btn"), self._save_step, kind="accent")
        self.btn_add.pack(side="left", fill="x", expand=True, ipady=7)
        self.btn_cancel_edit = self._btn(btn_row, self._get_t("cancel_edit"), self._clear_form, kind="danger")

        # ----- queue box -----
        self.box_queue = ttk.LabelFrame(self.root, text=self._get_t("queue_box"), padding=12)
        self.box_queue.pack(fill="both", expand=True, padx=16, pady=8)

        cols = ("#1", "#2", "#3", "#4", "#5", "#6")
        self.tree = ttk.Treeview(self.box_queue, columns=cols, show="headings")
        self._update_table_headings()
        self.tree.column("#1", width=36, anchor="center")
        self.tree.column("#2", width=150)
        self.tree.column("#3", width=190)
        self.tree.column("#4", width=70, anchor="center")
        self.tree.column("#5", width=70, anchor="center")
        self.tree.column("#6", width=60, anchor="center")
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

        # ----- bottom bar -----
        bottom_bar = tk.Frame(self.root, bg=c["bg"])
        bottom_bar.pack(fill="x", padx=16, pady=(4, 4))

        self._btn(bottom_bar, self._get_t("import"), self._load_profile).pack(side="left", padx=(0, 6))
        self._btn(bottom_bar, self._get_t("export"), self._save_profile).pack(side="left")

        action_frame = tk.Frame(bottom_bar, bg=c["bg"])
        action_frame.pack(side="right")
        self.btn_cancel = self._btn(action_frame, self._get_t("cancel"), self._cancel_engine, kind="danger")
        self.btn_cancel.pack(side="right", padx=(6, 0), ipady=4)
        self.btn_pause = self._btn(action_frame, self._get_t("pause"), self._toggle_pause)
        self.btn_pause.pack(side="right", padx=(6, 0), ipady=4)
        self.btn_start = self._btn(action_frame, self._get_t("start"), self._start_engine, kind="accent")
        self.btn_start.pack(side="right", ipady=4)

        footer = tk.Label(self.root, text=f"TRIGGER v{APP_VERSION}", font=("Segoe UI", 8),
                           bg=c["bg"], fg=c["text_muted"])
        footer.pack(pady=(0, 10))

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

    # ---------- toggles (rebuild-safe) ----------

    def _rebuild(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self._apply_styles()
        self._build_interface()

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

    # ---------- queue management ----------

    def _find_step(self, iid):
        return next((s for s in self.steps if s["id"] == iid), None)

    def _refresh_tree(self):
        c = self._colors()
        self.tree.delete(*self.tree.get_children())
        unit_display = {
            "ms": self._get_t("unit_ms"), "sec": self._get_t("unit_sec"), "min": self._get_t("unit_min")
        }
        for s in self.steps:
            icon = "✅" if s.get("enabled", True) else "⛔"
            self.tree.insert(
                "", "end", iid=s["id"],
                values=(icon, s.get("name", "Step"), os.path.basename(s["path"]),
                        f'{s["confidence"]:.2f}', s["delay"], unit_display.get(canon_unit(s.get("unit", "sec")), "sec")),
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
            messagebox.showwarning("Warning", self._get_t("warn_no_image"))
            return None

        name = self.name_var.get().strip() or os.path.splitext(os.path.basename(path))[0]

        raw_conf = self.conf_var.get()
        conf = self._to_float(raw_conf, 0.8)
        bad_input = (self._to_float(raw_conf, None) is None) or (self._to_float(self.delay_val_var.get(), None) is None)
        conf = min(max(conf, 0.1), 1.0)

        delay = max(self._to_float(self.delay_val_var.get(), 1.0), 0.0)

        display_unit = self.delay_unit_var.get()
        reverse_map = {v: k for k, v in self.unit_display_map.items()}
        unit = reverse_map.get(display_unit, "sec")

        if bad_input:
            messagebox.showwarning("Warning", self._get_t("warn_bad_number"))

        return {
            "id": existing_id or uuid.uuid4().hex,
            "name": name, "path": path,
            "confidence": round(conf, 2), "delay": delay, "unit": unit,
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
        self._sync_edit_ui()

    def _sync_edit_ui(self):
        if self.editing_id:
            step = self._find_step(self.editing_id)
            name = step.get("name", "") if step else ""
            self.editing_hint_lbl.config(text=self._get_t("editing_hint").format(name=name))
            self.btn_add.config(text=self._get_t("update_btn"))
            self.btn_cancel_edit.pack(side="left", padx=(6, 0), ipady=7)
        else:
            self.editing_hint_lbl.config(text="")
            self.btn_add.config(text=self._get_t("add_btn"))
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
            messagebox.showinfo("Info", self._get_t("no_selection"))
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
            messagebox.showinfo("Info", self._get_t("no_selection_single"))
            return
        step = self._find_step(sel[0])
        if not step:
            return
        new_name = simpledialog.askstring(
            self._get_t("rename_sel"), self._get_t("rename_prompt"), initialvalue=step.get("name", "")
        )
        if new_name and new_name.strip():
            step["name"] = new_name.strip()
            self._refresh_tree()
            self.tree.selection_set(sel[0])
            self._save_settings_dict()

    def _remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info", self._get_t("no_selection"))
            return
        if not messagebox.askyesno(
            self._get_t("confirm_remove_title"),
            self._get_t("confirm_remove_msg").format(n=len(sel))
        ):
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
            messagebox.showerror("Error", str(e))
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
            self.btn_start.config(state="disabled")
            self.btn_pause.config(state="normal", text=self._get_t("pause"))
            self.btn_cancel.config(state="normal")
        elif self.is_running and self.is_paused:
            self.status_lbl.config(text="⏸ " + self._get_t("status_paused"), bg=c["entry_bg"], fg=c["accent"])
            self.btn_start.config(state="disabled")
            self.btn_pause.config(state="normal", text=self._get_t("resume"))
            self.btn_cancel.config(state="normal")
        else:
            self.status_lbl.config(text="○ " + self._get_t("idle"), bg=c["btn_face"], fg=c["text_muted"])
            self.btn_start.config(state="normal")
            self.btn_pause.config(state="disabled", text=self._get_t("pause"))
            self.btn_cancel.config(state="disabled")

    def _start_engine(self):
        if not any(s.get("enabled", True) for s in self.steps):
            messagebox.showwarning("Warning", self._get_t("warn_empty"))
            return
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
            if keyboard.is_pressed("q"):
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
                try:
                    pos = pyautogui.locateOnScreen(step["path"], confidence=step["confidence"])
                    if pos:
                        center = pyautogui.center(pos)
                        pyautogui.click(center)
                        time.sleep(self._parse_delay_canon(step["delay"], step["unit"]))
                except Exception:
                    pass

            time.sleep(0.2)


if __name__ == "__main__":
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = TriggerApp(root)
    root.mainloop()
