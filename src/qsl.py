"""Carte QSL : photo de fond + bandeau avec indicatifs, date UTC, fréquence, report."""

from i18n import tr

from PIL import Image, ImageDraw, ImageFont

W, H = 960, 600              # carte de base (fond dégradé) ; mise en page dessinée pour cette taille
MAX_SIDE = 2000             # 2.31 (M7WUV) : la carte garde la taille de son fond, jusqu'à 2000 px

# polices proposées : nom -> (normale, grasse) ; fichiers des polices Windows
FONTS = {
    "Arial": ("arial.ttf", "arialbd.ttf"),
    "Arial Black": ("ariblk.ttf", "ariblk.ttf"),
    "Segoe UI": ("segoeui.ttf", "segoeuib.ttf"),
    "Verdana": ("verdana.ttf", "verdanab.ttf"),
    "Tahoma": ("tahoma.ttf", "tahomabd.ttf"),
    "Trebuchet MS": ("trebuc.ttf", "trebucbd.ttf"),
    "Georgia": ("georgia.ttf", "georgiab.ttf"),
    "Times New Roman": ("times.ttf", "timesbd.ttf"),
    "Impact": ("impact.ttf", "impact.ttf"),
    "Comic Sans MS": ("comic.ttf", "comicbd.ttf"),
    "Courier New": ("cour.ttf", "courbd.ttf"),
    "Consolas": ("consola.ttf", "consolab.ttf"),
}
# style d'origine (celui des versions précédentes)
DEFAULT_STYLE = {"font": "Arial", "call": "#ffffff", "text": "#ffffff", "accent": "#ffd166",
                 "band": "#000000", "band_alpha": 60, "call_size": 100,
                 "head_h": 100, "band_h": 100}          # hauteur des bandeaux du haut / du bas (%)
BAND_MIN, BAND_MAX = 50, 150
# 1.68 : blocs de texte déplaçables à la souris (style["pos"] : bloc -> [dx, dy] en fraction de la carte)
BLOCKS = ("call", "loc", "to", "info", "msg")


def card_size(background):
    """2.31 (M7WUV) : taille de la carte = taille et forme de l'image de fond (sans rien couper),
    ramenée à MAX_SIDE au plus ; une petite image est agrandie à 960 px de large au moins."""
    if background is None:
        return W, H
    w, h = background.size
    k = min(1.0, MAX_SIDE / max(w, h))
    if max(w, h) * k < W:
        k = W / max(w, h)
    return max(1, round(w * k)), max(1, round(h * k))


def _offset(st, key, cw=W, ch=H):
    try:
        dx, dy = (st.get("pos") or {}).get(key) or (0, 0)
        return max(-1.0, min(1.0, float(dx))) * cw, max(-1.0, min(1.0, float(dy))) * ch
    except (TypeError, ValueError):
        return 0.0, 0.0
_font_name = "Arial"


def _font(size, bold=False):
    reg, bd = FONTS.get(_font_name, FONTS["Arial"])
    import i18n
    names = list(i18n.cjk_fonts(bold)) + ([bd, "arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"] if bold
                                          else [reg, "arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"])
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _cover(img, w, h):
    """Recadre l'image pour remplir w×h sans déformation."""
    img = img.convert("RGB")
    r = max(w / img.width, h / img.height)
    img = img.resize((max(w, round(img.width * r)), max(h, round(img.height * r))), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def _rgb(c, alpha=None):
    c = (c or "#000000").lstrip("#")
    v = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return v + (alpha,) if alpha is not None else v


def _dim(rgb, k=0.75):
    """Couleur des petites étiquettes (Date UTC, Fréquence…) : le texte, un peu adouci."""
    return tuple(int(v * k + 128 * (1 - k)) for v in rgb[:3])


def make_card(background, mycall, locator="", to_call="", freq="", report="", message="",
              utc=None, style=None, boxes=None, size=None):
    """Retourne la carte (image PIL), à la taille de son fond (card_size) ou à size=(l, h)
    (aperçu). style : police et couleurs (voir DEFAULT_STYLE), et style["pos"] : décalage de
    chaque bloc de texte. boxes (dict) : reçoit le cadre de chaque bloc (x0, y0, x1, y1),
    pour le déplacer à la souris."""
    global _font_name
    st = dict(DEFAULT_STYLE, **(style or {}))
    _font_name = st["font"]
    call_c, text_c, acc_c = _rgb(st["call"]), _rgb(st["text"]), _rgb(st["accent"])
    alpha = int(255 * max(0, min(100, int(st["band_alpha"]))) / 100)
    band_top = _rgb(st["band"], int(alpha * 0.85))
    band_bot = _rgb(st["band"], alpha)
    big = max(0.5, min(1.4, int(st["call_size"]) / 100))
    CW, CH = size or card_size(background)
    S = min(CW / W, CH / H)                               # échelle de la mise en page (960×600 -> 1)
    if background is None:
        card = Image.new("RGB", (CW, CH), "#1d3557")
        g = ImageDraw.Draw(card)
        for y in range(CH):                                # dégradé simple
            c = int(30 + 60 * y / CH)
            g.line([(0, y), (CW, y)], fill=(c // 2, c, 90 + c))
    else:
        card = _cover(background, CW, CH)
    d = ImageDraw.Draw(card, "RGBA")
    import clocktz
    utc = utc or clocktz.fmt("%Y-%m-%d %H:%M", suffix=False)

    # hauteur des bandeaux (demande de RK1AT) : le texte suit la hauteur choisie
    kh = max(BAND_MIN, min(BAND_MAX, int(st.get("head_h") or 100))) / 100
    kb = max(BAND_MIN, min(BAND_MAX, int(st.get("band_h") or 100))) / 100

    def px(v, k):
        return max(8, int(round(v * k * S)))

    M = 28 * S                                            # marge
    # en-tête : indicatif + locator
    head = int(max(120, int(120 * big)) * kh * S)
    if alpha:
        d.rectangle([0, 0, CW, head], fill=band_top)
    box = {} if boxes is None else boxes

    def text(key, xy, txt, font, fill, anchor="la"):
        ox, oy = _offset(st, key, CW, CH)
        xy = (xy[0] + ox, xy[1] + oy)
        d.text(xy, txt, font=font, fill=fill, anchor=anchor)
        b = d.textbbox(xy, txt, font=font, anchor=anchor)
        o = box.get(key)
        box[key] = b if o is None else (min(o[0], b[0]), min(o[1], b[1]), max(o[2], b[2]), max(o[3], b[3]))

    fc = _font(px(76 * big, kh), True)
    text("call", (M, head / 2), mycall.upper(), fc, call_c, "lm")
    if locator:
        text("loc", (CW - M, head / 2 - 8 * kh * S), locator.upper(), _font(px(34, kh), True), acc_c, "rs")
    text("loc", (CW - M, head / 2 + 6 * kh * S), "HFImage", _font(px(22, kh)), _dim(text_c), "ra")

    # bandeau du bas : QSO
    band = int(190 * kb * S)
    if alpha:
        d.rectangle([0, CH - band, CW, CH], fill=band_bot)
    y0 = CH - band + 14 * kb * S
    if to_call:
        text("to", (M, y0), tr(f"To : {to_call.upper()}"), _font(px(40, kb), True), acc_c)
    rows = [(tr("Date UTC") if clocktz.utc() else tr("Date"), utc), (tr("Fréquence"), freq), (tr("Report"), report)]
    x = M
    # date / fréquence / report : la ligne doit tenir dans la largeur de la carte
    kr = kb
    while True:
        fv = _font(px(28, kr), True)
        need = M + sum(max(int(220 * kr * S), int(d.textlength(v, font=fv)) + int(40 * kr * S)) for _, v in rows if v)
        if need <= CW - 10 * S or kr <= 0.5:
            break
        kr *= 0.92
    for lab, val in rows:
        if not val:
            continue
        text("info", (x, y0 + 58 * kb * S), lab, _font(px(18, kr)), _dim(text_c))
        text("info", (x, y0 + 80 * kb * S), val, fv, text_c)
        x += max(int(220 * kr * S), int(d.textlength(val, font=fv)) + int(40 * kr * S))
    if message:
        text("msg", (M, y0 + 128 * kb * S), message, _font(px(26, kb)), text_c)
    return card
