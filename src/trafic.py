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
    import i18n
    for f in i18n.cjk_fonts(bold):                   # chinois : police avec les caractères chinois
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
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
    import i18n
    for f in i18n.cjk_fonts(True) + ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf",
                                       "LiberationSans-Bold.ttf"):
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


PIP_MIN, PIP_MAX = 0.04, 0.90      # taille libre : fraction de la largeur de l'image (1.69 : 4 %, petit logo)


PIP_SHAPES = ("rect", "arrondi", "rond", "ovale")     # forme de l'incrustation


def pip_layout(img_size, thumb_size, caption="", corner="haut-droite", size="moyenne", pos=None, scale=None,
               logo=False, shape="rect"):
    """Place de l'incrustation -> (x, y, W, H, tw, b, fs, cap_h).
    pos = (fx, fy) entre 0 et 1 : position libre (0 = bord gauche / haut, 1 = bord droit / bas) ;
    scale = largeur libre en fraction de la largeur de l'image."""
    iw, ih = img_size
    frac = min(PIP_MAX, max(PIP_MIN, float(scale))) if scale else PIP_SCALE.get(size, 0.34)
    tw = max(20 if logo else 40, int(iw * frac))
    th_h = tw if shape == "rond" else max(1, round(thumb_size[1] * tw / max(1, thumb_size[0])))
    b = 0 if logo else max(2, tw // 60)                    # cadre (aucun pour un logo)
    fs = max(11, tw // 13)
    cap_h = int(fs * 1.45) if caption and not logo else 0
    if cap_h and shape in ("rond", "ovale"):
        cap_h += max(2, fs // 4)                           # légende dans une pastille sous la forme
    W, H = tw + 2 * b, th_h + 2 * b + cap_h
    if H > ih:                                             # très haute : on réduit pour qu'elle tienne
        k = ih / H
        return pip_layout(img_size, thumb_size, caption, corner, size, pos, max(PIP_MIN, frac * k * 0.98), logo,
                          shape)
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


def _shape_mask(size, shape, corners=None):
    """Masque (L) lissé de la forme : « arrondi », « rond » / « ovale » (ellipse), sinon plein."""
    W, H = size
    k = 4                                                  # dessiné en grand puis réduit : bords lisses
    m = Image.new("L", (W * k, H * k), 0)
    d = ImageDraw.Draw(m)
    if shape in ("rond", "ovale"):
        d.ellipse((0, 0, W * k - 1, H * k - 1), fill=255)
    elif shape == "arrondi":
        r = max(4, min(W, H) // 8) * k
        d.rounded_rectangle((0, 0, W * k - 1, H * k - 1), radius=r, fill=255, corners=corners)
    else:
        d.rectangle((0, 0, W * k, H * k), fill=255)
    return m.resize((W, H), Image.LANCZOS)


def _square(im):
    """Centre carré de l'image (forme « rond »)."""
    s = min(im.size)
    x, y = (im.width - s) // 2, (im.height - s) // 2
    return im.crop((x, y, x + s, y + s))


def _shaped_box(th, caption, W, H, tw, b, fs, cap_h, shape):
    """Incrustation avec cadre blanc découpée suivant la forme -> image RGBA."""
    font = _font(fs)
    box = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    th_h = th.height
    if shape in ("rond", "ovale"):
        eh = th_h + 2 * b
        frame = Image.new("RGBA", (W, eh), (255, 255, 255, 255))
        frame.putalpha(_shape_mask((W, eh), shape))
        box.alpha_composite(frame, (0, 0))
        pic = th.convert("RGBA")
        pic.putalpha(_shape_mask(pic.size, shape))
        box.alpha_composite(pic, (b, b))
        if caption:
            d = ImageDraw.Draw(box)
            pill_h = int(fs * 1.45)
            w = d.textlength(caption, font=font)
            pw = min(W, int(w + fs * 1.2))
            y0 = H - pill_h
            d.rounded_rectangle(((W - pw) // 2, y0, (W + pw) // 2, H - 1), radius=pill_h // 2,
                                fill=(20, 20, 20, 255))
            d.text(((W - w) / 2, y0 + (pill_h - fs) / 2 - 1), caption, font=font, fill=(255, 230, 90))
        return box
    # coins arrondis : cadre blanc arrondi, photo arrondie en haut (et en bas sans légende)
    flat = Image.new("RGB", (W, H), (255, 255, 255))
    pic = th.convert("RGBA")
    pic.putalpha(_shape_mask(pic.size, "arrondi", None if not caption else (True, True, False, False)))
    flat.paste(pic, (b, b), pic)
    if caption:
        d = ImageDraw.Draw(flat)
        d.rectangle((0, th_h + 2 * b, W, H), fill=(20, 20, 20))
        w = d.textlength(caption, font=font)
        d.text(((W - w) / 2, th_h + 2 * b + (cap_h - fs) / 2 - 1), caption, font=font, fill=(255, 230, 90))
    box = flat.convert("RGBA")
    box.putalpha(_shape_mask((W, H), "arrondi"))
    return box


def logo_on(img, logo, x, y, W, H, rot=0, tilt=0, opacity=1.0, shape="rect"):
    """Logo (PNG à fond transparent, demande de RK1AT) posé directement sur l'image : ni cadre,
    ni ombre, ni légende ; la transparence laisse voir la photo. Rotation, perspective et opacité ;
    la forme (arrondi, rond, ovale) découpe le logo."""
    src = logo.convert("RGBA")
    if shape == "rond":
        src = _square(src)
    card = src.resize((max(1, W), max(1, H)), Image.LANCZOS)
    if shape in ("arrondi", "rond", "ovale"):
        a = card.getchannel("A")
        card.putalpha(Image.composite(a, Image.new("L", a.size, 0), _shape_mask(card.size, shape)))
    if abs(float(tilt or 0)) >= 0.01:
        card = _perspective(card, tilt)
    rot = max(-PIP_ROT_MAX, min(PIP_ROT_MAX, float(rot or 0)))
    if abs(rot) >= 0.5:
        card = card.rotate(rot, resample=Image.BICUBIC, expand=True)
    op = max(0.0, min(1.0, float(opacity if opacity is not None else 1.0)))
    if op < 0.999:
        card.putalpha(card.getchannel("A").point(lambda a: int(a * op)))
    px, py = round(x + W / 2 - card.width / 2), round(y + H / 2 - card.height / 2)
    base = img.convert("RGBA")
    base.paste(card, (px, py), card)
    return base.convert("RGB")


def has_alpha(im):
    """Image avec de la transparence (PNG à fond transparent…) ?"""
    if im.mode in ("RGBA", "LA", "PA"):
        return im.getchannel("A").getextrema()[0] < 255
    return im.mode == "P" and "transparency" in im.info


def pip(img, thumb, caption="", corner="haut-droite", size="moyenne", pos=None, scale=None, rot=0, tilt=0,
        logo=False, opacity=1.0, shape="rect"):
    """Image du correspondant incrustée dans un coin, ou à l'endroit et à la taille choisis
    à la souris (cadre blanc, légende « de F4EMK — +12 dB »). rot : rotation en degrés
    (sens inverse des aiguilles d'une montre) ; tilt : perspective de -1 à 1 (0 : de face)."""
    shape = shape if shape in PIP_SHAPES else "rect"
    if logo:
        x, y, W, H = pip_layout(img.size, thumb.size, "", corner, size, pos, scale, logo=True, shape=shape)[:4]
        return logo_on(img, thumb, x, y, W, H, rot, tilt, opacity, shape)
    im = img.convert("RGB").copy()
    th = thumb.convert("RGB")
    if shape == "rond":
        th = _square(th)
    x, y, W, H, tw, b, fs, cap_h = pip_layout(im.size, th.size, caption, corner, size, pos, scale, shape=shape)
    th = th.resize((tw, H - 2 * b - cap_h), Image.LANCZOS)
    rot = max(-PIP_ROT_MAX, min(PIP_ROT_MAX, float(rot or 0)))
    tilt = float(tilt or 0)
    if shape != "rect":
        box = _shaped_box(th, caption, W, H, tw, b, fs, cap_h, shape)
    else:
        font = _font(fs)
        box = Image.new("RGB", (W, H), (255, 255, 255))
        box.paste(th, (b, b))
        if caption:
            d = ImageDraw.Draw(box)
            d.rectangle((0, th.height + 2 * b, W, H), fill=(20, 20, 20))
            w = d.textlength(caption, font=font)
            d.text(((W - w) / 2, th.height + 2 * b + (cap_h - fs) / 2 - 1), caption, font=font,
                   fill=(255, 230, 90))
    if shape != "rect" or abs(rot) >= 0.5 or abs(tilt) >= 0.01:
        # forme, penchée / tournée : même centre ; ce qui dépasse de la forme reste transparent
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
