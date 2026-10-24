"""« Mes conditions de trafic » incrustées sur l'image émise (comme le bandeau d'EasyPal) :
indicatif, locator, poste, puissance, antenne, fréquence, date UTC, texte libre."""

from PIL import Image, ImageDraw, ImageFont

DEFAULT = {"tc_on": False, "tc_rig": "", "tc_power": "", "tc_ant": "", "tc_qth": "", "tc_extra": "",
           "tc_call": True, "tc_loc": True, "tc_freq": True, "tc_date": True, "tc_pos": "bas", "tc_size": "normale",
           "tc_font": "Arial", "tc_bold": True, "tc_italic": False, "tc_color": "#ffffff", "tc_stroke": "#000000",
           "tc_bg": "#000000", "tc_alpha": 60, "tc_callcolor": "", "tc_frame": False}
STYLE_WORDS = ("Bold", "Italic", "Oblique", "Light", "Semibold", "SemiBold", "Black", "Medium", "Thin",
               "Condensed", "Demibold", "Heavy", "Semilight", "ExtraLight", "Regular", "Gras", "Italique")
# Polices livrées avec Windows (secours si le registre n'est pas lisible) : (normal, gras, italique, gras italique)
BUILTIN = {"Arial": ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"),
           "Arial Black": ("ariblk.ttf",) * 4, "Impact": ("impact.ttf",) * 4,
           "Verdana": ("verdana.ttf", "verdanab.ttf", "verdanai.ttf", "verdanaz.ttf"),
           "Tahoma": ("tahoma.ttf", "tahomabd.ttf", "tahoma.ttf", "tahomabd.ttf"),
           "Segoe UI": ("segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf", "segoeuiz.ttf"),
           "Calibri": ("calibri.ttf", "calibrib.ttf", "calibrii.ttf", "calibriz.ttf"),
           "Trebuchet MS": ("trebuc.ttf", "trebucbd.ttf", "trebucit.ttf", "trebucbi.ttf"),
           "Times New Roman": ("times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf"),
           "Georgia": ("georgia.ttf", "georgiab.ttf", "georgiai.ttf", "georgiaz.ttf"),
           "Courier New": ("cour.ttf", "courbd.ttf", "couri.ttf", "courbi.ttf"),
           "Consolas": ("consola.ttf", "consolab.ttf", "consolai.ttf", "consolaz.ttf"),
           "Comic Sans MS": ("comic.ttf", "comicbd.ttf", "comici.ttf", "comicz.ttf"),
           "DejaVu Sans": ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf",
                           "DejaVuSans-BoldOblique.ttf")}
_FONTS = None
SIZES = {"petite": 46.0, "normale": 36.0, "grande": 28.0}      # largeur / taille de police


def _registry_fonts():
    """{nom affiché: fichier} d'après le registre Windows (polices système + polices de l'utilisateur)."""
    out = {}
    try:
        import winreg
    except ImportError:
        return out
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            k = winreg.OpenKey(root, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts")
        except OSError:
            continue
        i = 0
        while True:
            try:
                name, val, _ = winreg.EnumValue(k, i)
            except OSError:
                break
            i += 1
            if not isinstance(val, str) or not val.lower().endswith((".ttf", ".otf", ".ttc")):
                continue
            for suf in (" (TrueType)", " (OpenType)"):
                name = name.replace(suf, "")
            for n in name.split(" & "):
                out.setdefault(n.strip(), val)
    return out


FONT_DIRS = ("/usr/share/fonts", "/usr/local/share/fonts", "~/.local/share/fonts", "~/.fonts")


def _linux_fonts():
    """Linux : {famille: (normal, gras, italique, gras italique)} d'après les fichiers de polices
    installés (noms lus dans les fichiers eux-mêmes)."""
    import os
    files = []
    for d in FONT_DIRS:
        d = os.path.expanduser(d)
        for root, _dirs, names in os.walk(d):
            files += [os.path.join(root, n) for n in names if n.lower().endswith((".ttf", ".otf"))]
            if len(files) > 3000:
                break
    fam = {}
    for f in files:
        try:
            family, style = ImageFont.truetype(f, 12).getname()
        except Exception:
            continue
        st = (style or "").lower()
        slot = (1 if "bold" in st else 0) + (2 if ("italic" in st or "oblique" in st) else 0)
        if any(w in st for w in ("light", "thin", "black", "condensed", "medium", "semi", "extra")):
            continue
        fam.setdefault(family, [None] * 4)
        if fam[family][slot] is None:
            fam[family][slot] = f
    out = {}
    for name, (n, b, i, bi) in fam.items():
        base = n or b or i or bi
        out[name] = (base, b or base, i or base, bi or b or base)
    return out


def fonts():
    """{famille: (normal, gras, italique, gras italique)} — les polices installées, triées."""
    global _FONTS
    if _FONTS is not None:
        return _FONTS
    import sys
    if not sys.platform.startswith("win"):
        _FONTS = dict(sorted(_linux_fonts().items(), key=lambda kv: kv[0].lower()))
        return _FONTS
    reg = _registry_fonts()
    fam = {}
    for name, f in reg.items():
        words = name.split()
        if any(w in STYLE_WORDS for w in words) or name.startswith(("@", "Marlett", "Symbol", "Wingdings",
                                                                     "Webdings", "MT Extra")):
            continue
        g = lambda *suf: next((reg[name + " " + x] for x in suf if name + " " + x in reg), None)
        b = g("Bold", "Gras") or f
        it = g("Italic", "Oblique", "Italique") or f
        bi = g("Bold Italic", "Bold Oblique", "Gras Italique") or b
        fam[name] = (f, b, it, bi)
    for name, files in BUILTIN.items():
        if name not in fam and _try(files[0]):
            fam[name] = files
    _FONTS = dict(sorted(fam.items(), key=lambda kv: kv[0].lower()))
    return _FONTS


def _try(f, size=12):
    try:
        ImageFont.truetype(f, size)
        return True
    except OSError:
        return False


# Linux : polices libres équivalentes aux polices de Windows
LINUX_ALIAS = {"Arial": "Liberation Sans", "Times New Roman": "Liberation Serif", "Courier New": "Liberation Mono",
               "Verdana": "DejaVu Sans", "Tahoma": "DejaVu Sans", "Segoe UI": "DejaVu Sans", "Calibri": "Carlito"}


def font(family="Arial", size=24, bold=True, italic=False):
    fs = fonts()
    files = fs.get(family) or fs.get(LINUX_ALIAS.get(family, "")) or BUILTIN.get(family)
    if files:
        for f in (files[bold + 2 * italic], files[1 if bold else 0], files[0]):
            try:
                return ImageFont.truetype(f, size)
            except OSError:
                pass
    return _font(size)


def _rgb(c, default=(255, 255, 255)):
    try:
        c = c.lstrip("#")
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, AttributeError, IndexError):
        return default


def _font(size):
    for f in ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def parts(conf, call="", loc="", rig_model="", freq_text=""):
    """Morceaux du bandeau, dans l'ordre."""
    c = dict(DEFAULT, **{k: v for k, v in conf.items() if k.startswith("tc_")})
    out = []
    if c["tc_call"] and call:
        out.append(call)
    if c["tc_loc"] and loc:
        out.append(loc)
    if c["tc_qth"]:
        out.append(c["tc_qth"])
    rig = c["tc_rig"] or rig_model
    if rig:
        out.append(rig)
    if c["tc_power"]:
        p = str(c["tc_power"]).strip()
        out.append(p if not p.replace(",", ".").replace(".", "", 1).isdigit() else p + " W")
    if c["tc_ant"]:
        out.append(c["tc_ant"])
    if c["tc_freq"] and freq_text:
        out.append(freq_text)
    if c["tc_date"]:
        import clocktz
        out.append(clocktz.fmt("%Y-%m-%d %H:%M"))
    if c["tc_extra"]:
        out.append(c["tc_extra"])
    return out


def overlay(img, items, pos="bas", size="normale", style=None, call=""):
    """Bandeau avec les conditions de trafic, sur une ou plusieurs lignes.
    style : police, gras/italique, couleurs (texte, contour, fond + opacité, indicatif) — clés tc_*."""
    if not items:
        return img
    st = dict(DEFAULT, **(style or {}))
    im = img.convert("RGB").copy()
    fs = max(12, int(im.width / SIZES.get(size, 36.0)))
    fnt = font(st["tc_font"], fs, bool(st["tc_bold"]), bool(st["tc_italic"]))
    fg, sk = _rgb(st["tc_color"]), _rgb(st["tc_stroke"], (0, 0, 0))
    cc = _rgb(st["tc_callcolor"], fg) if st.get("tc_callcolor") else fg
    bg = _rgb(st["tc_bg"], (0, 0, 0))
    alpha = max(0, min(100, int(st.get("tc_alpha", 60) or 0)))
    sw = max(1, fs // 14) if st["tc_stroke"] else 0
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    sep = "  •  "
    maxw = im.width - 2 * fs
    lines, cur = [], []
    width = lambda parts: d.textlength(sep.join(parts), font=fnt)
    for it in items:
        if not cur or width(cur + [it]) <= maxw:
            cur.append(it)
        else:
            lines.append(cur)
            cur = [it]
    if cur:
        lines.append(cur)
    asc, desc = fnt.getmetrics()
    lh = int((asc + desc) * 1.12)
    h = lh * len(lines) + fs // 2
    y0 = im.height - h if pos == "bas" else 0
    if alpha:
        d.rectangle((0, y0, im.width, y0 + h), fill=bg + (round(alpha * 2.55),))
    if st.get("tc_frame"):
        d.line((0, y0 if pos == "bas" else y0 + h - 1, im.width, y0 if pos == "bas" else y0 + h - 1),
               fill=cc + (255,), width=max(2, fs // 10))
    for i, parts in enumerate(lines):
        x = (im.width - width(parts)) / 2
        y = y0 + fs // 4 + i * lh
        for k, p in enumerate(parts):
            if k:
                d.text((x, y), sep, font=fnt, fill=fg + (255,), stroke_width=sw, stroke_fill=sk + (255,))
                x += d.textlength(sep, font=fnt)
            col = cc if call and p == call else fg
            d.text((x, y), p, font=fnt, fill=col + (255,), stroke_width=sw, stroke_fill=sk + (255,))
            x += d.textlength(p, font=fnt)
    base = im.convert("RGBA")
    base.alpha_composite(layer)
    return base.convert("RGB")


PIP_SCALE = {"petite": 0.26, "moyenne": 0.34, "grande": 0.45}


PIP_MIN, PIP_MAX = 0.10, 0.90      # taille libre : fraction de la largeur de l'image


def pip_layout(img_size, thumb_size, caption="", corner="haut-droite", size="moyenne", pos=None, scale=None):
    """Place de l'incrustation -> (x, y, W, H, tw, b, fs, cap_h).
    pos = (fx, fy) entre 0 et 1 : position libre (0 = bord gauche / haut, 1 = bord droit / bas) ;
    scale = largeur libre en fraction de la largeur de l'image."""
    iw, ih = img_size
    frac = min(PIP_MAX, max(PIP_MIN, float(scale))) if scale else PIP_SCALE.get(size, 0.34)
    tw = max(40, int(iw * frac))
    th_h = max(1, round(thumb_size[1] * tw / max(1, thumb_size[0])))
    b = max(2, tw // 60)                                   # cadre
    fs = max(11, tw // 13)
    cap_h = int(fs * 1.45) if caption else 0
    W, H = tw + 2 * b, th_h + 2 * b + cap_h
    if H > ih:                                             # très haute : on réduit pour qu'elle tienne
        k = ih / H
        return pip_layout(img_size, thumb_size, caption, corner, size, pos, max(PIP_MIN, frac * k * 0.98))
    if pos is not None:
        fx, fy = (min(1.0, max(0.0, float(v))) for v in pos)
        x, y = round(fx * max(0, iw - W)), round(fy * max(0, ih - H))
    else:
        m = max(6, iw // 60)                               # marge au bord
        x = m if "gauche" in corner else iw - W - m
        y = m if "haut" in corner else ih - H - m
    return x, y, W, H, tw, b, fs, cap_h


PIP_ROT_MAX = 45          # rotation de l'incrustation : -45° à +45°


def _perspective(box, tilt):
    """Incrustation « penchée » (effet 3D, demande de M7WUV) : tilt de -1 à 1 ; > 0 : le bord
    droit s'éloigne (plus petit), < 0 : le bord gauche. -> image RGBA (coins transparents)."""
    import numpy as np
    W, H = box.size
    t = max(-1.0, min(1.0, float(tilt)))
    dy = H * 0.4 * abs(t) / 2                    # le bord éloigné rapetisse jusqu'à 60 %
    dx = W * 0.12 * abs(t)                       # et se rapproche un peu (raccourci)
    if t > 0:
        dst = [(0, 0), (W - dx, dy), (W - dx, H - dy), (0, H)]
    else:
        dst = [(dx, dy), (W, 0), (W, H), (dx, H - dy)]
    src = [(0, 0), (W, 0), (W, H), (0, H)]
    # PIL : pour chaque point de l'image obtenue, le point d'origine (dst -> src)
    a, bvec = [], []
    for (x, y), (u, v) in zip(dst, src):
        a.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        a.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        bvec += [u, v]
    coef = np.linalg.solve(np.array(a, float), np.array(bvec, float))
    return box.transform((W, H), Image.PERSPECTIVE, tuple(coef), Image.BICUBIC)


def pip(img, thumb, caption="", corner="haut-droite", size="moyenne", pos=None, scale=None, rot=0, tilt=0):
    """Image du correspondant incrustée dans un coin, ou à l'endroit et à la taille choisis
    à la souris (cadre blanc, légende « de F4EMK — +12 dB »). rot : rotation en degrés
    (sens inverse des aiguilles d'une montre) ; tilt : perspective de -1 à 1 (0 : de face)."""
    im = img.convert("RGB").copy()
    th = thumb.convert("RGB")
    x, y, W, H, tw, b, fs, cap_h = pip_layout(im.size, th.size, caption, corner, size, pos, scale)
    th = th.resize((tw, H - 2 * b - cap_h), Image.LANCZOS)
    font = _font(fs)
    box = Image.new("RGB", (W, H), (255, 255, 255))
    box.paste(th, (b, b))
    if caption:
        d = ImageDraw.Draw(box)
        d.rectangle((0, th.height + 2 * b, W, H), fill=(20, 20, 20))
        w = d.textlength(caption, font=font)
        d.text(((W - w) / 2, th.height + 2 * b + (cap_h - fs) / 2 - 1), caption, font=font, fill=(255, 230, 90))
    rot = max(-PIP_ROT_MAX, min(PIP_ROT_MAX, float(rot or 0)))
    tilt = float(tilt or 0)
    if abs(rot) >= 0.5 or abs(tilt) >= 0.01:
        # penchée / tournée : même centre ; les coins qui dépassent restent transparents
        card = box.convert("RGBA")
        if abs(tilt) >= 0.01:
            card = _perspective(card, tilt)
        if abs(rot) >= 0.5:
            card = card.rotate(rot, resample=Image.BICUBIC, expand=True)
        cx, cy = x + W / 2, y + H / 2
        px, py = round(cx - card.width / 2), round(cy - card.height / 2)
        alpha = card.getchannel("A")
        shadow = Image.new("RGBA", card.size, (0, 0, 0, 0))
        shadow.putalpha(alpha.point(lambda a: a * 110 // 255))
        base = im.convert("RGBA")
        base.paste(shadow, (px + b * 2, py + b * 2), shadow)
        base.paste(card, (px, py), card)
        return base.convert("RGB")
    # ombre
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 110))
    base = im.convert("RGBA")
    base.alpha_composite(sh, (max(0, min(im.width - W, x + b * 2)), max(0, min(im.height - H, y + b * 2))))
    base.paste(box, (x, y))
    return base.convert("RGB")
