<div align="center">

# ⚡ TRIGGER
### Automation Engine

A desktop automation tool that uses image recognition to trigger clicks and keystrokes — built with Python & PyAutoGUI.

![Platform](https://img.shields.io/badge/platform-Windows-0078D7?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10%2B-FF5722?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-888888?style=flat-square)
![Status](https://img.shields.io/badge/status-active-4CAF50?style=flat-square)

</div>

---

## ⚠️ Disclaimer — Please Read Before Using

**TRIGGER is a general-purpose automation utility, not a cheat, hack, or bot designed to bypass any specific software's rules.**

- It works purely through **image recognition on your screen** — it does not read, modify, or inject anything into any other process's memory, files, or network traffic.
- You are solely responsible for how you use this tool, and for making sure that use complies with the terms of service of whatever software or platform you use it with.
- **The developer(s) provide this software "as is," with no warranty of any kind, and accept no responsibility or liability** for bans, data loss, system issues, or any other consequence resulting from the use or misuse of this application. By downloading, building, or running TRIGGER, you agree to these terms.
- This tool is intended for legitimate automation, testing, and accessibility purposes only.

The app itself shows this same disclaimer on first launch and requires explicit acceptance before it can be used.

---

## ✨ Features

| | |
|---|---|
| 🎯 | **Image-based automation** — point it at a screenshot, it finds and clicks the match (powered by PyAutoGUI) |
| 📥 | **Drag & drop** target images straight into the app, with a live large preview |
| ✏️ | **Editable queue** — select any step to update its confidence, delay, unit or name after adding it |
| ✅ | **Enable / disable / rename / remove** individual steps without rebuilding your whole sequence |
| ▶️⏸️⏹️ | **Start, Pause, and Cancel** controls, plus a global `Q` emergency abort hotkey |
| 💾 | **Auto-saved queue** — close the app and reopen it, your steps are still there |
| 📂 | **Import / export** step sequences as portable JSON profiles |
| 🎨 | **Modern & Classic UI modes**, plus Dark / Light theming |
| 🌐 | **Multi-language** — English & Turkish, fully localized |
| 🗂️ | **Remembers your preferences** (language, theme, UI mode) between launches |
| 🎬 | Animated splash screen and an in-app "what's new" changelog on update |

---

## 🖥️ Requirements

- Windows 10/11 (uses `pyautogui` + `keyboard` for screen automation and global hotkeys)
- Python **3.10+** if running from source

---

## 🚀 Getting Started

### Option A — Run from source

```bash
git clone https://github.com/skycoldtr/trigger-automation.git
cd trigger-automation

pip install -r requirements.txt
python trigger.py
```

### Option B — Build a standalone .exe

A ready-made build script is included:

```bash
git clone https://github.com/skycoldtr/trigger-automation.git
cd trigger-automation

build.bat
```

This installs the dependencies, bundles everything with PyInstaller, and produces a single-file `dist\TRIGGER.exe` — no Python installation needed to run it afterwards.

> **Note:** `keyboard` requires administrator privileges on Windows to listen for the global abort hotkey. Run the exe "as Administrator" if `Q` doesn't cancel a running sequence.

---

## 📖 Usage

1. **Add a step** — drag an image onto the drop zone (or click it to browse), give it a name, set the confidence and delay, then hit **Add Step**.
2. **Edit a step** — click it in the queue; its values load back into the editor. Adjust them and hit **Update Step**.
3. **Enable/disable/remove** steps from the queue toolbar or the right-click context menu.
4. **Start** the sequence — TRIGGER scans your screen for each enabled step's image and clicks it when found, waiting the configured delay between actions.
5. Press **`Q`** at any time, or hit **Cancel**, to stop immediately.
6. **Export/Import** your queue as a `.json` profile to reuse or share a sequence.

---

## 🗂️ Profile Format

Exported profiles are plain JSON, one object per step:

```json
[
  {
    "id": "…",
    "name": "Confirm Button",
    "path": "C:\\images\\confirm.png",
    "confidence": 0.85,
    "delay": 1.5,
    "unit": "sec",
    "enabled": true
  }
]
```

---

## 🛠️ Tech Stack

- **Python 3** + **Tkinter** for the UI
- **PyAutoGUI** for screen recognition & input simulation
- **keyboard** for the global abort hotkey
- **Pillow** for image handling & previews
- **tkinterdnd2** *(optional)* for drag & drop support
- **PyInstaller** for producing a standalone `.exe`

---

## 🤝 Contributing

Issues and pull requests are welcome. If you're reporting a bug, please include your OS version, Python version (if running from source), and steps to reproduce.

## 📄 License

MIT — see [`LICENSE`](LICENSE) for details.
