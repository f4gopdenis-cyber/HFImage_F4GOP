"""Petites icônes au trait pour les tuiles du style Moderne (dessinées par le programme, sans
fichier) : flèche d'émission, relecture, clé, bulle, signal, personne, texte, onde, casque,
image, globe, engrenage, dossier…

icon(nom, taille, couleur) -> image PIL RGBA (dessinée en grand puis réduite : traits lisses)."""
import math

from PIL import Image, ImageDraw

K = 4          # suréchantillonnage


def _rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def _arc_pts(cx, cy, r, a0, a1, n=24):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def _draw(name, d, s, w, col):
    """Dessin sur une grille 24×24 mise à l'échelle s (= taille * K / 24)."""
    def P(*xy):
        return [(x * s, y * s) for x, y in zip(xy[::2], xy[1::2])]

    def line(*xy):
        d.line(P(*xy), fill=col, width=w, joint="curve")

    def poly(*xy):
        d.line(P(*xy) + P(*xy[:2]), fill=col, width=w, joint="curve")

    def circle(cx, cy, r, fill=False):
        box = [(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s]
        if fill:
            d.ellipse(box, fill=col)
        else:
            d.ellipse(box, outline=col, width=w)

    def arc(cx, cy, r, a0, a1):
        d.line([(x * s, y * s) for x, y in _arc_pts(cx, cy, r, a0, a1)], fill=col, width=w, joint="curve")

    def rect(x0, y0, x1, y1):
        d.rounded_rectangle([x0 * s, y0 * s, x1 * s, y1 * s], radius=2 * s, outline=col, width=w)

    if name == "tx":                                   # émission : flèche
        line(4, 12, 19, 12)
        line(13, 6, 19, 12, 13, 18)
    elif name == "relire":                             # relecture
        arc(12, 12, 8, -150, 180)
        line(3, 6, 4.1, 11, 9, 9.5)
    elif name == "fix":                                # clé
        line(5, 19, 13, 11)
        arc(15.5, 8.5, 4.5, 110, 400)
    elif name == "bsr":                                # bulle de demande
        poly(4, 5, 20, 5, 20, 16, 9, 16, 5, 20, 5, 16, 4, 16)
        line(8, 9, 16, 9)
        line(8, 12.5, 13, 12.5)
    elif name == "accord":                             # signal (accord)
        line(2, 12, 6, 12, 9, 5, 13, 19, 16, 9, 18, 12, 22, 12)
    elif name == "id":                                 # personne
        circle(12, 8, 4)
        arc(12, 21, 8, 200, 340)
    elif name == "texte":                              # lignes de texte
        line(4, 6, 20, 6)
        line(4, 12, 20, 12)
        line(4, 18, 14, 18)
    elif name == "wave":                               # onde
        pts = [(2 + i * 0.5, 12 - 6 * math.sin(i * 0.5 * math.pi / 4)) for i in range(41)]
        d.line([(x * s, y * s) for x, y in pts], fill=col, width=w, joint="curve")
    elif name == "ecoute":                             # casque
        arc(12, 13, 8, 180, 360)
        rect(3, 13, 7, 20)
        rect(17, 13, 21, 20)
    elif name == "txtinc":                             # texte + image
        rect(3, 5, 21, 19)
        line(7, 10, 17, 10)
        line(7, 14, 13, 14)
    elif name == "log":                                # liste
        for y in (6, 12, 18):
            circle(5, y, 1.2, fill=True)
            line(9, y, 20, y)
    elif name == "qsl":                                # carte
        rect(3, 5, 21, 19)
        circle(8, 10, 2)
        line(12, 9, 18, 9)
        line(6, 15, 18, 15)
    elif name == "image":                              # image
        rect(3, 4, 21, 20)
        circle(9, 9.5, 2)
        line(21, 16, 16, 11, 6, 20)
    elif name == "hyb":                                # globe (Internet)
        circle(12, 12, 9)
        line(3, 12, 21, 12)
        d.ellipse([(12 - 4) * s, 3 * s, (12 + 4) * s, 21 * s], outline=col, width=w)
    elif name == "reglages":                           # engrenage
        circle(12, 12, 3.2)
        for a in range(0, 360, 45):
            r0, r1 = 6.5, 9.5
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            line(12 + r0 * ca, 12 + r0 * sa, 12 + r1 * ca, 12 + r1 * sa)
        circle(12, 12, 6.5)
    elif name == "dossier":                            # dossier
        poly(3, 6, 9, 6, 11, 8, 21, 8, 21, 19, 3, 19)
    else:                                              # inconnu : point
        circle(12, 12, 3, fill=True)


NAMES = ("tx", "relire", "fix", "bsr", "accord", "id", "texte", "wave", "ecoute", "txtinc", "log", "qsl",
         "image", "hyb", "reglages", "dossier")


def icon(name, size=18, color="#000000"):
    big = size * K
    im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    _draw(name, d, big / 24, max(2, round(big * 0.085)), _rgb(color))
    return im.resize((size, size), Image.LANCZOS)
