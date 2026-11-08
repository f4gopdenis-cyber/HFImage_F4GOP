"""Mise en ligne des images sur votre site web, comme EasyPal (et donc visibles dans Digi-Sites).

Comme EasyPal, chaque image reçue est envoyée par FTP sous le nom « image1 » (SANS extension :
c'est ce fichier que lit Digi-Sites) ; les précédentes glissent d'un cran (image1 -> image2 …
jusqu'au nombre choisi). Les images
émises vont dans TX1.jpg … TX5.jpg. Chaque image porte une étiquette (indicatif, date UTC,
mode, bande), et une page hfimage.html (rafraîchie toutes les 5 min) les présente.
On ajoute ensuite l'adresse de la page (ou du dossier) dans Digi-Sites (Setup -> Edit site).

Tout se fait dans un fil de fond, une image après l'autre : la réception n'est jamais
ralentie, et une coupure Internet ne bloque rien (l'erreur est notée dans le journal).
"""
import ftplib
import html
import io
import os
import json
import queue
import threading
import time

from PIL import Image, ImageDraw, ImageFont

import hybrid
import imgfmt

PAGE = "hfimage.html"


def remote(prefix, i):
    """Nom sur le serveur : « image1 » sans extension, comme EasyPal (Digi-Sites lit ce fichier) ;
    images émises : « TX1.jpg »."""
    return f"{prefix}{i}" if prefix == "image" else f"{prefix}{i}.jpg"
LIST = "list.txt"
TX_KEEP = 5


_FONT_DIRS = [os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"), "/usr/share/fonts/opentype/noto",
              "/usr/share/fonts/opentype/ipafont-gothic", "/usr/share/fonts/truetype/dejavu",
              "/System/Library/Fonts", "/Library/Fonts"]
# 2.24 (BH2RMX) : police qui sait écrire le chinois, le russe… (la police par défaut affichait des carrés)
_WIDE = ("msyh.ttc", "msyhbd.ttc", "simhei.ttf", "simsun.ttc", "NotoSansCJK-Regular.ttc", "ipagp.ttf",
         "PingFang.ttc")
_LATIN = ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf")


def _label_font(caption, size):
    """Police de l'étiquette : une police « large » (chinois…) si le texte en a besoin."""
    names = (_WIDE + _LATIN) if any(ord(ch) > 0x24F for ch in caption) else (_LATIN + _WIDE)
    for n in names:
        for d in _FONT_DIRS:
            p = os.path.join(d, n)
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except OSError:
                    pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def label_image(path, caption, max_w=1024):
    """JPEG étiqueté (bandeau en bas) prêt à mettre en ligne."""
    im = Image.open(path)
    im.seek(0)
    if getattr(im, "n_frames", 1) == 1:
        im = imgfmt.upright(im)                   # photo de téléphone : dans le bon sens
    im = im.convert("RGB")
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    size = max(13, im.width // 36)
    font = _label_font(caption, size)
    # bandeau AJOUTÉ sous l'image (avant, il était posé sur le bas de la photo et cachait
    # le bandeau de la station émettrice : les deux textes se mélangeaient)
    try:                                           # 2.24 : hauteur du bandeau selon la police réelle
        x0, y0, x1, y1 = font.getbbox(caption)
        th = y1 - y0
    except Exception:
        y0, th = 0, size
    h = max(size, th) + 10
    out = Image.new("RGB", (im.width, im.height + h), (0, 0, 0))
    out.paste(im, (0, 0))
    im = out
    d = ImageDraw.Draw(im)
    d.text((6, im.height - h + 5 - y0), caption, fill=(255, 255, 255), font=font)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88, optimize=True, progressive=True)
    return buf.getvalue(), im.size


def _page(call, rx, tx, n):
    """Page HTML de la galerie (les images sont rechargées sans cache)."""
    def cells(items, prefix, count):
        out = []
        for i in range(1, count + 1):
            # 2.24 (BH2RMX) : plus de texte sous l'image, l'étiquette SUR l'image dit déjà tout
            cap = html.escape(items[i - 1]["caption"]) if i <= len(items) else ""
            out.append(f'<figure><a href="{remote(prefix, i)}"><img src="{remote(prefix, i)}" alt="{cap}" '
                       f'title="{cap}" onerror="this.closest(\'figure\').style.display=\'none\'"></a></figure>')
        return "\n".join(out)
    title = html.escape(f"{call} — HFImage")
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="300">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body{{background:#111;color:#eee;font-family:Segoe UI,Arial,sans-serif;margin:0;padding:12px}}
h1{{font-size:20px;margin:4px 0 2px}} h2{{font-size:16px;color:#7fd47f;margin:18px 0 6px}}
p{{color:#aaa;font-size:13px;margin:0 0 8px}}
.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px}}
figure{{margin:0;background:#222;border:1px solid #333}} img{{width:100%;display:block}}
figcaption{{font-size:12px;padding:3px 6px;color:#ddd}}
</style>
<script>addEventListener('load',()=>{{const t=Date.now();document.querySelectorAll('img').forEach(i=>i.src=i.getAttribute('src')+'?'+t)}})</script>
</head><body>
<h1>{title}</h1>
<p>Images numériques reçues en HF avec HFImage F4GOP — page rafraîchie toutes les 5 minutes.
Mise à jour : {__import__('clocktz').fmt('%Y-%m-%d %H:%M')}</p>
<h2>Images reçues</h2>
<div class="g">
{cells(rx, "image", n)}
</div>
<h2>Images émises</h2>
<div class="g">
{cells(tx, "TX", TX_KEEP)}
</div>
</body></html>
"""


class WebSync:
    """File d'envoi FTP (un fil de fond)."""

    def __init__(self, state_path, log=lambda m: None):
        self.state_path = state_path
        self.log = log
        self.q = queue.Queue()
        self.state = {"rx": [], "tx": []}
        try:
            with open(state_path, encoding="utf-8") as f:
                self.state.update(json.load(f))
        except (OSError, ValueError):
            pass
        threading.Thread(target=self._run, daemon=True).start()

    def _save(self):
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=0)
        except OSError:
            pass

    # ------------------------------------------------------------------ API
    def add(self, cfg, kind, path, caption):
        """kind : « rx » ou « tx »."""
        self.q.put(("img", dict(cfg), kind, path, caption))

    def page(self, cfg):
        self.q.put(("page", dict(cfg), None, None, None))

    def resync(self, cfg, rx, tx):
        """Remet en ligne d'un coup les dernières images (« Envoyer la page maintenant ») :
        rx / tx = [(chemin, légende)], de la plus récente à la plus ancienne. Utile après un
        changement de dossier : pas besoin d'attendre la prochaine image reçue."""
        self.q.put(("sync", dict(cfg), None, (list(rx), list(tx)), None))

    # ------------------------------------------------------------------ fil d'envoi
    def _run(self):
        while True:
            job = self.q.get()
            try:
                self._do(*job)
            except Exception as e:
                self.log(f"Site web : envoi impossible ({e})")

    def _do(self, what, cfg, kind, path, caption):
        n = max(1, min(60, int(cfg.get("count") or 20)))
        data = None
        if what == "img":
            data, _size = label_image(path, caption)
        ftp = hybrid._ftp_connect(cfg)
        done = {"rx": 0, "tx": 0}
        try:
            hybrid._ftp_cd(ftp, cfg.get("dir"))
            if what == "sync":
                for kind, items, prefix, keep in (("rx", path[0], "image", n), ("tx", path[1], "TX", TX_KEEP)):
                    lst = []
                    for src, cap in items:
                        if len(lst) >= keep:
                            break
                        try:
                            blob, _size = label_image(src, cap)
                        except Exception:
                            continue                              # fichier effacé ou illisible
                        ftp.storbinary(f"STOR {remote(prefix, len(lst) + 1)}", io.BytesIO(blob))
                        lst.append({"caption": cap, "t": time.time()})
                    if lst:
                        self.state[kind] = lst
                        done[kind] = len(lst)
                self._save()
            if what == "img":
                prefix, keep = ("image", n) if kind == "rx" else ("TX", TX_KEEP)
                self._rotate(ftp, prefix, keep)
                ftp.storbinary(f"STOR {remote(prefix, 1)}", io.BytesIO(data))
                lst = self.state.setdefault(kind, [])
                lst.insert(0, {"caption": caption, "t": time.time()})
                del lst[keep:]
                self._save()
            rx, tx = self.state.get("rx", []), self.state.get("tx", [])
            page = _page(cfg.get("call") or "", rx, tx, n).encode("utf-8")
            ftp.storbinary(f"STOR {PAGE}", io.BytesIO(page))
            text = "\n".join(e["caption"] for e in rx[:10]) + "\n"
            ftp.storbinary(f"STOR {LIST}", io.BytesIO(text.encode("utf-8")))
        finally:
            try:
                ftp.quit()
            except Exception:
                ftp.close()
        if what == "img":
            self.log(f"Site web : {'image reçue' if kind == 'rx' else 'image émise'} mise en ligne ({caption})")
        elif what == "sync":
            self.log(f"Site web : page et images remises en ligne ({done['rx']} reçue(s), {done['tx']} émise(s)).")
        else:
            self.log("Site web : page mise en ligne.")

    @staticmethod
    def _rotate(ftp, prefix, keep):
        """image1 -> image2 … (la plus ancienne est effacée)."""
        try:
            ftp.delete(remote(prefix, keep))
        except ftplib.all_errors:
            pass
        for i in range(keep - 1, 0, -1):
            try:
                ftp.rename(remote(prefix, i), remote(prefix, i + 1))
            except ftplib.all_errors:
                pass                                  # pas encore d'image à ce rang


def digisites_url(cfg):
    """Adresse à donner à Digi-Sites : le fichier image1 lui-même (vérifié avec Digi-Sites)."""
    base = (cfg.get("url") or "").strip()
    return base.rstrip("/") + "/" + remote("image", 1) if base else ""


def page_url(cfg):
    base = (cfg.get("url") or "").strip()
    if not base:
        return ""
    return base.rstrip("/") + "/" + PAGE
