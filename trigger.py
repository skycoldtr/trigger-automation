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

APP_VERSION = "2.0"

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif")

UNIT_ALIASES = {
    "ms": "ms", "milisaniye": "ms",
    "sec": "sec", "saniye": "sec", "sn": "sec",
    "min": "min", "dakika": "min", "dk": "min",
}


def canon_unit(u):
    return UNIT_ALIASES.get(str(u).strip().lower(), "sec")


LANGUAGES = {
    "EN": {
        "title": "TRIGGER // Automation Engine",
        "idle": "[IDLE]",
        "armed": "[RUNNING]",
        "status_paused": "[PAUSED]",
        "disarmed": "[STOPPED]",
        "abort": "ABORT KEY: [Q]",
        "config_box": " ⚙ NEW STEP ",
        "target_lbl": "🎯 Target:",
        "name_lbl": "🏷 Step Name:",
        "browse": "📂 Browse",
        "confidence": "🎚 Confidence:",
        "delay": "⏱ Delay:",
        "add_btn": "➕ ADD STEP",
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
        "idle": "[BOŞTA]",
        "armed": "[ÇALIŞIYOR]",
        "status_paused": "[DURAKLATILDI]",
        "disarmed": "[DURDURULDU]",
        "abort": "İPTAL TUŞU: [Q]",
        "config_box": " ⚙ YENİ ADIM ",
        "target_lbl": "🎯 Hedef:",
        "name_lbl": "🏷 Adım Adı:",
        "browse": "📂 Gözat",
        "confidence": "🎚 Hassasiyet:",
        "delay": "⏱ Bekleme:",
        "add_btn": "➕ ADIM EKLE",
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
        "unit_sec": "sn",
        "unit_ms": "ms",
        "unit_min": "dk",
        "drop_hint": "📥 Görseli buraya\nsürükleyip bırakın\nya da tıklayıp seçin",
        "no_dnd_hint": "⚠ Sürükle-bırak için 'tkinterdnd2' kurun",
        "no_file": "— dosya seçilmedi —",
        "confirm_remove_title": "Silme Onayı",
        "confirm_remove_msg": "{n} adım kaldırılsın mı?",
        "rename_prompt": "Bu adım için yeni bir isim girin:",
        "no_selection": "Önce listeden en az bir adım seçin.",
        "no_selection_single": "Yeniden adlandırmak için tek bir adım seçin.",
        "toggle_ui": "🎨 Klasik Arayüz",
        "toggle_ui_modern": "🎨 Modern Arayüz",
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
        "border": "#2c2c2c", "red": "#CF6679", "entry_bg": "#2A2A2A",
        "tree_bg": "#181818", "tree_sel": "#333333", "btn_face": "#242424",
    },
    "LIGHT": {
        "bg": "#F5F5F5", "frame_bg": "#FFFFFF", "accent": "#FF5722",
        "accent_active": "#E64A19", "text": "#121212", "text_muted": "#666666",
        "border": "#CCCCCC", "red": "#D32F2F", "entry_bg": "#EEEEEE",
        "tree_bg": "#FAFAFA", "tree_sel": "#E0E0E0", "btn_face": "#EAEAEA",
    },
    "CLASSIC": {
        "bg": "#F0F0F0", "frame_bg": "#FFFFFF", "accent": "#0078D7",
        "accent_active": "#005A9E", "text": "#000000", "text_muted": "#555555",
        "border": "#ADADAD", "red": "#C42B1C", "entry_bg": "#FFFFFF",
        "tree_bg": "#FFFFFF", "tree_sel": "#CCE4F7", "btn_face": "#E1E1E1",
    },
}

PREVIEW_W, PREVIEW_H = 200, 160


class TriggerApp:
    def __init__(self, root):
        self.root = root
        self.current_lang = "EN"
        self.current_theme = "DARK"
        self.ui_mode = "MODERN"  # MODERN or CLASSIC

        self.root.title(LANGUAGES[self.current_lang]["title"])
        self._set_app_icon()          # taskbar/titlebar icon, set before the dialog so it shows there too
        self.header_logo_photo = self._load_header_logo(44)

        if not self._show_disclaimer():
            self.root.destroy()
            sys.exit()

        self.steps = []
        self.is_running = False
        self.is_paused = False
        self.worker_thread = None
        self._preview_photo = None
        self.name_var = tk.StringVar()
        self.img_path_var = tk.StringVar()

        self.root.geometry("820x860")
        self.root.minsize(700, 720)

        self._apply_styles()
        self._build_interface()

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
            "header": ("Montserrat", 14, "bold"),
            "bold": ("Montserrat", 10, "bold"),
            "main": ("Montserrat", 9, "bold"),
        }

    def _show_disclaimer(self):
        t = LANGUAGES[self.current_lang]
        return messagebox.askyesno(t["disclaimer_title"], t["disclaimer_msg"])

    def _get_t(self, key):
        return LANGUAGES[self.current_lang].get(key, "")

    def _set_app_icon(self):
        icon_names = ["icon.ico", "icon.png", "logo.ico", "logo.png"]
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        # keep a reference on the instance so this PhotoImage isn't garbage collected
        self._app_icon_photo = None
        for icon_name in icon_names:
            icon_path = os.path.join(base_path, icon_name)
            if os.path.exists(icon_path):
                try:
                    img = Image.open(icon_path)
                    photo = ImageTk.PhotoImage(img)
                    self.root.iconphoto(True, photo)
                    self._app_icon_photo = photo
                    break
                except Exception:
                    pass

    def _load_header_logo(self, size=44):
        """Loads icon.png/logo.png next to the script and scales it down for the header bar."""
        logo_names = ["icon.png", "logo.png"]
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        for logo_name in logo_names:
            logo_path = os.path.join(base_path, logo_name)
            if os.path.exists(logo_path):
                try:
                    img = Image.open(logo_path).convert("RGBA")
                    img.thumbnail((size, size), Image.LANCZOS)
                    return ImageTk.PhotoImage(img)
                except Exception:
                    return None
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

        style.configure("TSpinbox", fieldbackground=c["entry_bg"], background=c["frame_bg"],
                         foreground=c["text"], arrowcolor=c["accent"], bordercolor=c["border"],
                         darkcolor=c["entry_bg"], lightcolor=c["entry_bg"])

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
        """Themed button factory used everywhere so MODERN/CLASSIC stay consistent."""
        c = self._colors()
        f = self._fonts()
        classic = self.ui_mode == "CLASSIC"

        if kind == "accent":
            bg, fg, active = c["accent"], ("#FFFFFF" if classic else "#000000"), c["accent_active"]
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
        return b

    # ---------- interface ----------

    def _build_interface(self):
        c = self._colors()
        f = self._fonts()

        # ----- header -----
        header = tk.Frame(self.root, bg=c["frame_bg"], height=60,
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
            # graceful fallback when icon.png isn't shipped next to the script
            self.title_lbl = tk.Label(title_wrap, text="⚡ TRIGGER", font=f["header"],
                                       bg=c["frame_bg"], fg=c["accent"])
        self.title_lbl.pack(side="left")

        self.status_lbl = tk.Label(header, text="", font=f["bold"], bg=c["frame_bg"], fg=c["text_muted"])
        self.status_lbl.pack(side="left", padx=4)

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

        left = tk.Frame(self.box_config, bg=c["bg"])
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
                     font=("Segoe UI", 7), wraplength=170, justify="center").pack(pady=(4, 0))

        self.lbl_filename = tk.Label(left, text=self._get_t("no_file"), bg=c["bg"],
                                      fg=c["text_muted"], font=("Segoe UI", 8), wraplength=190)
        self.lbl_filename.pack(pady=(6, 0))

        self._update_preview(self.img_path_var.get())

        right = tk.Frame(self.box_config, bg=c["bg"])
        right.pack(side="left", fill="both", expand=True)
        right.columnconfigure(1, weight=1)

        row = 0
        tk.Label(right, text=self._get_t("name_lbl"), anchor="w", bg=c["bg"], fg=c["text"],
                 font=f["main"]).grid(row=row, column=0, sticky="w", pady=4)
        self.entry_name = tk.Entry(right, textvariable=self.name_var, bg=c["entry_bg"], fg=c["text"],
                                    insertbackground=c["text"], relief="flat", bd=1)
        self.entry_name.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=4, ipady=4)

        row += 1
        tk.Label(right, text=self._get_t("target_lbl"), anchor="w", bg=c["bg"], fg=c["text"],
                 font=f["main"]).grid(row=row, column=0, sticky="w", pady=4)
        self.entry_img = tk.Entry(right, textvariable=self.img_path_var, bg=c["entry_bg"], fg=c["text"],
                                   insertbackground=c["text"], relief="flat", bd=1, state="readonly",
                                   readonlybackground=c["entry_bg"])
        self.entry_img.grid(row=row, column=1, sticky="ew", padx=(8, 4), pady=4, ipady=4)
        self._btn(right, self._get_t("browse"), self._select_image).grid(row=row, column=2, pady=4)

        row += 1
        tk.Label(right, text=self._get_t("confidence"), anchor="w", bg=c["bg"], fg=c["text"],
                 font=f["main"]).grid(row=row, column=0, sticky="w", pady=4)
        self.conf_var = tk.DoubleVar(value=0.80)
        ttk.Spinbox(right, from_=0.5, to=0.99, increment=0.05, textvariable=self.conf_var,
                    width=8).grid(row=row, column=1, sticky="w", padx=(8, 0), pady=4)

        row += 1
        tk.Label(right, text=self._get_t("delay"), anchor="w", bg=c["bg"], fg=c["text"],
                 font=f["main"]).grid(row=row, column=0, sticky="w", pady=4)
        delay_frame = tk.Frame(right, bg=c["bg"])
        delay_frame.grid(row=row, column=1, columnspan=2, sticky="w", padx=(8, 0), pady=4)
        self.delay_val_var = tk.DoubleVar(value=1.5)
        ttk.Spinbox(delay_frame, from_=0.0, to=3600.0, increment=0.5,
                    textvariable=self.delay_val_var, width=10).pack(side="left")
        self.unit_display_map = {
            "ms": self._get_t("unit_ms"), "sec": self._get_t("unit_sec"), "min": self._get_t("unit_min")
        }
        self.delay_unit_var = tk.StringVar(value=self.unit_display_map["sec"])
        self.cb_unit = ttk.Combobox(delay_frame, textvariable=self.delay_unit_var,
                                     values=list(self.unit_display_map.values()), width=8, state="readonly")
        self.cb_unit.pack(side="left", padx=(6, 0))

        row += 1
        self._btn(right, self._get_t("add_btn"), self._add_step, kind="accent").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=(12, 2), ipady=6)

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
        bottom_bar.pack(fill="x", padx=16, pady=(8, 16))

        self._btn(bottom_bar, self._get_t("import"), self._load_profile).pack(side="left", padx=(0, 6))
        self._btn(bottom_bar, self._get_t("export"), self._save_profile).pack(side="left")

        action_frame = tk.Frame(bottom_bar, bg=c["bg"])
        action_frame.pack(side="right")
        self.btn_cancel = self._btn(action_frame, self._get_t("cancel"), self._cancel_engine, kind="danger")
        self.btn_cancel.pack(side="right", padx=(6, 0), ipady=4)
        self.btn_pause = self._btn(action_frame, self._get_t("pause"), self._toggle_pause)
        self.btn_pause.pack(side="right", padx=(6, 0), ipady=4)
        self.btn_start = self._btn(action_frame, self._get_t("start"), self._start_engine, kind="accent")
        self.btn_start.pack(side="right", ipady=4, padx=(0, 0))

        self._refresh_tree()
        self._sync_status_ui()

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
        self._rebuild()

    def _toggle_theme(self):
        self.current_theme = "LIGHT" if self.current_theme == "DARK" else "DARK"
        self._rebuild()

    def _toggle_ui_mode(self):
        self.ui_mode = "CLASSIC" if self.ui_mode == "MODERN" else "MODERN"
        self._rebuild()

    # ---------- preview / drag&drop ----------

    def _update_preview(self, path):
        c = self._colors()
        if not path or not os.path.exists(path):
            self.drop_zone.config(image="", text=self._get_t("drop_hint"))
            self.lbl_filename.config(text=self._get_t("no_file"))
            self._preview_photo = None
            return
        try:
            img = Image.open(path)
            img.thumbnail((PREVIEW_W, PREVIEW_H))
            photo = ImageTk.PhotoImage(img)
            self._preview_photo = photo
            self.drop_zone.config(image=photo, text="")
            self.lbl_filename.config(text=os.path.basename(path))
        except Exception:
            self.drop_zone.config(image="", text="⚠️")
            self.lbl_filename.config(text=self._get_t("no_file"))
            self._preview_photo = None

    def _on_drop(self, event):
        try:
            paths = self.root.tk.splitlist(event.data)
        except Exception:
            paths = [event.data]
        for p in paths:
            p = p.strip("{}")
            if p.lower().endswith(IMAGE_EXTS) and os.path.exists(p):
                self.img_path_var.set(p)
                if not self.name_var.get().strip():
                    self.name_var.set(os.path.splitext(os.path.basename(p))[0])
                self._update_preview(p)
                return

    def _select_image(self):
        f = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif")])
        if f:
            self.img_path_var.set(f)
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
                        s["confidence"], s["delay"], unit_display.get(canon_unit(s.get("unit", "sec")), "sec")),
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

    def _add_step(self):
        path = self.img_path_var.get().strip()
        if not path:
            messagebox.showwarning("Warning", self._get_t("warn_no_image"))
            return

        name = self.name_var.get().strip() or os.path.splitext(os.path.basename(path))[0]
        display_unit = self.delay_unit_var.get()
        reverse_map = {v: k for k, v in self.unit_display_map.items()}
        unit = reverse_map.get(display_unit, "sec")

        step = {
            "id": uuid.uuid4().hex,
            "name": name,
            "path": path,
            "confidence": round(float(self.conf_var.get()), 2),
            "delay": float(self.delay_val_var.get()),
            "unit": unit,
            "enabled": True,
        }
        self.steps.append(step)
        self._refresh_tree()
        self._center_tree_item(step["id"])

        self.name_var.set("")
        self.img_path_var.set("")
        self._update_preview("")

    def _on_tree_select(self, event=None):
        sel = self.tree.selection()
        if len(sel) == 1:
            step = self._find_step(sel[0])
            if step:
                self._update_preview(step["path"])

    def _on_tree_double_click(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return
        step = self._find_step(row)
        if step:
            step["enabled"] = not step.get("enabled", True)
            self._refresh_tree()
            self.tree.selection_set(row)

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
        self.steps = [s for s in self.steps if s["id"] not in ids_to_remove]
        self._refresh_tree()

    def _show_context_menu(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            if row not in self.tree.selection():
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

        normalized = []
        for s in loaded:
            normalized.append({
                "id": s.get("id") or uuid.uuid4().hex,
                "name": s.get("name") or os.path.splitext(os.path.basename(s.get("path", "step")))[0],
                "path": s.get("path", ""),
                "confidence": float(s.get("confidence", 0.8)),
                "delay": float(s.get("delay", 1.0)),
                "unit": canon_unit(s.get("unit", "sec")),
                "enabled": bool(s.get("enabled", True)),
            })
        self.steps = normalized
        self._refresh_tree()

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
            self.status_lbl.config(text=self._get_t("armed"), fg=c["accent"])
            self.btn_start.config(state="disabled")
            self.btn_pause.config(state="normal", text=self._get_t("pause"))
            self.btn_cancel.config(state="normal")
        elif self.is_running and self.is_paused:
            self.status_lbl.config(text=self._get_t("status_paused"), fg=c["text_muted"])
            self.btn_start.config(state="disabled")
            self.btn_pause.config(state="normal", text=self._get_t("resume"))
            self.btn_cancel.config(state="normal")
        else:
            self.status_lbl.config(text=self._get_t("idle"), fg=c["text_muted"])
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
