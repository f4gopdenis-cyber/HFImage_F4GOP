"""Waterfall Tkinter : spectre 0-3000 Hz qui défile, avec repères des modes.

Les calculs FFT (rows_from) sont faits dans le thread audio ; l'affichage
(add_rows / _render) dans le thread de l'interface.
"""
import tkinter as tk

import numpy as np
from PIL import Image, ImageTk

FS = 8000
NFFT = 1024                 # 7,8 Hz par case
HOP = 800                   # 10 lignes par seconde
F_MAX = 3000
NBINS = int(F_MAX * NFFT / FS)
SCALE_H = 18                # hauteur de l'échelle de fréquences
WINDOW = np.hanning(NFFT)

# bandes occupées mesurées sur le signal codec2 (Hz)
MODE_BANDS = {"DATAC1X": (420, 2580, "#f06292"), "DATAC1": (670, 2330, "#4fc3f7"), "DATAC3": (1190, 1800, "#81c784"),
              "DATAC4": (1340, 1600, "#ffb74d"), "DATAC13": (1390, 1610, "#f48fb1"),
              "EasyPal": (350, 2800, "#ce93d8")}
# bandes EasyPal mesurées sur le signal (mode A / B / E, largeur 2,2 / 2,4 kHz) : affichées
# pour le mode reçu ou émis, sans ajouter un trait par variante dans l'échelle
EASYPAL_BANDS = {}
for _m, _bw, _lo, _hi in (("A", "2,2", 375, 2654), ("B", "2,2", 340, 2520), ("E", "2,2", 387, 2561),
                          ("A", "2,4", 381, 2824), ("B", "2,4", 340, 2801), ("E", "2,4", 387, 2713)):
    EASYPAL_BANDS[f"EasyPal {_m} {_bw}"] = (_lo, _hi, "#ce93d8")


def easypal_band_key(mode_idx, bw_idx):
    """Clé de bande pour mark_mode : mode 0/1/2 (A/B/E), largeur 0/1 (2,2/2,4 kHz)."""
    if not (0 <= mode_idx <= 2) or bw_idx not in (0, 1):
        return "EasyPal"
    return f"EasyPal {'ABE'[mode_idx]} {'2,2' if bw_idx == 0 else '2,4'}"


def _palette():
    """Palette noir -> bleu -> cyan -> jaune -> rouge -> blanc (256 x RGB)."""
    pts = [(0, (0, 0, 0)), (60, (0, 0, 140)), (120, (0, 170, 220)),
           (175, (240, 230, 0)), (225, (240, 40, 0)), (255, (255, 255, 255))]
    lut = np.zeros((256, 3), np.uint8)
    for (i0, c0), (i1, c1) in zip(pts, pts[1:]):
        for c in range(3):
            lut[i0:i1 + 1, c] = np.linspace(c0[c], c1[c], i1 - i0 + 1)
    return lut


LUT = _palette()


class RowMaker:
    """Transforme un flux d'échantillons 8 kHz en lignes de spectre (dB)."""

    def __init__(self):
        self.buf = np.zeros(0, np.float32)

    def rows_from(self, samples8k: np.ndarray):
        x = samples8k.astype(np.float32) / 32768.0
        self.buf = np.concatenate([self.buf, x])
        rows = []
        while len(self.buf) >= NFFT:
            spec = np.fft.rfft(self.buf[:NFFT] * WINDOW)[:NBINS]
            rows.append(10 * np.log10(np.abs(spec) ** 2 + 1e-12).astype(np.float32))
            self.buf = self.buf[HOP:]
        return rows


SPEC_H = 46                 # hauteur du spectre au-dessus de l'échelle


class Waterfall(tk.Canvas):
    """Spectre (en haut), échelle 0-3000 Hz, puis waterfall qui défile vers le bas.
    S'adapte à la taille de son conteneur (colonne étroite à la EasyPal)."""

    def __init__(self, master, height=150, spectrum=True, **kw):
        self.spec_h = SPEC_H if spectrum else 0
        super().__init__(master, height=height + SCALE_H + self.spec_h, bg="#000",
                         highlightthickness=0, **kw)
        self.h = height
        self.data = np.zeros((height, NBINS), np.uint8)
        self.spec = None            # dernier spectre normalisé 0..1
        self.floor = None           # plancher de bruit suivi (dB)
        self.peak = None            # crête suivie (dB)
        self.range_db = 45.0
        self.dirty = False
        self._img = None
        self._img_id = None
        self.mode_mark = None
        self.bind("<Configure>", self._resize)
        self.bind("<Motion>", self._hover)
        self.bind("<Leave>", lambda e: self.delete("hover"))
        self.after(100, self._tick)

    @property
    def top(self):                  # ordonnée du haut du waterfall
        return self.spec_h + SCALE_H

    def _resize(self, e):
        h = max(20, e.height - self.top)
        if h != self.h:
            new = np.zeros((h, NBINS), np.uint8)
            k = min(h, self.h)
            new[:k] = self.data[:k]
            self.data, self.h = new, h
        self._draw_scale()

    # ----- données
    def add_rows(self, rows):
        """Lignes en dB (thread interface). Niveau automatique sur le plancher de bruit."""
        if not rows:
            return
        rows = rows[-self.h:]
        arr = np.array(rows)
        med = float(np.median(arr))
        pk = float(np.percentile(arr, 99.5))
        if self.floor is None:
            self.floor, self.peak = med, pk
        else:
            self.floor = 0.9 * self.floor + 0.1 * med
            self.peak = max(pk, 0.95 * self.peak + 0.05 * pk)
        # échelle calée sur le bruit (réception) sans saturer un signal propre (émission)
        lo = max(self.floor - 5, self.peak - 70)
        hi = max(lo + self.range_db, self.peak + 3)
        v = np.clip((arr - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
        n = len(v)
        self.data = np.vstack([v[::-1], self.data[:-n]]) if n < self.h else v[::-1][:self.h]
        sp = np.clip((arr[-3:].mean(axis=0) - lo) / (hi - lo), 0, 1)
        self.spec = sp if self.spec is None else 0.5 * self.spec + 0.5 * sp
        self.dirty = True

    def clear(self):
        self.data[:] = 0
        self.floor = None
        self.spec = None
        self.dirty = True

    def mark_mode(self, mode):
        """Met en évidence la bande du mode reçu ou émis."""
        if mode != self.mode_mark:
            self.mode_mark = mode
            self._draw_scale()

    # ----- affichage
    def _tick(self):
        if self.dirty:
            self._render()
            self.dirty = False
        self.after(100, self._tick)

    def _render(self):
        w = max(10, self.winfo_width())
        img = Image.fromarray(LUT[self.data]).resize((w, self.h), Image.NEAREST)
        self._img = ImageTk.PhotoImage(img)
        if self._img_id is None:
            self._img_id = self.create_image(0, self.top, image=self._img, anchor="nw")
        else:
            self.coords(self._img_id, 0, self.top)
            self.itemconfigure(self._img_id, image=self._img)
        self.delete("spec")
        if self.spec_h and self.spec is not None:
            n = len(self.spec)
            xs = np.arange(n) * w / n
            ys = self.spec_h - 2 - self.spec * (self.spec_h - 6)
            pts = [0, self.spec_h] + [c for xy in zip(xs, ys) for c in xy] + [w, self.spec_h]
            self.create_polygon(pts, fill="#7a3d00", outline="", tags="spec")
            self.create_line([c for xy in zip(xs, ys) for c in xy], fill="#ffb347", tags="spec")
        self.tag_raise("band")

    def _x(self, f):
        return f / F_MAX * max(10, self.winfo_width())

    def _draw_scale(self):
        self.delete("scale", "band")
        w = max(10, self.winfo_width())
        y0 = self.spec_h
        if self.spec_h:
            self.create_rectangle(0, 0, w, y0, fill="#000", outline="", tags="scale")
        self.create_rectangle(0, y0, w, y0 + SCALE_H, fill="#1b1b1b", outline="", tags="scale")
        step = 500 if w >= 200 else 1000
        for f in range(0, F_MAX + 1, 250):
            x = self._x(f)
            major = f % 500 == 0
            self.create_line(x, y0 + SCALE_H - (7 if major else 4), x, y0 + SCALE_H, fill="#888", tags="scale")
            if f % step == 0 and 0 < f < F_MAX:
                self.create_text(x, y0 + 1, text=str(f), fill="#bbb", anchor="n",
                                 font=("TkDefaultFont", 7), tags="scale")
        # repères des modes : trait fin dans l'échelle, bande pleine pour le mode actif
        for i, (mode, (lo, hi, col)) in enumerate(MODE_BANDS.items()):
            y = y0 + SCALE_H - 2 - i * 2
            self.create_line(self._x(lo), y, self._x(hi), y, fill=col, width=1, tags="scale")
        band = MODE_BANDS.get(self.mode_mark) or EASYPAL_BANDS.get(self.mode_mark)
        if band:
            lo, hi, col = band
            for f in (lo, hi):
                self.create_line(self._x(f), self.top, self._x(f), self.top + self.h,
                                 fill=col, dash=(3, 4), tags="band")
            self.create_text(self._x(hi) + 3, self.top + 4, text=self.mode_mark, fill=col,
                             anchor="nw", font=("TkDefaultFont", 8, "bold"), tags="band")
        self.dirty = True

    def _hover(self, e):
        self.delete("hover")
        if e.y < self.top:
            return
        f = e.x / max(10, self.winfo_width()) * F_MAX
        self.create_line(e.x, self.top, e.x, self.top + self.h, fill="#fff", tags="hover")
        self.create_text(e.x + 5 if e.x < self.winfo_width() - 60 else e.x - 5, self.top + 14,
                         text=f"{f:.0f} Hz", fill="#fff",
                         anchor="w" if e.x < self.winfo_width() - 60 else "e",
                         font=("TkDefaultFont", 8), tags="hover")
