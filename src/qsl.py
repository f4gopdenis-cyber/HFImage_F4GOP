"""Carte QSL : photo de fond + bandeau avec indicatifs, date UTC, fréquence, report."""
import time

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
                 "band": "#000000", "band_alpha": 60, "call_size": 100}
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
              utc=None, style=None):
    """Retourne une image PIL 960×600. style : police et couleurs (voir DEFAULT_STYLE)."""
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
    utc = utc or time.strftime("%Y-%m-%d %H:%M", time.gmtime())

    # en-tête : indicatif + locator
    head = max(120, int(120 * big))
    if alpha:
        d.rectangle([0, 0, W, head], fill=band_top)
    fc = _font(int(76 * big), True)
    d.text((28, head / 2), mycall.upper(), font=fc, fill=call_c, anchor="lm")
    if locator:
        d.text((W - 28, head / 2 - 8), locator.upper(), font=_font(34, True), fill=acc_c, anchor="rs")
    d.text((W - 28, head / 2 + 6), "HFImage", font=_font(22), fill=_dim(text_c), anchor="ra")

    # bandeau du bas : QSO
    if alpha:
        d.rectangle([0, H - 190, W, H], fill=band_bot)
    y0 = H - 176
    if to_call:
        d.text((28, y0), tr(f"To : {to_call.upper()}"), font=_font(40, True), fill=acc_c)
    rows = [(tr("Date UTC"), utc), (tr("Fréquence"), freq), (tr("Report"), report)]
    x = 28
    for lab, val in rows:
        if not val:
            continue
        d.text((x, y0 + 58), lab, font=_font(18), fill=_dim(text_c))
        d.text((x, y0 + 80), val, font=_font(28, True), fill=text_c)
        x += max(220, int(d.textlength(val, font=_font(28, True))) + 40)
    if message:
        d.text((28, y0 + 128), message, font=_font(26), fill=text_c)
    return card
