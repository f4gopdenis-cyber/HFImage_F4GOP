"""Petit drapeau australien (hommage à Erik Sundstrup VK4AES, créateur d'EasyPal), dessiné par le
programme : fond bleu, Union Jack en haut à gauche, étoile du Commonwealth, Croix du Sud."""
import math

from PIL import Image, ImageDraw

BLUE = (1, 33, 105)
RED = (200, 16, 46)
WHITE = (255, 255, 255)


def _star(d, cx, cy, r, points=7, inner=0.45):
    pts = []
    for i in range(points * 2):
        a = -math.pi / 2 + i * math.pi / points
        rr = r if i % 2 == 0 else r * inner
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=WHITE)


def australia(w=30, h=15):
    """-> image RGB du drapeau (proportions 2:1), dessinée en grand puis réduite."""
    k = 8
    W, H = w * k, h * k
    im = Image.new("RGB", (W, H), BLUE)
    d = ImageDraw.Draw(im)
    cw, ch = W // 2, H // 2                   # Union Jack : quart en haut à gauche (dessiné à part,
    uj = Image.new("RGB", (cw, ch), BLUE)     # pour que les diagonales ne débordent pas)
    u = ImageDraw.Draw(uj)
    t = ch / 15
    u.line([(0, 0), (cw, ch)], fill=WHITE, width=int(6 * t))
    u.line([(0, ch), (cw, 0)], fill=WHITE, width=int(6 * t))
    u.line([(0, 0), (cw, ch)], fill=RED, width=int(2 * t))
    u.line([(0, ch), (cw, 0)], fill=RED, width=int(2 * t))
    u.rectangle([cw / 2 - 5 * t, 0, cw / 2 + 5 * t, ch], fill=WHITE)
    u.rectangle([0, ch / 2 - 5 * t, cw, ch / 2 + 5 * t], fill=WHITE)
    u.rectangle([cw / 2 - 3 * t, 0, cw / 2 + 3 * t, ch], fill=RED)
    u.rectangle([0, ch / 2 - 3 * t, cw, ch / 2 + 3 * t], fill=RED)
    im.paste(uj, (0, 0))
    # étoile du Commonwealth (7 branches) sous l'Union Jack
    _star(d, cw / 2, H * 0.75, H * 0.15)
    # Croix du Sud (moitié droite)
    for x, y, r, n in ((0.75, 0.83, 0.07, 7), (0.62, 0.45, 0.07, 7), (0.75, 0.17, 0.07, 7),
                       (0.86, 0.39, 0.07, 7), (0.80, 0.56, 0.04, 5)):
        _star(d, W * x, H * y, H * r, n)
    return im.resize((w, h), Image.LANCZOS)
