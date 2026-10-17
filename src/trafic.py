"""« Mes conditions de trafic » incrustées sur l'image émise (comme le bandeau d'EasyPal) :
indicatif, locator, poste, puissance, antenne, fréquence, date UTC, texte libre."""
import time

from PIL import Image, ImageDraw, ImageFont

DEFAULT = {"tc_on": False, "tc_rig": "", "tc_power": "", "tc_ant": "", "tc_qth": "", "tc_extra": "",
           "tc_call": True, "tc_loc": True, "tc_freq": True, "tc_date": True, "tc_pos": "bas", "tc_size": "normale"}
SIZES = {"petite": 46.0, "normale": 36.0, "grande": 28.0}      # largeur / taille de police


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
        out.append(time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()))
    if c["tc_extra"]:
        out.append(c["tc_extra"])
    return out


def overlay(img, items, pos="bas", size="normale"):
    """Bandeau semi-transparent avec les conditions de trafic, sur une ou deux lignes."""
    if not items:
        return img
    im = img.convert("RGB").copy()
    fs = max(12, int(im.width / SIZES.get(size, 36.0)))
    font = _font(fs)
    d = ImageDraw.Draw(im, "RGBA")
    sep = "  •  "
    maxw = im.width - 2 * fs
    lines, cur = [], ""
    for it in items:
        test = it if not cur else cur + sep + it
        if d.textlength(test, font=font) <= maxw or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = it
    if cur:
        lines.append(cur)
    lh = int(fs * 1.3)
    h = lh * len(lines) + fs // 2
    y0 = im.height - h if pos == "bas" else 0
    d.rectangle((0, y0, im.width, y0 + h), fill=(0, 0, 0, 150))
    for i, l in enumerate(lines):
        w = d.textlength(l, font=font)
        d.text(((im.width - w) / 2, y0 + fs // 4 + i * lh), l, font=font, fill=(255, 255, 255),
               stroke_width=max(1, fs // 14), stroke_fill=(0, 0, 0))
    return im
