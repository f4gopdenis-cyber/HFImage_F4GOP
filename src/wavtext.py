"""Texte dans le waterfall (comme EasyPal) et gestion des fichiers WAV begin / end.

Le texte est dessiné en bitmap, puis chaque ligne de pixels devient une tranche de
temps où l'on émet une tonalité par pixel allumé : sur le waterfall du correspondant
(fréquence en horizontal, temps qui défile vers le bas), le texte apparaît lisible.
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FS = 8000
F_LO, F_HI = 400.0, 2600.0        # largeur du texte : 2,2 kHz, toute la bande SSB utile
ROW_S = 0.20                      # durée d'une ligne de pixels : lettres hautes sur le waterfall
COLS = 72                         # résolution horizontale (~31 Hz par colonne)
CLIP = 2.0                        # écrêtage doux : ~+4 dB de puissance moyenne
PEAK = 16000                      # même crête que le signal modem

FONTS = {
    "Arial": ("arialbd.ttf", "arial.ttf"),
    "Courier New": ("courbd.ttf", "cour.ttf"),
    "Times New Roman": ("timesbd.ttf", "times.ttf"),
    "Verdana": ("verdanab.ttf", "verdana.ttf"),
    "Tahoma": ("tahomabd.ttf", "tahoma.ttf"),
    "Impact": ("impact.ttf",),
    "Comic Sans MS": ("comicbd.ttf", "comic.ttf"),
}
FALLBACK = ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf")


def _font(name, size):
    for f in FONTS.get(name, ()) + FALLBACK:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def render(text, font="Arial", negative=False, cols=COLS):
    """Texte -> bitmap booléen (lignes x colonnes), une ligne de texte par ligne saisie."""
    lines = [l.rstrip() for l in text.strip().splitlines() if l.strip()] or [" "]
    size = 40
    f = _font(font, size)
    tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
    widths = [tmp.textlength(l, font=f) for l in lines]
    asc, desc = f.getmetrics()
    lh = asc + desc
    W = int(max(widths)) + 8
    H = lh * len(lines) + 6
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    for i, l in enumerate(lines):
        x = (W - widths[i]) / 2
        d.text((x, 3 + i * lh), l, font=f, fill=255)
    # recadrage vertical sur l'encre, puis mise à l'échelle sur `cols` colonnes
    bbox = img.getbbox() or (0, 0, W, H)
    img = img.crop((0, max(0, bbox[1] - 2), W, min(H, bbox[3] + 2)))
    rows = max(8, round(img.height * cols / img.width * 1.0))
    small = img.resize((cols, rows), Image.LANCZOS)
    bm = np.asarray(small) > 90
    if negative:
        bm = ~bm
    return bm


IMG_COLS = 96                     # image : ~23 Hz par colonne
IMG_DB = 24.0                     # dynamique des gris sur le waterfall (dB)


def render_image(img, cols=IMG_COLS, negative=False, max_rows=120):
    """Image (photo, logo) -> tableau de gris 0..1 (lignes x colonnes) pour le waterfall.
    Proportions gardées : une colonne = ~23 Hz, une ligne = ROW_S secondes, ce qui donne
    une image à peu près à l'échelle sur les waterfalls courants (EasyPal, HFImage…)."""
    from PIL import ImageOps
    im = img.convert("L")
    im = ImageOps.autocontrast(im, cutoff=1)
    rows = max(8, min(max_rows, round(cols * im.height / im.width * 0.8)))
    small = np.asarray(im.resize((cols, rows), Image.LANCZOS), dtype=np.float64) / 255.0
    if negative:
        small = 1.0 - small
    return small


def _levels(bitmap):
    """Bitmap booléen ou gris 0..1 -> amplitudes par pixel (échelle en dB pour les gris)."""
    if bitmap.dtype == bool:
        return bitmap.astype(np.float64)
    b = np.clip(bitmap, 0, 1)
    a = 10 ** ((b - 1.0) * IMG_DB / 20.0)          # le waterfall affiche en dB
    a[b < 0.06] = 0.0                              # noir = rien
    return a


def synth(bitmap, volume=5, fs=FS):
    """Bitmap -> audio int16 8 kHz. La dernière ligne est émise en premier, pour que
    le texte se lise à l'endroit sur un waterfall qui défile vers le bas.

    Pour que le texte soit bien visible chez le correspondant :
    - puissance par pixel constante (les lignes très remplies sont seulement limitées) ;
    - phases de Newman (faible facteur de crête) puis écrêtage doux tanh, ce qui donne
      beaucoup plus de puissance moyenne pour la même crête que le modem."""
    amp = _levels(bitmap)
    rows, cols = amp.shape
    freqs = np.linspace(F_LO, F_HI, cols)
    n = int(ROW_S * fs)
    t = np.arange(n) / fs
    ramp = np.ones(n)
    r = int(0.006 * fs)                       # fondus de 6 ms : pas de claquements
    ramp[:r] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, r))
    ramp[-r:] = ramp[:r][::-1]
    k = np.arange(cols)
    phase = np.pi * k * k / cols              # phases de Newman
    counts = (amp ** 2).sum(axis=1)
    ref = max(1.0, float(np.median(counts[counts > 0])) if counts.any() else 1.0)
    lead = np.zeros(int(0.3 * fs))
    out = [lead]
    for row, cnt in zip(amp[::-1], counts[::-1]):
        on = np.nonzero(row)[0]
        blk = np.zeros(n)
        if len(on):
            blk = (row[on, None] * np.sin(2 * np.pi * freqs[on, None] * t[None, :] + phase[on, None])).sum(axis=0)
            blk *= ramp / np.sqrt(max(cnt, ref))
        out.append(blk)
    out.append(lead)
    x = np.concatenate(out)
    act = x[np.abs(x) > 0]
    rms = float(np.sqrt(np.mean(act ** 2))) if len(act) else 1.0
    x = np.tanh(x / (rms * CLIP))
    # filtre passe-bande : l'écrêtage ne doit rien produire hors de la bande du texte
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    g = np.clip(np.minimum(f - (F_LO - 120), (F_HI + 120) - f) / 80.0, 0, 1)
    x = np.fft.irfft(X * g, len(x))
    peak = np.max(np.abs(x)) or 1.0
    x = x / peak * PEAK * max(0.1, min(2.0, volume / 5.0))
    return np.clip(x, -32767, 32767).astype(np.int16)


def preview(bitmap, scale=3):
    """Image de ce que verra le correspondant sur son waterfall."""
    if bitmap.dtype == bool:
        img = Image.fromarray(np.where(bitmap, 255, 20).astype(np.uint8))
    else:
        img = Image.fromarray((20 + 235 * np.clip(bitmap, 0, 1)).astype(np.uint8))
    img = img.resize((bitmap.shape[1] * scale, bitmap.shape[0] * scale), Image.NEAREST)
    lut = np.zeros((256, 3), np.uint8)
    lut[:, 0] = np.linspace(0, 255, 256)
    lut[:, 1] = np.linspace(0, 230, 256)
    lut[:, 2] = np.linspace(60, 0, 256)
    return Image.fromarray(lut[np.asarray(img)])


def normalize(x8k, volume=5):
    """WAV quelconque (déjà en 8 kHz int16) -> même crête que le modem x volume."""
    x = x8k.astype(np.float64)
    peak = np.max(np.abs(x)) or 1.0
    x = x / peak * PEAK * max(0.1, min(2.0, volume / 5.0))
    return np.clip(x, -32767, 32767).astype(np.int16)


def wav_dir(base):
    d = os.path.join(base, "wav")
    os.makedirs(d, exist_ok=True)
    return d
