"""Formats d'image à l'émission et à la réception : JPEG / JPG, SVG, fichier « original ».

- « original » : le fichier ouvert part tel quel, sans recompression (JPG, PNG, GIF, AVIF, WEBP).
- SVG : le dessin vectoriel part en texte, nettoyé et compressé gzip (souvent quelques
  centaines d'octets), et la station qui reçoit le redessine à n'importe quelle taille.
  Pour l'afficher (et pour l'envoyer en AVIF / WEBP / JPEG), il est rendu avec resvg.
"""
import gzip
import io
import os
import re

from PIL import Image

SVG_RENDER_W = 1280          # largeur de rendu d'un SVG pour l'affichage et la conversion


def is_svg(data: bytes) -> bool:
    if data[:2] == b"\x1f\x8b":
        try:
            data = gzip.decompress(data)
        except OSError:
            return False
    head = data[:2048].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    return head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in data[:4096].lower()) \
        or (head.startswith(b"<!--") and b"<svg" in data[:4096].lower()) \
        or (head.startswith(b"<!doctype svg"))


def svg_text(data: bytes) -> bytes:
    """SVG brut (décompressé si .svgz)."""
    return gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data


def svg_minify(svg: bytes) -> bytes:
    """Retire commentaires, métadonnées d'éditeur et espaces inutiles (le dessin ne change pas)."""
    s = svg.decode("utf-8", errors="replace")
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<metadata\b.*?</metadata>", "", s, flags=re.S | re.I)
    s = re.sub(r">\s+<", "><", s)
    s = re.sub(r"[ \t\r\n]+", " ", s)
    return s.strip().encode("utf-8")


def svg_pack(svg: bytes) -> bytes:
    """SVG -> données radio : nettoyé puis gzip (mtime=0 : même fichier = mêmes octets)."""
    return gzip.compress(svg_minify(svg_text(svg)), compresslevel=9, mtime=0)


def render_svg(data: bytes, width=SVG_RENDER_W) -> Image.Image:
    """SVG (ou SVGZ) -> image PIL sur fond blanc."""
    import resvg_py
    svg = svg_text(data).decode("utf-8", errors="replace")
    try:
        png = resvg_py.svg_to_bytes(svg_string=svg, width=width, background="white")
    except Exception:
        png = resvg_py.svg_to_bytes(svg_string=svg, background="white")   # sans taille imposée
    return Image.open(io.BytesIO(bytes(png))).convert("RGB")


def load_source(path):
    """Fichier ouvert pour l'émission -> (image affichable, octets bruts, type)."""
    with open(path, "rb") as f:
        raw = f.read()
    if path.lower().endswith((".svg", ".svgz")) or is_svg(raw):
        return render_svg(raw), raw, "svg"
    img = Image.open(io.BytesIO(raw))
    kind = (img.format or "bin").lower()
    return img.convert("RGB"), raw, kind


def original_payload(raw: bytes, kind: str, hybrid=False) -> bytes:
    """Octets envoyés en mode « original ». En hybride, le SVG reste en clair pour être
    lisible directement dans un navigateur."""
    if kind == "svg":
        return svg_minify(svg_text(raw)) if hybrid else svg_pack(raw)
    return raw


EXT = {"jpeg": "jpg", "svg": "svg", "png": "png", "gif": "gif", "avif": "avif", "webp": "webp"}


def ext_for(fmt: str) -> str:
    return EXT.get(fmt, fmt or "bin")


def save_received(base: str, fmt: str, data: bytes):
    """Enregistre un fichier reçu -> (chemin, png pour l'affichage ou None)."""
    if fmt == "svg":
        path = base + ".svg"
        with open(path, "wb") as f:
            f.write(svg_text(data))
        try:
            render_svg(data).save(base + ".png")
            return path, base + ".png"
        except Exception:
            return path, None
    path = f"{base}.{ext_for(fmt)}"
    with open(path, "wb") as f:
        f.write(data)
    if path.endswith(".png"):
        return path, path
    try:
        Image.open(io.BytesIO(data)).save(base + ".png")
        return path, base + ".png"
    except Exception:
        return path, None


def describe(kind: str) -> str:
    return {"jpeg": "JPEG", "svg": "SVG", "png": "PNG", "gif": "GIF", "avif": "AVIF",
            "webp": "WEBP"}.get(kind, kind.upper())


def file_kind_label(path):
    return os.path.splitext(path)[1].lstrip(".").upper()


# ------------------------------------------------------------------ GIF animés
GIF_MAX_FRAMES = 400          # au-delà, l'affichage ne garde qu'une image sur deux…


def gif_info(data: bytes):
    """-> (nombre d'images, durée totale en s) ; (1, 0) pour un GIF fixe."""
    try:
        im = Image.open(io.BytesIO(data))
        n = getattr(im, "n_frames", 1)
        total = 0
        for i in range(n):
            im.seek(i)
            total += im.info.get("duration", 100) or 100
        return n, total / 1000
    except Exception:
        return 1, 0.0


def is_animated_gif(data: bytes) -> bool:
    return data[:6] in (b"GIF87a", b"GIF89a") and gif_info(data)[0] > 1


def gif_frames(src, max_frames=GIF_MAX_FRAMES):
    """GIF (octets ou chemin) -> ([images RGB], [durées ms]) pour l'animation à l'écran."""
    from PIL import ImageSequence
    im = Image.open(io.BytesIO(src) if isinstance(src, (bytes, bytearray)) else src)
    frames, durs = [], []
    for fr in ImageSequence.Iterator(im):
        frames.append(fr.convert("RGB"))
        durs.append(max(20, fr.info.get("duration", 100) or 100))
    step = max(1, -(-len(frames) // max_frames))
    if step > 1:                               # trop d'images : on en saute, durée conservée
        frames = frames[::step]
        durs = [sum(durs[i:i + step]) for i in range(0, len(durs), step)]
    return frames, durs


def _gif_encode(frames, durs, scale, colors, keep_every):
    fr = frames[::keep_every]
    du = [sum(durs[i:i + keep_every]) for i in range(0, len(durs), keep_every)]
    if scale < 1:
        w, h = frames[0].size
        size = (max(16, int(w * scale)), max(16, int(h * scale)))
        fr = [f.resize(size, Image.LANCZOS) for f in fr]
    # une seule palette pour toute l'animation (prise sur quelques images) : les images
    # successives restent comparables et le GIF ne stocke que ce qui change
    picks = fr[:: max(1, len(fr) // 6)][:6]
    w, h = fr[0].size
    mont = Image.new("RGB", (w, h * len(picks)))
    for i, f in enumerate(picks):
        mont.paste(f, (0, h * i))
    ref = mont.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = [f.quantize(palette=ref, dither=Image.Dither.NONE) for f in fr]
    buf = io.BytesIO()
    pal[0].save(buf, "GIF", save_all=True, append_images=pal[1:], duration=du, loop=0,
                optimize=True, disposal=1)
    return buf.getvalue()


def gif_shrink(data: bytes, max_bytes: int):
    """Réduit un GIF animé trop lourd pour le serveur en gardant l'animation :
    moins de couleurs, puis plus petit, puis une image sur deux.
    -> (octets, description du traitement) ; data inchangé s'il tient déjà."""
    if len(data) <= max_bytes:
        return data, ""
    frames, durs = gif_frames(data, max_frames=10 ** 6)
    last = None
    for keep, colors in ((1, 128), (1, 64), (2, 64), (3, 32)):
        # première estimation : la taille varie à peu près comme la surface
        full = _gif_encode(frames, durs, 1.0, colors, keep)
        scale = min(1.0, (max_bytes / len(full)) ** 0.5 * 1.05)
        while True:
            d = full if scale >= 1.0 else _gif_encode(frames, durs, scale, colors, keep)
            last = (d, f"réduit : {int(scale * 100)} %, {colors} couleurs"
                       + (f", 1 image sur {keep}" if keep > 1 else ""))
            if len(d) <= max_bytes:
                return last
            if scale <= 0.25:
                break
            scale = max(0.25, scale * 0.88)
    return last
    return last
