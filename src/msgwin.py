"""Fenêtre « Message reçu » : s'ouvre quand un correspondant envoie un message
(texte seul, ou texte joint à une image), avec Répondre / Copier et l'historique de la session."""
import os
import sys
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from i18n import tr


def flash_taskbar(win):
    """Fait clignoter le bouton de la barre des tâches (Windows), sans voler le clavier."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        from ctypes import wintypes

        class FLASHWINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("hwnd", wintypes.HWND), ("dwFlags", wintypes.DWORD),
                        ("uCount", wintypes.UINT), ("dwTimeout", wintypes.DWORD)]
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
        fi = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd, 3 | 12, 0, 0)   # FLASHW_ALL | FLASHW_TIMERNOFG
        ctypes.windll.user32.FlashWindowEx(ctypes.byref(fi))
    except Exception:
        pass


class MessageWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.items = []                 # dicts : id, call, text, utc, mode, snr, image
        self.pos = 0
        self.title(tr("Message reçu"))
        self.geometry("620x380")
        self.minsize(460, 280)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        top = ttk.Frame(self, padding=(12, 10, 12, 4))
        top.pack(fill="x")
        self.lb_call = ttk.Label(top, text="", font=("TkDefaultFont", 15, "bold"))
        self.lb_call.pack(side="left")
        nav = ttk.Frame(top)
        nav.pack(side="right")
        self.bt_prev = ttk.Button(nav, text="◀", width=3, command=lambda: self.go(1))
        self.bt_prev.pack(side="left")
        self.lb_nav = ttk.Label(nav, text="", width=9, anchor="center")
        self.lb_nav.pack(side="left")
        self.bt_next = ttk.Button(nav, text="▶", width=3, command=lambda: self.go(-1))
        self.bt_next.pack(side="left")
        self.lb_info = ttk.Label(self, text="", foreground="#666", padding=(12, 0))
        self.lb_info.pack(anchor="w")
        mid = ttk.Frame(self, padding=(12, 6))
        mid.pack(fill="both", expand=True)
        self.txt = tk.Text(mid, wrap="word", font=("TkDefaultFont", 13), height=8, padx=8, pady=6,
                           relief="solid", bd=1)
        sb = ttk.Scrollbar(mid, command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set)
        self.thumb = tk.Label(mid, cursor="hand2")
        self.thumb._no_theme = True
        self.thumb.bind("<Button-1>", lambda e: self.open_image())
        self.thumb.pack(side="right", anchor="n", padx=(8, 0))
        sb.pack(side="right", fill="y")
        self.txt.pack(side="left", fill="both", expand=True)
        self.txt.bind("<Key>", lambda e: None if (e.state & 4 and e.keysym.lower() in ("c", "a")) else "break")
        bot = ttk.Frame(self, padding=(12, 4, 12, 10))
        bot.pack(fill="x")
        self.v_auto = tk.BooleanVar(value=app.conf.get("msg_popup", True))
        self.v_bell = tk.BooleanVar(value=app.conf.get("msg_bell", True))
        ttk.Checkbutton(bot, text="Ouvrir à chaque message reçu", variable=self.v_auto,
                        command=self._store).pack(side="left")
        ttk.Checkbutton(bot, text="Bip", variable=self.v_bell, command=self._store).pack(side="left", padx=(10, 0))
        ttk.Button(bot, text="Fermer", command=self.withdraw).pack(side="right")
        ttk.Button(bot, text="Copier", command=self.copy).pack(side="right", padx=4)
        ttk.Button(bot, text="Répondre…", command=self.reply).pack(side="right")
        self._photo = None
        app._translate_ui(self)
        self.withdraw()

    def _store(self):
        self.app.conf["msg_popup"] = bool(self.v_auto.get())
        self.app.conf["msg_bell"] = bool(self.v_bell.get())
        self.app._save_conf_file()

    # ------------------------------------------------------------------ données
    def add(self, item, popup=True):
        for it in self.items:            # même message reçu une seconde fois (répétition) : on ne double pas
            if it.get("id") is not None and it.get("id") == item.get("id") and it["text"] == item["text"]:
                it.update({k: v for k, v in item.items() if v not in (None, "?", "")})
                self.show()
                return
        self.items.insert(0, item)
        del self.items[100:]
        self.pos = 0
        self.show()
        if popup and self.app.conf.get("msg_popup", True):
            self.present()

    def set_call(self, iid, call):
        for it in self.items:
            if it.get("id") == iid and it.get("call") in (None, "", "?"):
                it["call"] = call
        self.show()

    def set_image(self, iid, path):
        for it in self.items:
            if it.get("id") == iid:
                it["image"] = path
        self.show()

    # ------------------------------------------------------------------ affichage
    def present(self):
        was_hidden = self.state() == "withdrawn"
        self.deiconify()
        if was_hidden:
            try:                          # près de la fenêtre principale
                x = self.app.winfo_rootx() + max(0, (self.app.winfo_width() - 620) // 2)
                y = self.app.winfo_rooty() + 120
                self.geometry(f"+{x}+{y}")
            except tk.TclError:
                pass
        self.lift()
        self.attributes("-topmost", True)
        self.after(1500, lambda: self.winfo_exists() and self.attributes("-topmost", False))
        if self.app.conf.get("msg_bell", True):
            self.bell()
        flash_taskbar(self)

    def go(self, d):
        self.pos = max(0, min(len(self.items) - 1, self.pos + d))
        self.show()

    def show(self):
        n = len(self.items)
        self.txt.delete("1.0", "end")
        if not n:
            self.lb_call.configure(text=tr("Aucun message reçu pour l'instant."))
            self.lb_info.configure(text="")
            self.lb_nav.configure(text="")
            self.thumb.configure(image="")
            return
        it = self.items[self.pos]
        call = it.get("call")
        self.lb_call.configure(text=tr("Message de") + " " + (call if call not in (None, "", "?")
                                                              else tr("(indicatif à venir)")))
        info = [it["utc"] + " UTC"]
        if it.get("mode"):
            info.append(it["mode"])
        if it.get("snr") is not None:
            info.append(f"{it['snr']:+.0f} dB")
        if it.get("image"):
            info.append(tr("avec une image"))
        self.lb_info.configure(text="   •   ".join(info))
        self.txt.insert("1.0", it["text"])
        self.lb_nav.configure(text=f"{n - self.pos} / {n}")
        self.bt_prev.state(["!disabled" if self.pos < n - 1 else "disabled"])
        self.bt_next.state(["!disabled" if self.pos > 0 else "disabled"])
        self._photo = None
        p = it.get("image")
        if p and os.path.exists(p):
            try:
                im = Image.open(p)
                im.thumbnail((180, 180))
                self._photo = ImageTk.PhotoImage(im.convert("RGB"))
            except Exception:
                self._photo = None
        self.thumb.configure(image=self._photo or "")

    # ------------------------------------------------------------------ actions
    def copy(self):
        if self.items:
            self.clipboard_clear()
            self.clipboard_append(self.items[self.pos]["text"])

    def open_image(self):
        p = self.items[self.pos].get("image") if self.items else None
        if p and os.path.exists(p):
            self.app.open_path(p)

    def reply(self):
        it = self.items[self.pos] if self.items else {}
        call = it.get("call")
        me = self.app.v_call.get().strip().upper()
        self.app.show_text()
        box = self.app.txt_msg
        if call not in (None, "", "?") and not box.get("1.0", "end").strip():
            box.insert("1.0", f"{call} de {me} : " if me else f"{call} : ")
        box.mark_set("insert", "end-1c")
        box.focus_set()
