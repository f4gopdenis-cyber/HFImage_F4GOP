"""Carte QSL : photo de fond + bandeau avec indicatifs, date UTC, fréquence, report."""

from i18n import tr

from PIL import Image, ImageDraw, ImageFont

W, H = 960, 600

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


def _offset(st, key):
    try:
        dx, dy = (st.get("pos") or {}).get(key) or (0, 0)
        return max(-1.0, min(1.0, float(dx))) * W, max(-1.0, min(1.0, float(dy))) * H
    except (TypeError, ValueError):
        return 0.0, 0.0
_font_name = "Arial"


def _font(size, bold=False):
    reg, bd = FONTS.get(_font_name, FONTS["Arial"])
    names = ([bd, "arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"] if bold
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
              utc=None, style=None, boxes=None):
    """Retourne une image PIL 960×600. style : police et couleurs (voir DEFAULT_STYLE), et
    style["pos"] : décalage de chaque bloc de texte. boxes (dict) : reçoit le cadre de chaque
    bloc (x0, y0, x1, y1), pour le déplacer à la souris."""
    global _font_name
    st = dict(DEFAULT_STYLE, **(style or {}))
    _font_name = st["font"]
    call_c, text_c, acc_c = _rgb(st["call"]), _rgb(st["text"]), _rgb(st["accent"])
    alpha = int(255 * max(0, min(100, int(st["band_alpha"]))) / 100)
    band_top = _rgb(st["band"], int(alpha * 0.85))
    band_bot = _rgb(st["band"], alpha)
    big = max(0.5, min(1.4, int(st["call_size"]) / 100))
    if background is None:
        card = Image.new("RGB", (W, H), "#1d3557")
        g = ImageDraw.Draw(card)
        for y in range(H):                                 # dégradé simple
            c = int(30 + 60 * y / H)
            g.line([(0, y), (W, y)], fill=(c // 2, c, 90 + c))
    else:
        card = _cover(background, W, H)
    d = ImageDraw.Draw(card, "RGBA")
    import clocktz
    utc = utc or clocktz.fmt("%Y-%m-%d %H:%M", suffix=False)

    # hauteur des bandeaux (demande de RK1AT) : le texte suit la hauteur choisie
    kh = max(BAND_MIN, min(BAND_MAX, int(st.get("head_h") or 100))) / 100
    kb = max(BAND_MIN, min(BAND_MAX, int(st.get("band_h") or 100))) / 100

    def px(v, k):
        return max(8, int(round(v * k)))

    # en-tête : indicatif + locator
    head = int(max(120, int(120 * big)) * kh)
    if alpha:
        d.rectangle([0, 0, W, head], fill=band_top)
    box = {} if boxes is None else boxes

    def text(key, xy, txt, font, fill, anchor="la"):
        ox, oy = _offset(st, key)
        xy = (xy[0] + ox, xy[1] + oy)
        d.text(xy, txt, font=font, fill=fill, anchor=anchor)
        b = d.textbbox(xy, txt, font=font, anchor=anchor)
        o = box.get(key)
        box[key] = b if o is None else (min(o[0], b[0]), min(o[1], b[1]), max(o[2], b[2]), max(o[3], b[3]))

    fc = _font(px(76 * big, kh), True)
    text("call", (28, head / 2), mycall.upper(), fc, call_c, "lm")
    if locator:
        text("loc", (W - 28, head / 2 - 8 * kh), locator.upper(), _font(px(34, kh), True), acc_c, "rs")
    text("loc", (W - 28, head / 2 + 6 * kh), "HFImage", _font(px(22, kh)), _dim(text_c), "ra")

    # bandeau du bas : QSO
    band = int(190 * kb)
    if alpha:
        d.rectangle([0, H - band, W, H], fill=band_bot)
    y0 = H - band + 14 * kb
    if to_call:
        text("to", (28, y0), tr(f"To : {to_call.upper()}"), _font(px(40, kb), True), acc_c)
    rows = [(tr("Date UTC") if clocktz.utc() else tr("Date"), utc), (tr("Fréquence"), freq), (tr("Report"), report)]
    x = 28
    # date / fréquence / report : la ligne doit tenir dans la largeur de la carte
    kr = kb
    while True:
        fv = _font(px(28, kr), True)
        need = 28 + sum(max(int(220 * kr), int(d.textlength(v, font=fv)) + int(40 * kr)) for _, v in rows if v)
        if need <= W - 10 or kr <= 0.5:
            break
        kr *= 0.92
    for lab, val in rows:
        if not val:
            continue
        text("info", (x, y0 + 58 * kb), lab, _font(px(18, kr)), _dim(text_c))
        text("info", (x, y0 + 80 * kb), val, fv, text_c)
        x += max(int(220 * kr), int(d.textlength(val, font=fv)) + int(40 * kr))
    if message:
        text("msg", (28, y0 + 128 * kb), message, _font(px(26, kb)), text_c)
    return card
