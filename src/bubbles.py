"""Bulles de texte façon bande dessinée, dessinées sur l'image émise.

Une bulle : {"text", "style", "size", "cx", "cy", "tx", "ty", "bg", "fg"}
  - style : « parole » (bulle ronde + pointe), « pensée » (petits ronds), « cri » (contour en
    étoile + pointe), « cartouche » (rectangle, sans pointe) ;
  - size : « petite », « moyenne », « grande » (hauteur du texte relative à l'image) ;
  - text peut contenir les émoticônes de EMOJI (dessinées en couleur, images Twemoji) ;
  - cx, cy : centre de la bulle, tx, ty : bout de la pointe, en fractions de la largeur /
    hauteur de l'image (0..1) : la bulle garde sa place quelle que soit la taille d'émission.
Le dessin est fait à double résolution puis réduit (bords lisses).
"""
import math
import os
import sys

from PIL import Image, ImageDraw

import trafic

STYLES = ("parole", "pensée", "cri", "cartouche", "texte")
NO_TAIL = ("cartouche", "texte")       # « texte » : texte seul sur l'image, sans bulle (contour = couleur de fond)
SIZES = {"petite": 0.038, "moyenne": 0.052, "grande": 0.072}
MIN_PX = 14                     # en dessous, le texte devient illisible après compression
FONTS = ("Comic Sans MS", "Arial")
SS = 2                          # suréchantillonnage

# émoticônes (images Twemoji, CC-BY 4.0) : dessinées en couleur dans le texte des bulles
EMOJI_CODES = ("1f600 1f602 1f609 1f60e 1f60d 1f914 1f62e 1f622 1f44d 1f44b 1f44f 1f64f 1f91d 2764 2b50 "
               "1f389 1f382 2615 1f37a 1f525 26a1 2600 1f327 2744 1f30d 1f4fb 1f4e1 1f399 1f4f7 1f3c6").split()
EMOJI = {chr(int(c, 16)): c for c in EMOJI_CODES}
_EMO_CACHE = {}


def emoji_dir():
    here = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(here, "emoji")


def emoji_image(ch, px):
    """Image RGBA de l'émoticône `ch` à la taille px (None si inconnue)."""
    code = EMOJI.get(ch)
    if not code:
        return None
    key = (code, px)
    if key not in _EMO_CACHE:
        try:
            im = Image.open(os.path.join(emoji_dir(), code + ".png")).convert("RGBA")
        except OSError:
            _EMO_CACHE[key] = None
            return None
        _EMO_CACHE[key] = im.resize((px, px), Image.LANCZOS)
    return _EMO_CACHE[key]


# émoticônes animées (mode hybride : l'image part en GIF animé). Les animations sont faites
# par HFImage à partir des mêmes images Twemoji : battement, rebond, balancement, rotation,
# clin d'œil, scintillement.
ANIM_FRAMES, ANIM_MS = 12, 90
ANIM_KIND = {"2764": "pulse", "1f525": "flicker", "1f389": "pulse", "1f382": "bounce", "2b50": "spin",
             "2600": "spin", "2744": "spin", "26a1": "flash", "1f44b": "wave", "1f44d": "wave",
             "1f44f": "pulse", "1f64f": "pulse", "1f91d": "wave", "1f609": "blink", "1f600": "bounce",
             "1f602": "shake", "1f60d": "pulse", "1f622": "bounce", "1f327": "bounce", "1f30d": "spin",
             "1f3c6": "wave", "1f4fb": "shake", "1f4e1": "wave"}


def has_anim(bubbles):
    """Au moins une bulle animée qui contient une émoticône ?"""
    return any(b.get("anim") and any(ch in EMOJI for ch in (b.get("text") or "")) for b in bubbles or [])


def anim_emoji(ch, px, t):
    """Émoticône animée à l'instant t (0..1) -> (image RGBA de taille px, décalage dx, dy)."""
    code = EMOJI.get(ch)
    kind = ANIM_KIND.get(code, "bounce")
    a = 2 * math.pi * t
    if kind == "blink":                       # clin d'œil : 😀 ouvert, 😉 sur une partie du cycle
        im = emoji_image(chr(int("1f600", 16)) if t < 0.7 else ch, px)
        return im, 0, 0
    base = emoji_image(ch, px)
    if base is None:
        return None, 0, 0
    dx = dy = 0
    if kind == "pulse":                       # battement : grossit / rétrécit
        k = 1 + 0.18 * max(0.0, math.sin(a * 2)) if code == "2764" else 1 + 0.12 * math.sin(a)
        s = max(1, int(round(px * k)))
        im = base.resize((s, s), Image.LANCZOS)
        return im, (px - s) / 2, (px - s) / 2
    if kind == "bounce":                      # rebond
        dy = -abs(math.sin(a)) * px * 0.22
        return base, 0, dy
    if kind == "shake":                       # secousse
        dx = math.sin(a * 3) * px * 0.08
        return base.rotate(math.sin(a * 3) * 8, resample=Image.BICUBIC), dx, 0
    if kind == "wave":                        # balancement
        return base.rotate(math.sin(a) * 20, resample=Image.BICUBIC), 0, 0
    if kind == "spin":                        # rotation
        return base.rotate(-360 * t, resample=Image.BICUBIC), 0, 0
    if kind == "flicker":                     # flamme : s'étire vers le haut
        k = 1 + 0.12 * math.sin(a * 2)
        h = max(1, int(round(px * k)))
        return base.resize((px, h), Image.LANCZOS), 0, px - h
    if kind == "flash":                       # éclair : clignote
        im = base.copy()
        if math.sin(a * 2) < -0.3:
            im.putalpha(im.getchannel("A").point(lambda v: v // 4))
        return im, 0, 0
    return base, 0, 0


def _runs(text):
    """Texte -> [(« t », morceau) ou (« e », émoticône)]."""
    out, cur = [], ""
    for ch in text.replace("\ufe0f", ""):
        if ch in EMOJI:
            if cur:
                out.append(("t", cur))
                cur = ""
            out.append(("e", ch))
        else:
            cur += ch
    if cur:
        out.append(("t", cur))
    return out


def _esize(font):
    return int(round(font.size * 1.15))


def _measure(font, text):
    return sum(font.getlength(v) if k == "t" else _esize(font) + font.size * 0.08 for k, v in _runs(text))


def new(text="", style="parole", size="moyenne", cx=0.5, cy=0.3):
    return {"text": text, "style": style, "size": size, "cx": cx, "cy": cy,
            "tx": min(0.95, cx + 0.12), "ty": min(0.95, cy + 0.2), "bg": "#ffffff", "fg": "#000000"}


def _font(px):
    fams = trafic.fonts()
    for fam in FONTS:
        if fam in fams or fam in trafic.BUILTIN:
            return trafic.font(fam, px, bold=True)
    return trafic.font("Arial", px, bold=True)


def font_px(H, size):
    return max(MIN_PX, int(round(H * SIZES.get(size, SIZES["moyenne"]))))


def _wrap(text, font, max_w):
    lines = []
    for para in (text or "").split("\n"):
        words, cur = para.split(), ""
        if not words:
            lines.append("")
            continue
        for w in words:
            t = f"{cur} {w}".strip()
            if cur and _measure(font, t) > max_w:
                lines.append(cur)
                cur = w
            else:
                cur = t
        lines.append(cur)
    return lines or [""]


def layout(W, H, b, scale=1.0):
    """Géométrie d'une bulle sur une image W×H (pixels ; scale = suréchantillonnage).
    -> dict : centre, demi-axes, pointe, lignes, police, boîte englobante de la bulle."""
    fpx = font_px(H, b.get("size"))
    font = _font(int(fpx * scale))
    # texte seul : lignes plus longues (légende sur toute la largeur)
    lines = _wrap(b.get("text", ""), font, (0.85 if b.get("style") == "texte" else 0.45) * W * scale)
    lh = font.size * 1.18
    tw = max([_measure(font, t) for t in lines] + [font.size * 2])
    th = lh * len(lines)
    pad = font.size * 0.55
    style = b.get("style", "parole")
    if style == "cartouche":
        rx, ry = tw / 2 + pad, th / 2 + pad * 0.7
    elif style == "texte":
        rx, ry = tw / 2 + pad * 0.3, th / 2 + pad * 0.3
    else:
        rx, ry = tw / 2 * 1.22 + pad, th / 2 * 1.5 + pad * 0.6
    if style == "cri":
        rx, ry = rx * 1.08, ry * 1.12
    cx, cy = b.get("cx", 0.5) * W * scale, b.get("cy", 0.3) * H * scale
    # la bulle reste entièrement dans l'image
    ext = 1.28 if style == "cri" else 1.0
    cx = min(max(cx, rx * ext + 2), W * scale - rx * ext - 2) if 2 * rx * ext < W * scale else W * scale / 2
    cy = min(max(cy, ry * ext + 2), H * scale - ry * ext - 2) if 2 * ry * ext < H * scale else H * scale / 2
    tx, ty = b.get("tx", 0.6) * W * scale, b.get("ty", 0.6) * H * scale
    return {"cx": cx, "cy": cy, "rx": rx, "ry": ry, "tx": tx, "ty": ty, "lines": lines, "font": font,
            "lh": lh, "th": th, "lw": max(2, font.size / 9), "style": style,
            "box": (cx - rx * ext, cy - ry * ext, cx + rx * ext, cy + ry * ext)}


def _ell_pt(g, ang, k=1.0):
    return g["cx"] + g["rx"] * k * math.cos(ang), g["cy"] + g["ry"] * k * math.sin(ang)


def _has_tail(g):
    if g["style"] in NO_TAIL:
        return False
    # pointe à l'intérieur de la bulle : pas de pointe
    dx, dy = (g["tx"] - g["cx"]) / g["rx"], (g["ty"] - g["cy"]) / g["ry"]
    return dx * dx + dy * dy > 1.15


def _tail_poly(g):
    ang = math.atan2((g["ty"] - g["cy"]) / g["ry"], (g["tx"] - g["cx"]) / g["rx"])
    a, b = _ell_pt(g, ang - 0.22, 0.9), _ell_pt(g, ang + 0.22, 0.9)
    return [a, (g["tx"], g["ty"]), b]


def _star(g, n=18):
    pts = []
    for i in range(2 * n):
        ang = math.pi * i / n
        k = 1.28 if i % 2 == 0 else 1.0
        pts.append(_ell_pt(g, ang, k))
    return pts


def _bounds(g):
    x0, y0, x1, y1 = g["box"]
    if _has_tail(g):
        x0, y0 = min(x0, g["tx"]), min(y0, g["ty"])
        x1, y1 = max(x1, g["tx"]), max(y1, g["ty"])
    m = g["lw"] * 3
    return x0 - m, y0 - m, x1 + m, y1 + m


def _draw_one(d, g, off, bg, fg, layer=None, t=None):
    ox, oy = off
    sh = lambda pts: [(x - ox, y - oy) for x, y in pts]
    lw = g["lw"]
    cx, cy, rx, ry = g["cx"] - ox, g["cy"] - oy, g["rx"], g["ry"]
    style, tail = g["style"], _has_tail(g)
    if style == "texte":
        pass                                  # pas de bulle : le texte seul, avec un contour (plus bas)
    elif style == "cartouche":
        d.rounded_rectangle((cx - rx - lw, cy - ry - lw, cx + rx + lw, cy + ry + lw), radius=lw * 2, fill=fg)
        d.rounded_rectangle((cx - rx, cy - ry, cx + rx, cy + ry), radius=lw * 1.5, fill=bg)
    elif style == "pensée":
        d.ellipse((cx - rx - lw, cy - ry - lw, cx + rx + lw, cy + ry + lw), fill=fg)
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=bg)
        if tail:
            ang = math.atan2((g["ty"] - g["cy"]) / ry, (g["tx"] - g["cx"]) / rx)
            sx, sy = _ell_pt(g, ang, 1.08)
            for k, f in enumerate((0.3, 0.62, 0.92)):
                x = sx + (g["tx"] - sx) * f - ox
                y = sy + (g["ty"] - sy) * f - oy
                r = max(lw * 1.5, g["font"].size * (0.55 - 0.13 * k))
                d.ellipse((x - r - lw, y - r - lw, x + r + lw, y + r + lw), fill=fg)
                d.ellipse((x - r, y - r, x + r, y + r), fill=bg)
    else:
        body = sh(_star(g)) if style == "cri" else None
        tp = sh(_tail_poly(g)) if tail else None
        # contour : traits épais (2 lw) le long des formes ; l'intérieur, dessiné ensuite,
        # en recouvre la moitié intérieure : il reste un contour de lw tout autour
        w2 = max(2, int(round(lw * 2)))
        if body:
            d.line(body + [body[0]], fill=fg, width=w2, joint="curve")
            d.polygon(body, fill=fg)
        else:
            d.ellipse((cx - rx - lw, cy - ry - lw, cx + rx + lw, cy + ry + lw), fill=fg)
        if tp:
            d.line(tp + [tp[0]], fill=fg, width=w2, joint="curve")
        # intérieur : la pointe recouvre le contour à sa base (bulle d'un seul tenant)
        if body:
            d.polygon(body, fill=bg)
        else:
            d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=bg)
        if tp:
            d.polygon(tp, fill=bg)
    font, lh = g["font"], g["lh"]
    y = cy - g["th"] / 2
    for line in g["lines"]:
        ym = y + lh / 2
        x = cx - _measure(font, line) / 2
        for kind, v in _runs(line):
            if kind == "t":
                if style == "texte":          # contour de la couleur de « fond » : lisible sur toute photo
                    d.text((x, ym), v, font=font, fill=fg, anchor="lm",
                           stroke_width=max(2, int(round(font.size / 12))), stroke_fill=bg)
                else:
                    d.text((x, ym), v, font=font, fill=fg, anchor="lm")
                x += font.getlength(v)
            else:
                es = _esize(font)
                dx = dy = 0
                if t is None:
                    em = emoji_image(v, es)
                else:
                    em, dx, dy = anim_emoji(v, es, t)
                if em is not None and layer is not None:
                    px_, py_ = int(x + font.size * 0.04 + dx), int(ym - es / 2 + dy)
                    # l'animation peut déborder un peu : on reste dans le calque
                    px_ = max(0, min(layer.width - em.width, px_))
                    py_ = max(0, min(layer.height - em.height, py_))
                    layer.alpha_composite(em, (px_, py_))
                x += es + font.size * 0.08
        y += lh


def draw(img, bubbles, t=None):
    """-> nouvelle image RGB avec les bulles (l'image d'origine n'est pas modifiée).
    t (0..1) : instant de l'animation des émoticônes des bulles animées (None : fixes)."""
    bubbles = [b for b in bubbles or [] if (b.get("text") or "").strip()]
    if not bubbles:
        return img
    out = img.convert("RGBA")
    W, H = out.size
    for b in bubbles:
        g = layout(W, H, b, SS)
        x0, y0, x1, y1 = (int(math.floor(v)) for v in _bounds(g))
        x0, y0 = max(0, x0 - x0 % SS), max(0, y0 - y0 % SS)
        x1, y1 = min(W * SS, x1 + SS), min(H * SS, y1 + SS)
        if x1 <= x0 or y1 <= y0:
            continue
        layer = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
        _draw_one(ImageDraw.Draw(layer), g, (x0, y0), trafic._rgb(b.get("bg"), (255, 255, 255)) + (255,),
                  trafic._rgb(b.get("fg"), (0, 0, 0)) + (255,), layer, t if b.get("anim") else None)
        small = layer.resize(((x1 - x0) // SS, (y1 - y0) // SS), Image.LANCZOS)
        out.alpha_composite(small, (x0 // SS, y0 // SS))
    return out.convert("RGB")


def frames(img, bubbles, n=ANIM_FRAMES):
    """Images de l'animation (une par instant) pour le GIF animé."""
    return [draw(img, bubbles, k / n) for k in range(n)]


def make_gif(base, bubbles_json, wmax=800, max_bytes=2_000_000):
    """Image + bulles animées -> GIF animé (octets, traitement). bubbles_json : les bulles en JSON
    (clé du cache de préparation). Largeur ramenée à wmax : une photo en GIF (256 couleurs) pèse
    vite lourd ; réduit encore si besoin (imgfmt.gif_shrink)."""
    import json
    import imgfmt
    bubs = json.loads(bubbles_json)
    if base.width > wmax:
        base = base.resize((wmax, max(1, round(base.height * wmax / base.width))), Image.LANCZOS)
    fr = frames(base.convert("RGB"), bubs)
    data = imgfmt._gif_encode(fr, [ANIM_MS] * len(fr), 1.0, 255, 1)
    return imgfmt.gif_shrink(data, max_bytes)


def hit(W, H, bubbles, x, y, grab=10):
    """Clic en (x, y) sur une image affichée en W×H -> (indice, « pointe » / « bulle ») ou None.
    La pointe est prioritaire (petite cible) ; les bulles du dessus d'abord."""
    for i in range(len(bubbles) - 1, -1, -1):
        g = layout(W, H, bubbles[i])
        if g["style"] not in NO_TAIL and math.hypot(x - g["tx"], y - g["ty"]) <= grab:
            return i, "pointe"
    for i in range(len(bubbles) - 1, -1, -1):
        x0, y0, x1, y1 = layout(W, H, bubbles[i])["box"]
        if x0 <= x <= x1 and y0 <= y <= y1:
            return i, "bulle"
    return None
