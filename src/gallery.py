"""Galerie des dernières images reçues et envoyées (comme « 30 dernières Rx / TX » d'EZPix).

- GalleryStore : liste des images (fichier galerie.json dans le dossier des images reçues).
  Au premier lancement, les images déjà présentes dans le dossier sont reprises d'après
  leur nom (20261016_101245_DATAC1X_F4EMK.avif).
- GalleryView  : mosaïque de vignettes « de F4EMK », clic = afficher, double-clic = plein
  format, clic droit = menu.
"""
import json
import os
import re
import threading
import time
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

INDEX = "galerie.json"
SENT_DIR = "envoyees"
KEEP = 300                       # entrées gardées dans l'index (par sens)
IMG_EXT = (".avif", ".webp", ".jpg", ".jpeg", ".png", ".gif", ".svg")
NAME_RX = re.compile(r"^(\d{8})_(\d{6})_([A-Za-z0-9]+(?:-HYB)?)(_apercu)?(?:_(.+?))?$")


class GalleryStore:
    def __init__(self, folder):
        self.folder = folder
        self.items = []
        self.lock = threading.Lock()
        self.load()

    def _path(self):
        return os.path.join(self.folder, INDEX)

    def load(self):
        try:
            with open(self._path(), encoding="utf-8") as f:
                self.items = [e for e in json.load(f) if isinstance(e, dict)]
        except (OSError, ValueError):
            self.items = self.scan()
            self.save()

    def save(self):
        try:
            os.makedirs(self.folder, exist_ok=True)
            with self.lock:
                rx = [e for e in self.items if e.get("dir") == "rx"][:KEEP]
                tx = [e for e in self.items if e.get("dir") == "tx"][:KEEP]
                data = sorted(rx + tx, key=lambda e: -e.get("t", 0))
            tmp = self._path() + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=0, ensure_ascii=False)
            os.replace(tmp, self._path())
        except OSError:
            pass

    def scan(self):
        """Images déjà présentes (reçues avant cette version, et envoyées)."""
        out = []
        for d, direction in ((self.folder, "rx"), (os.path.join(self.folder, SENT_DIR), "tx")):
            try:
                names = os.listdir(d)
            except OSError:
                continue
            stems = {}
            for n in names:
                stem, ext = os.path.splitext(n)
                if ext.lower() in IMG_EXT:
                    stems.setdefault(stem, []).append(ext)
            for stem, exts in stems.items():
                m = NAME_RX.match(stem)
                if not m or m.group(4) or (m.group(5) or "").startswith("texte"):
                    continue                               # aperçus et messages texte : non
                main = next((e for e in exts if e.lower() != ".png"), exts[0])
                path = os.path.join(d, stem + main)
                png = os.path.join(d, stem + ".png") if ".png" in [e.lower() for e in exts] else None
                try:
                    t = time.mktime(time.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S"))
                    size = os.path.getsize(path)
                except (ValueError, OSError):
                    continue
                out.append({"t": t, "dir": direction, "call": (m.group(5) or "?").replace("-", "/")
                            if direction == "rx" else "", "mode": m.group(3), "file": path,
                            "png": png, "size": size})
        out.sort(key=lambda e: -e["t"])
        return out

    def add(self, entry):
        with self.lock:
            # même fichier (ex. renommé après l'identification de fin) : remplacé
            self.items = [e for e in self.items if e.get("file") != entry.get("file")]
            self.items.insert(0, entry)
        self.save()

    def update_file(self, old, new_file, new_png, call):
        with self.lock:
            for e in self.items:
                if e.get("file") == old:
                    e.update(file=new_file, png=new_png, call=call)
        self.save()

    def remove(self, entry):
        with self.lock:
            self.items = [e for e in self.items if e is not entry]
        self.save()

    def latest(self, direction, n):
        with self.lock:
            return [e for e in self.items if e.get("dir") == direction
                    and os.path.exists(e.get("png") or e.get("file") or "")][:n]


class GalleryView(tk.Frame):
    TW, TH, CAP, GAP = 148, 111, 18, 6

    def __init__(self, master, app, tr):
        super().__init__(master, bg="black")
        self.app, self.tr = app, tr
        self.store = None
        self.v_dir = tk.StringVar(value="rx")
        self.v_n = tk.StringVar(value="30")
        self.thumbs = {}            # (chemin, date) -> PhotoImage
        self.shown = []
        self._job = None
        self._gen = 0

        bar = tk.Frame(self, bg="black")
        bar.pack(fill="x", pady=(4, 2))
        self.btns = {}
        for d, label in (("rx", "Dernières reçues"), ("tx", "Dernières envoyées")):
            b = tk.Button(bar, text=label, relief="raised", bd=1, padx=8,
                          command=lambda d=d: self.set_dir(d))
            b.pack(side="left", padx=(6 if d == "rx" else 2, 0))
            self.btns[d] = b
        ttk.Combobox(bar, textvariable=self.v_n, values=["30", "60", "100"], width=4,
                     state="readonly").pack(side="left", padx=8)
        self.v_n.trace_add("write", lambda *a: self.refresh())
        tk.Button(bar, text="Dossier", relief="raised", bd=1, command=self._open_dir).pack(side="right", padx=6)
        self.lb_help = tk.Label(bar, text="Clic : afficher — double-clic : plein format — clic droit : options",
                                bg="black", fg="white", font=("TkDefaultFont", 9, "bold"))
        self.lb_help.pack(side="left", padx=10)

        body = tk.Frame(self, bg="black")
        body.pack(fill="both", expand=True)
        self.cv = tk.Canvas(body, bg="#202020", highlightthickness=0)
        sb = ttk.Scrollbar(body, orient="vertical", command=self.cv.yview)
        self.cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.cv.pack(side="left", fill="both", expand=True)
        self.cv.bind("<Configure>", lambda e: self._layout_later())
        self.cv.bind("<MouseWheel>", lambda e: self.cv.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        self.cv.bind("<Button-4>", lambda e: self.cv.yview_scroll(-1, "units"))
        self.cv.bind("<Button-5>", lambda e: self.cv.yview_scroll(1, "units"))
        self.lb_status = tk.Label(self, text="", bg="black", fg="#bbbbbb", anchor="w")
        self.lb_status.pack(fill="x", padx=6)
        self.menu = tk.Menu(self, tearoff=0)
        self._cols = 0
        self._paint_btns()

    # ------------------------------------------------------------------ données
    def set_store(self, store):
        self.store = store
        self.refresh()

    def set_dir(self, d):
        self.v_dir.set(d)
        self._paint_btns()
        self.refresh()

    def _paint_btns(self):
        for d, b in self.btns.items():
            on = d == self.v_dir.get()
            b.configure(bg="#2040ff" if on else "white", fg="white" if on else "black",
                        activebackground="#4060ff" if on else "#e6e6e6")

    def refresh(self):
        if self.store is None:
            return
        try:
            n = int(self.v_n.get())
        except ValueError:
            n = 30
        self.shown = self.store.latest(self.v_dir.get(), n)
        self._cols = 0
        self._layout()

    # ------------------------------------------------------------------ dessin
    def _layout_later(self):
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(80, self._layout)

    def _layout(self):
        self._job = None
        W = max(self.cv.winfo_width(), self.TW + 2 * self.GAP)
        cols = max(1, (W - self.GAP) // (self.TW + self.GAP))
        self._cols = cols
        self._gen += 1
        gen = self._gen
        cv = self.cv
        cv.delete("all")
        if not self.shown:
            cv.create_text(W // 2, 60, fill="#bbbbbb", text=self.tr(
                "Aucune image reçue pour l'instant." if self.v_dir.get() == "rx"
                else "Aucune image envoyée pour l'instant."))
            cv.configure(scrollregion=(0, 0, W, 120))
            self.lb_status.configure(text="")
            return
        x0 = (W - cols * (self.TW + self.GAP) + self.GAP) // 2
        for i, e in enumerate(self.shown):
            r, c = divmod(i, cols)
            x = x0 + c * (self.TW + self.GAP)
            y = self.GAP + r * (self.TH + self.CAP + self.GAP)
            tag = f"t{i}"
            cv.create_rectangle(x, y, x + self.TW, y + self.TH, fill="#5a5a5a", outline="#5a5a5a", tags=(tag,))
            cap = self._caption(e)
            cv.create_rectangle(x, y + self.TH + 1, x + self.TW, y + self.TH + self.CAP, fill="black",
                                outline="#7a7a7a", tags=(tag,))
            cv.create_text(x + self.TW // 2, y + self.TH + self.CAP // 2 + 1, text=cap, fill="white",
                           font=("TkDefaultFont", 9), tags=(tag,))
            cv.tag_bind(tag, "<Button-1>", lambda ev, e=e: self._click(e))
            cv.tag_bind(tag, "<Double-Button-1>", lambda ev, e=e: self._full(e))
            cv.tag_bind(tag, "<Button-3>", lambda ev, e=e: self._popup(ev, e))
            cv.tag_bind(tag, "<Enter>", lambda ev, e=e: self._hover(e))
        rows = (len(self.shown) + cols - 1) // cols
        cv.configure(scrollregion=(0, 0, W, self.GAP + rows * (self.TH + self.CAP + self.GAP)))
        self.lb_status.configure(text=self.tr(f"{len(self.shown)} images") if len(self.shown) != 1
                                 else self.tr("1 image"))
        self._load_thumbs(gen, x0, cols)

    def _caption(self, e):
        if e.get("dir") == "rx":
            return self.tr(f"de {e.get('call') or '?'}")
        return f"{e.get('mode', '')}  {time.strftime('%d/%m %H:%M', time.localtime(e.get('t', 0)))}"

    def _load_thumbs(self, gen, x0, cols, i=0):
        """Vignettes chargées petit à petit (l'interface reste fluide)."""
        if gen != self._gen or i >= len(self.shown):
            return
        e = self.shown[i]
        src = e.get("png") or e.get("file")
        try:
            key = (src, os.path.getmtime(src))
            ph = self.thumbs.get(key)
            if ph is None:
                im = Image.open(src)
                im.draft("RGB", (self.TW * 2, self.TH * 2))
                im = im.convert("RGB")
                im.thumbnail((self.TW, self.TH), Image.LANCZOS)
                ph = ImageTk.PhotoImage(im)
                if len(self.thumbs) > 400:
                    self.thumbs.clear()
                self.thumbs[key] = ph
            r, c = divmod(i, cols)
            x = x0 + c * (self.TW + self.GAP)
            y = self.GAP + r * (self.TH + self.CAP + self.GAP)
            self.cv.create_image(x + self.TW // 2, y + self.TH // 2, image=ph, tags=(f"t{i}",))
        except Exception:
            pass
        self.after(1, lambda: self._load_thumbs(gen, x0, cols, i + 1))

    # ------------------------------------------------------------------ actions
    def _hover(self, e):
        t = time.strftime("%d/%m/%Y %H:%M", time.localtime(e.get("t", 0)))
        who = (self.tr("de") + f" {e.get('call') or '?'}   —   ") if e.get("dir") == "rx" else ""
        self.lb_status.configure(text=f"{who}{t}   —   {e.get('mode', '')}   —   "
                                      f"{(e.get('size') or 0) / 1000:.1f} K   —   {os.path.basename(e.get('file') or '')}")

    def _click(self, e):
        self.app.gallery_show(e)

    def _full(self, e):
        self.app.gallery_full(e)

    def _popup(self, ev, e):
        m = self.menu
        m.delete(0, "end")
        m.add_command(label=self.tr("Afficher dans l'onglet RX"), command=lambda: self._click(e))
        m.add_command(label=self.tr("Ouvrir en plein format"), command=lambda: self._full(e))
        m.add_command(label=self.tr("Renvoyer cette image (onglet TX)"), command=lambda: self.app.gallery_to_tx(e))
        if e.get("dir") == "rx":
            m.add_command(label=self.tr("Répondre avec cette image (incrustée dans mon image TX)"),
                          command=lambda: self.app.set_pip(e))
        if e.get("dir") == "rx" and e.get("call") not in (None, "", "?"):
            m.add_command(label=self.tr(f"Voir {e['call']} sur la carte"), command=lambda: self.app.show_map(e["call"]))
        m.add_separator()
        m.add_command(label=self.tr("Ouvrir le dossier"), command=lambda: self.app.gallery_folder(e))
        m.add_command(label=self.tr("Retirer de la galerie"), command=lambda: self._remove(e))
        try:
            m.tk_popup(ev.x_root, ev.y_root)
        finally:
            m.grab_release()

    def _remove(self, e):
        self.store.remove(e)
        self.refresh()

    def _open_dir(self):
        d = self.store.folder if self.store else None
        if d and self.v_dir.get() == "tx":
            d = os.path.join(d, SENT_DIR)
        if d:
            self.app.open_path(d)
