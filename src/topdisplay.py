"""2.18 : barre du haut du style Moderne façon « écran de poste » (choix de F4GOP).

La fréquence s'affiche dans un petit afficheur sombre, chiffres orange lumineux (7.058.000),
le mode et la bande dans le coin ; l'indicatif dans une pastille. Dessinés avec PIL (lueur,
coins arrondis), puis posés dans les étiquettes de la barre. Sans police trouvée : None
(la barre garde alors l'affichage texte d'avant).
"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

LCD_BG = (2, 8, 22)
LCD_DIGIT = (255, 205, 90)
LCD_GLOW = (255, 175, 40)
LCD_UNIT = (205, 165, 85)
LCD_SUB = (120, 200, 255)
LCD_OFF = (90, 75, 45)

_MONO = ("consolab.ttf", "DejaVuSansMono-Bold.ttf", "LiberationMono-Bold.ttf", "FreeMonoBold.ttf")
_SANS = ("segoeuib.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "FreeSansBold.ttf")
_DIRS = [os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
         "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation",
         "/usr/share/fonts/truetype/freefont", "/usr/share/fonts/TTF", "/Library/Fonts",
         os.path.expanduser("~/.fonts")]
_cache = {}


def _font(names, px):
    key = (names, px)
    if key in _cache:
        return _cache[key]
    f = None
    for d in _DIRS:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                try:
                    f = ImageFont.truetype(p, px)
                    break
                except OSError:
                    pass
        if f:
            break
    _cache[key] = f
    return f


def freq_text(hz):
    """7058000 -> « 7.058.000 » (MHz.kHz.Hz, comme sur l'afficheur du poste)."""
    hz = int(round(hz))
    return f"{hz // 1_000_000}.{(hz // 1000) % 1000:03d}.{hz % 1000:03d}"


def lcd(hz, mode, band, border, pt, empty_label=""):
    """Afficheur de fréquence -> image PIL (RGBA), ou None sans police.
    pt : taille de base en pixels (grandit avec la taille de police choisie)."""
    fd = _font(_MONO, int(pt * 1.45))
    fs = _font(_SANS, max(8, int(pt * 0.62)))
    if fd is None or fs is None:
        return None
    s = 3                                                 # dessin 3x, réduit (bords nets)
    fd3 = _font(_MONO, int(pt * 1.45) * s)
    fs3 = _font(_SANS, max(8, int(pt * 0.62)) * s)
    txt = freq_text(hz) if hz else "-.---.---"
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    tw = probe.textlength("88.888.888", font=fd3)         # largeur fixe : ne bouge pas avec la fréquence
    # largeur fixe aussi pour le coin mode / bande (la barre ne bouge pas en changeant de bande)
    sub_w = max(probe.textlength(x, font=fs3) for x in (mode or "", "MHz · " + (band or ""), empty_label or "",
                                                          "USB-DATA1", "LSB-DATA1", "MHz · 160 m"))
    pad = int(pt * 0.75) * s
    W = int(pad + tw + pad * 0.8 + sub_w + pad)
    H = int(pt * 2.3) * s
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=int(H * 0.22), fill=LCD_BG + (255,), outline=border, width=s)
    x0 = pad + tw                                         # chiffres alignés à droite (comme un afficheur)
    if hz:
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).text((x0, H / 2), txt, font=fd3, fill=LCD_GLOW + (255,), anchor="rm")
        im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(int(pt * 0.35) * s)))
        d = ImageDraw.Draw(im)
        d.text((x0, H / 2), txt, font=fd3, fill=LCD_DIGIT, anchor="rm")
    else:
        d.text((x0, H / 2), txt, font=fd3, fill=LCD_OFF, anchor="rm")
    xs = x0 + pad * 0.8
    if hz:
        d.text((xs, H * 0.27), mode or "", font=fs3, fill=LCD_SUB, anchor="lm")
        d.text((xs, H * 0.73), " · ".join(x for x in ("MHz", band or "") if x), font=fs3, fill=LCD_UNIT, anchor="lm")
    else:
        d.text((xs, H / 2), empty_label or "", font=fs3, fill=LCD_UNIT, anchor="lm")
    return im.resize((W // s, H // s), Image.LANCZOS)


def pill(text, bg, fg, pt):
    """Indicatif dans une pastille -> image PIL (RGBA), ou None sans police."""
    f3 = _font(_SANS, int(pt * 1.0) * 3)
    if f3 is None:
        return None
    s = 3
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    tw = probe.textlength(text, font=f3)
    H = int(pt * 1.75) * s
    W = int(tw + H * 0.9)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=H // 2, fill=bg)
    d.text((W / 2, H / 2), text, font=f3, fill=fg, anchor="mm")
    return im.resize((W // s, H // s), Image.LANCZOS)


def hex_rgb(c):
    c = str(c).lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    try:
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return (128, 128, 128)
