import os
import json
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

import pyautogui
import keyboard

pyautogui.PAUSE = 0.15

LANGUAGES = {
    "EN": {
        "title": "TRIGGER // Automation Engine",
        "idle": "[IDLE]",
        "armed": "[ARMED]",
        "disarmed": "[DISARMED]",
        "abort": "ABORT: [Q]",
        "config_box": " TRIGGER CONFIG ",
        "target_lbl": "Target Img:",
        "browse": "Browse",
        "confidence": "Confidence:",
        "delay": "Delay:",
        "add_btn": "+ ADD SEQUENCE",
        "queue_box": " SEQUENCE QUEUE ",
        "col_target": "TARGET FILE",
        "col_conf": "CONF",
        "col_delay": "DELAY",
        "col_unit": "UNIT",
        "remove": "Remove Selected",
        "import": "Import Profile",
        "export": "Export Profile",
        "arm": "ARM TRIGGER",
        "disarm": "DISARM TRIGGER",
        "warn_empty": "Queue is empty.",
        "unit_sec": "sec",
        "unit_ms": "ms",
        "unit_min": "min",
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
        "disarmed": "[DURDURULDU]",
        "abort": "İPTAL: [Q]",
        "config_box": " AYARLAR ",
        "target_lbl": "Hedef Görsel:",
        "browse": "Gözat",
        "confidence": "Hassasiyet:",
        "delay": "Bekleme:",
        "add_btn": "+ ADIM EKLE",
        "queue_box": " İŞLEM LİSTESİ ",
        "col_target": "HEDEF DOSYA",
        "col_conf": "HASSASİYET",
        "col_delay": "SÜRE",
        "col_unit": "BİRİM",
        "remove": "Seçileni Sil",
        "import": "Profil Yükle",
        "export": "Profil Kaydet",
        "arm": "BAŞLAT",
        "disarm": "DURDUR",
        "warn_empty": "Liste boş.",
        "unit_sec": "sn",
        "unit_ms": "ms",
        "unit_min": "dk",
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
        "bg": "#121212",
        "frame_bg": "#1e1e1e",
        "accent": "#FF5722",
        "accent_active": "#E64A19",
        "text": "#FFFFFF",
        "text_muted": "#888888",
        "border": "#2c2c2c",
        "red": "#CF6679",
        "entry_bg": "#2A2A2A",
        "tree_bg": "#181818",
        "tree_sel": "#333333"
    },
    "LIGHT": {
        "bg": "#F5F5F5",
        "frame_bg": "#FFFFFF",
        "accent": "#FF5722",
        "accent_active": "#E64A19",
        "text": "#121212",
        "text_muted": "#666666",
        "border": "#CCCCCC",
        "red": "#D32F2F",
        "entry_bg": "#EEEEEE",
        "tree_bg": "#FAFAFA",
        "tree_sel": "#E0E0E0"
    }
}

FONT_MAIN = ("Montserrat", 9, "bold")
FONT_BOLD = ("Montserrat", 10, "bold")
FONT_HEADER = ("Montserrat", 14, "bold")


class TriggerApp:
    def __init__(self, root):
        self.root = root
        self.current_lang = "EN"
        self.current_theme = "DARK"
        
        if not self._show_disclaimer():
            self.root.destroy()
            sys.exit()

        self.steps = []
        self.is_running = False
        self.worker_thread = None

        self.root.title(LANGUAGES[self.current_lang]["title"])
        
        self.root.geometry("720x780")
        self.root.minsize(640, 680)

        self._set_app_icon()
        self._apply_styles()
        self._build_interface()

    def _show_disclaimer(self):
        t = LANGUAGES[self.current_lang]
        return messagebox.askyesno(t["disclaimer_title"], t["disclaimer_msg"])

    def _get_t(self, key):
        return LANGUAGES[self.current_lang].get(key, "")

    def _set_app_icon(self):
        icon_names = ["icon.ico", "icon.png", "logo.ico", "logo.png"]
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))

        for icon_name in icon_names:
            icon_path = os.path.join(base_path, icon_name)
            if os.path.exists(icon_path):
                try:
                    img = Image.open(icon_path)
                    photo = ImageTk.PhotoImage(img)
                    self.root.iconphoto(True, photo)
                    break
                except Exception:
                    pass

    def _apply_styles(self):
        c = THEMES[self.current_theme]
        self.root.configure(bg=c["bg"])

        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=c["bg"], foreground=c["text"], font=FONT_MAIN)
        style.configure("TFrame", background=c["bg"])
        style.configure("TLabelframe", background=c["bg"], foreground=c["accent"], borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label", background=c["bg"], foreground=c["accent"], font=FONT_BOLD)
        style.configure("TLabel", background=c["bg"], foreground=c["text"], font=FONT_MAIN)
        
        style.configure("TSpinbox", 
                        fieldbackground=c["entry_bg"], 
                        background=c["frame_bg"], 
                        foreground=c["text"], 
                        arrowcolor=c["accent"],
                        bordercolor=c["border"],
                        darkcolor=c["entry_bg"],
                        lightcolor=c["entry_bg"])

        style.configure("TCombobox", 
                        fieldbackground=c["entry_bg"], 
                        background=c["frame_bg"], 
                        foreground=c["text"], 
                        arrowcolor=c["accent"],
                        bordercolor=c["border"],
                        darkcolor=c["entry_bg"],
                        lightcolor=c["entry_bg"])
        
        style.map("TCombobox", 
                  fieldbackground=[("readonly", c["entry_bg"])],
                  foreground=[("readonly", c["text"])])

        style.configure("Treeview", 
                        background=c["tree_bg"], 
                        foreground=c["text"], 
                        fieldbackground=c["tree_bg"], 
                        rowheight=32,
                        borderwidth=0,
                        font=FONT_MAIN)
        style.configure("Treeview.Heading", 
                        background=c["frame_bg"], 
                        foreground=c["accent"], 
                        font=FONT_BOLD, 
                        relief="flat")
        style.map("Treeview", background=[("selected", c["tree_sel"])])

    def _build_interface(self):
        c = THEMES[self.current_theme]

        header = tk.Frame(self.root, bg=c["frame_bg"], height=60, highlightthickness=1, highlightbackground=c["border"])
        header.pack(fill="x", padx=16, pady=(16, 8))
        header.pack_propagate(False)

        self.title_lbl = tk.Label(header, text="TRIGGER", font=FONT_HEADER, bg=c["frame_bg"], fg=c["accent"])
        self.title_lbl.pack(side="left", padx=16)

        self.status_lbl = tk.Label(header, text=self._get_t("idle"), font=FONT_BOLD, bg=c["frame_bg"], fg=c["text_muted"])
        self.status_lbl.pack(side="left", padx=4)

        self.abort_lbl = tk.Label(header, text=self._get_t("abort"), font=FONT_BOLD, bg=c["frame_bg"], fg=c["red"])
        self.abort_lbl.pack(side="right", padx=16)

        self.btn_theme = tk.Button(header, text="🌙" if self.current_theme == "DARK" else "☀️", command=self._toggle_theme, bg=c["bg"], fg=c["text"], relief="flat", padx=8, font=("Segoe UI Emoji", 10))
        self.btn_theme.pack(side="right", padx=4)

        self.btn_lang = tk.Button(header, text=self.current_lang, command=self._toggle_language, bg=c["bg"], fg=c["accent"], relief="flat", padx=10, font=FONT_BOLD)
        self.btn_lang.pack(side="right", padx=4)

        self.box_config = ttk.LabelFrame(self.root, text=self._get_t("config_box"), padding=12)
        self.box_config.pack(fill="x", padx=16, pady=8)

        r1 = tk.Frame(self.box_config, bg=c["bg"])
        r1.pack(fill="x", pady=6)
        self.lbl_target = tk.Label(r1, text=self._get_t("target_lbl"), width=12, anchor="w", bg=c["bg"], fg=c["text"])
        self.lbl_target.pack(side="left")

        self.img_path_var = tk.StringVar()
        self.entry_img = tk.Entry(r1, textvariable=self.img_path_var, bg=c["entry_bg"], fg=c["text"], insertbackground=c["text"], relief="flat", bd=1)
        self.entry_img.pack(side="left", fill="x", expand=True, padx=6, ipady=4)

        self.btn_browse = tk.Button(r1, text=self._get_t("browse"), command=self._select_image, bg=c["frame_bg"], fg=c["text"], activebackground=c["border"], relief="flat", font=FONT_MAIN, padx=12, pady=2)
        self.btn_browse.pack(side="right")

        r2 = tk.Frame(self.box_config, bg=c["bg"])
        r2.pack(fill="x", pady=8)

        self.lbl_conf = tk.Label(r2, text=self._get_t("confidence"), width=12, anchor="w", bg=c["bg"], fg=c["text"])
        self.lbl_conf.pack(side="left")
        
        self.conf_var = tk.DoubleVar(value=0.80)
        self.sp_conf = ttk.Spinbox(r2, from_=0.5, to=0.99, increment=0.05, textvariable=self.conf_var, width=8)
        self.sp_conf.pack(side="left", padx=6)

        self.lbl_delay = tk.Label(r2, text=self._get_t("delay"), width=12, anchor="e", bg=c["bg"], fg=c["text"])
        self.lbl_delay.pack(side="left", padx=(12, 6))
        
        self.delay_val_var = tk.DoubleVar(value=1.5)
        self.sp_delay = ttk.Spinbox(r2, from_=0.0, to=3600.0, increment=0.5, textvariable=self.delay_val_var, width=10)
        self.sp_delay.pack(side="left", padx=6)

        self.delay_unit_var = tk.StringVar(value=self._get_t("unit_sec"))
        self.cb_unit = ttk.Combobox(r2, textvariable=self.delay_unit_var, values=[self._get_t("unit_ms"), self._get_t("unit_sec"), self._get_t("unit_min")], width=8, state="readonly")
        self.cb_unit.pack(side="left", padx=6)

        self.btn_add = tk.Button(self.box_config, text=self._get_t("add_btn"), command=self._add_step, bg=c["accent"], fg="#000000", activebackground=c["accent_active"], font=FONT_BOLD, relief="flat", pady=8)
        self.btn_add.pack(fill="x", pady=(10, 2))

        self.box_queue = ttk.LabelFrame(self.root, text=self._get_t("queue_box"), padding=12)
        self.box_queue.pack(fill="both", expand=True, padx=16, pady=8)

        cols = ("#1", "#2", "#3", "#4")
        self.tree = ttk.Treeview(self.box_queue, columns=cols, show="headings")
        self._update_table_headings()

        self.tree.column("#1", width=320)
        self.tree.column("#2", width=90, anchor="center")
        self.tree.column("#3", width=90, anchor="center")
        self.tree.column("#4", width=80, anchor="center")
        self.tree.pack(fill="both", expand=True)

        self.btn_del = tk.Button(self.box_queue, text=self._get_t("remove"), command=self._remove_step, bg=c["frame_bg"], fg=c["red"], activebackground=c["border"], relief="flat", font=FONT_MAIN, pady=4)
        self.btn_del.pack(anchor="e", pady=(8, 0))

        bottom_bar = tk.Frame(self.root, bg=c["bg"])
        bottom_bar.pack(fill="x", padx=16, pady=(8, 16))

        self.btn_load = tk.Button(bottom_bar, text=self._get_t("import"), command=self._load_profile, bg=c["frame_bg"], fg=c["text"], relief="flat", padx=16, pady=6)
        self.btn_load.pack(side="left", padx=(0, 6))

        self.btn_save = tk.Button(bottom_bar, text=self._get_t("export"), command=self._save_profile, bg=c["frame_bg"], fg=c["text"], relief="flat", padx=16, pady=6)
        self.btn_save.pack(side="left")

        self.btn_toggle = tk.Button(bottom_bar, text=self._get_t("arm"), command=self._toggle_engine, bg=c["accent"], fg="#000000", font=FONT_BOLD, relief="flat", padx=24, pady=6)
        self.btn_toggle.pack(side="right")

    def _update_table_headings(self):
        self.tree.heading("#1", text=self._get_t("col_target"))
        self.tree.heading("#2", text=self._get_t("col_conf"))
        self.tree.heading("#3", text=self._get_t("col_delay"))
        self.tree.heading("#4", text=self._get_t("col_unit"))

    def _toggle_language(self):
        self.current_lang = "TR" if self.current_lang == "EN" else "EN"
        self.btn_lang.config(text=self.current_lang)
        self.root.title(self._get_t("title"))
        
        self.status_lbl.config(text=self._get_t("armed") if self.is_running else self._get_t("idle"))
        self.abort_lbl.config(text=self._get_t("abort"))
        self.box_config.config(text=self._get_t("config_box"))
        self.lbl_target.config(text=self._get_t("target_lbl"))
        self.btn_browse.config(text=self._get_t("browse"))
        self.lbl_conf.config(text=self._get_t("confidence"))
        self.lbl_delay.config(text=self._get_t("delay"))
        self.btn_add.config(text=self._get_t("add_btn"))
        self.box_queue.config(text=self._get_t("queue_box"))
        self.btn_del.config(text=self._get_t("remove"))
        self.btn_load.config(text=self._get_t("import"))
        self.btn_save.config(text=self._get_t("export"))
        self.btn_toggle.config(text=self._get_t("disarm") if self.is_running else self._get_t("arm"))
        
        self.cb_unit.config(values=[self._get_t("unit_ms"), self._get_t("unit_sec"), self._get_t("unit_min")])
        self.delay_unit_var.set(self._get_t("unit_sec"))
        self._update_table_headings()

    def _toggle_theme(self):
        self.current_theme = "LIGHT" if self.current_theme == "DARK" else "DARK"
        self.btn_theme.config(text="🌙" if self.current_theme == "DARK" else "☀️")
        
        self._apply_styles()
        
        for widget in self.root.winfo_children():
            widget.destroy()
        self._build_interface()

    def _select_image(self):
        f = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if f:
            self.img_path_var.set(f)

    def _add_step(self):
        path = self.img_path_var.get().strip()
        if not path:
            return

        step = {
            "path": path,
            "confidence": self.conf_var.get(),
            "delay": self.delay_val_var.get(),
            "unit": self.delay_unit_var.get()
        }

        self.steps.append(step)
        self.tree.insert("", "end", values=(os.path.basename(path), step["confidence"], step["delay"], step["unit"]))
        self.img_path_var.set("")

    def _remove_step(self):
        selected = self.tree.selection()
        if not selected:
            return
        for item in selected:
            idx = self.tree.index(item)
            del self.steps[idx]
            self.tree.delete(item)

    def _save_profile(self):
        if not self.steps:
            return
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Config", "*.json")])
        if f:
            with open(f, "w", encoding="utf-8") as out:
                json.dump(self.steps, out, indent=2)

    def _load_profile(self):
        f = filedialog.askopenfilename(filetypes=[("JSON Config", "*.json")])
        if f:
            with open(f, "r", encoding="utf-8") as inp:
                self.steps = json.load(inp)

            self.tree.delete(*self.tree.get_children())
            for s in self.steps:
                self.tree.insert("", "end", values=(os.path.basename(s["path"]), s["confidence"], s["delay"], s["unit"]))

    def _parse_delay(self, val, unit):
        if unit in ["ms", "ms"]:
            return val / 1000.0
        elif unit in ["min", "dk"]:
            return val * 60.0
        return val

    def _toggle_engine(self):
        c = THEMES[self.current_theme]
        if not self.is_running:
            if not self.steps:
                messagebox.showwarning("Warning", self._get_t("warn_empty"))
                return
            self.is_running = True
            self.btn_toggle.config(text=self._get_t("disarm"), bg=c["red"], fg="#FFFFFF")
            self.status_lbl.config(text=self._get_t("armed"), fg=c["accent"])
            self.worker_thread = threading.Thread(target=self._loop, daemon=True)
            self.worker_thread.start()
        else:
            self._stop_engine()

    def _stop_engine(self):
        c = THEMES[self.current_theme]
        self.is_running = False
        self.btn_toggle.config(text=self._get_t("arm"), bg=c["accent"], fg="#000000")
        self.status_lbl.config(text=self._get_t("disarmed"), fg=c["red"])

    def _loop(self):
        while self.is_running:
            if keyboard.is_pressed("q"):
                self.root.after(0, self._stop_engine)
                break

            for step in self.steps:
                if not self.is_running:
                    break

                try:
                    pos = pyautogui.locateOnScreen(step["path"], confidence=step["confidence"])
                    if pos:
                        center = pyautogui.center(pos)
                        pyautogui.click(center)
                        time.sleep(self._parse_delay(step["delay"], step["unit"]))
                except Exception:
                    pass

            time.sleep(0.2)


if __name__ == "__main__":
    root = tk.Tk()
    app = TriggerApp(root)
    root.mainloop()