"""« Sites des stations » : la dernière image reçue par chaque station, comme Digi-Sites.

Digi-Sites (W3WV) n'est plus entretenu. Ici, chaque HFImage qui met ses images en ligne
(Site web / Digi-Sites) annonce l'adresse de son fichier « image1 » dans sa présence Internet ;
cette fenêtre montre une vignette par station en ligne, relue régulièrement (seulement si le
fichier a changé : requête conditionnelle). On peut aussi ajouter à la main le site d'une
station EasyPal (adresse de son image1).

Sécurité : les adresses viennent d'autres stations : http / https seulement, serveurs publics
seulement (jamais l'ordinateur ni le réseau de la maison), 5 Mo au plus par image.
"""
import netssl
import email.utils
import io
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
from tkinter import messagebox, simpledialog, ttk

import hybrid
from i18n import tr

MAX_BYTES = 5_000_000
POLL_S = 120                     # chaque station relue toutes les 2 minutes (si le fichier a changé)
TW, TH = 200, 150                # taille des vignettes


def valid_url(url):
    return isinstance(url, str) and len(url) <= 300 and url.lower().startswith(("http://", "https://"))


def fetch(url, etag="", lastmod="", timeout=15):
    """-> (None, etag, lastmod) si inchangé, sinon (octets, etag, lastmod). Serveurs publics seulement."""
    hybrid._check_url(url)
    hybrid._check_public_url(url)
    headers = {"User-Agent": hybrid.USER_AGENT}
    if etag:
        headers["If-None-Match"] = etag
    if lastmod:
        headers["If-Modified-Since"] = lastmod
    req = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=netssl.context()),
                                         hybrid._PublicRedirect())
    try:
        with opener.open(req, timeout=timeout) as r:
            data = r.read(MAX_BYTES + 1)
            et, lm = r.headers.get("ETag", ""), r.headers.get("Last-Modified", "")
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return None, etag, lastmod
        raise RuntimeError(f"HTTP {e.code}") from e
    if len(data) > MAX_BYTES:
        raise RuntimeError("image trop grosse")
    return data, et, lm


def when_text(lastmod):
    """« Last-Modified » du serveur -> heure locale « 14:32 » (ou « 23/10 14:32 » si pas aujourd'hui)."""
    try:
        t = email.utils.parsedate_to_datetime(lastmod).timestamp()
    except (TypeError, ValueError, IndexError):
        return ""
    lt = time.localtime(t)
    return time.strftime("%H:%M" if time.strftime("%Y%m%d", lt) == time.strftime("%Y%m%d") else "%d/%m %H:%M", lt)


class SitesWindow(tk.Toplevel):
    """Grille de vignettes : une par station (en ligne avec un site, ou ajoutée à la main)."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Sites des stations")
        self.geometry("900x620")
        self.cache = {}            # url -> {"img", "etag", "lastmod", "t", "err", "raw"}
        self.cards = []
        self._ph = []
        self._closing = False
        self._busy = set()
        top = ttk.Frame(self, padding=(8, 6))
        top.pack(fill="x")
        self.lb = ttk.Label(top, text="")
        self.lb.pack(side="left")
        ttk.Button(top, text="Ajouter une station…", command=self.add_site).pack(side="right")
        ttk.Button(top, text="Actualiser", command=lambda: self.refresh(force=True)).pack(side="right", padx=6)
        self.cv = tk.Canvas(self, bg="#1d2b1d", highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.cv.yview)
        self.cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Configure>", lambda e: self.redraw())
        self.cv.bind("<MouseWheel>", lambda e: self.cv.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        self.cv.bind("<Button-4>", lambda e: self.cv.yview_scroll(-1, "units"))
        self.cv.bind("<Button-5>", lambda e: self.cv.yview_scroll(1, "units"))
        self.protocol("WM_DELETE_WINDOW", self.close)
        app._translate_ui(self)
        self.refresh(force=True)
        self._tick()

    # ------------------------------------------------------------------ données
    def stations(self):
        """[(indicatif, adresse image1, en ligne ?)] : stations en ligne qui ont un site, puis
        les sites ajoutés à la main (stations EasyPal…)."""
        out, seen = [], set()
        for d in list(self.app.online.values()):
            call, url = str(d.get("call") or ""), d.get("site")
            if call and valid_url(url) and call not in seen:
                out.append((call, url, True))
                seen.add(call)
        for e in self.app.conf.get("sites_extra", []):
            call, url = str(e.get("call", "")).upper(), e.get("url")
            if call and valid_url(url) and call not in seen:
                online = any(str(d.get("call")) == call for d in self.app.online.values())
                out.append((call, url, online))
                seen.add(call)
        return out

    def refresh(self, force=False):
        now = time.time()
        for call, url, _on in self.stations():
            c = self.cache.get(url)
            if url in self._busy or (c and not force and now - c["t"] < POLL_S):
                continue
            self._busy.add(url)
            threading.Thread(target=self._load, args=(url,), daemon=True).start()
        self.redraw()

    def _load(self, url):
        c = dict(self.cache.get(url) or {"img": None, "etag": "", "lastmod": "", "raw": None})
        try:
            data, et, lm = fetch(url, c["etag"], c["lastmod"])
            if data is not None:
                from PIL import Image
                import imgfmt
                im = imgfmt.upright(Image.open(io.BytesIO(data)))
                im = im.convert("RGB")
                c["raw"] = im.copy()
                im.thumbnail((TW, TH), Image.LANCZOS)
                c.update(img=im, etag=et, lastmod=lm or c["lastmod"])
            c["err"] = ""
        except Exception as e:
            c["err"] = str(e)[:60]
        c["t"] = time.time()
        if not self._closing:
            self.app.ui(self._loaded, url, c)

    def _loaded(self, url, c):
        self._busy.discard(url)
        self.cache[url] = c
        if not self._closing and self.winfo_exists():
            self.redraw()

    # ------------------------------------------------------------------ affichage
    def redraw(self):
        if self._closing or not self.winfo_exists():
            return
        cv = self.cv
        cv.delete("all")
        self._ph = []
        sts = self.stations()
        # les plus récentes d'abord (fichier modifié le plus récemment), puis les autres
        def key(s):
            c = self.cache.get(s[1]) or {}
            try:
                return -email.utils.parsedate_to_datetime(c.get("lastmod")).timestamp()
            except (TypeError, ValueError, IndexError):
                return 0
        sts.sort(key=key)
        self.lb.configure(text=f"{len(sts)} " + tr("station(s) avec un site — relues toutes les 2 minutes"))
        W = max(cv.winfo_width(), TW + 20)
        cw, ch = TW + 16, TH + 52
        cols = max(1, W // cw)
        self.cards = []
        for k, (call, url, online) in enumerate(sts):
            x, y = 8 + (k % cols) * cw, 8 + (k // cols) * ch
            c = self.cache.get(url) or {}
            cv.create_rectangle(x, y, x + TW + 8, y + TH + 44, fill="#2b3d2b", outline="#5f8f5c")
            if c.get("img") is not None:
                from PIL import ImageTk
                ph = ImageTk.PhotoImage(c["img"])
                self._ph.append(ph)
                cv.create_image(x + 4 + TW // 2, y + 4 + TH // 2, image=ph)
            else:
                msg = c.get("err") or ("…" if url in self._busy or not c else tr("pas d'image"))
                cv.create_text(x + 4 + TW // 2, y + 4 + TH // 2, text=msg, fill="#cfe8cf", width=TW - 10)
            label = self.app._label(call)
            cv.create_text(x + 6, y + TH + 10, text=label, anchor="w", fill="#ffffff" if online else "#a8c8a8",
                           font=("TkDefaultFont", 9, "bold"))
            sub = []
            if c.get("lastmod"):
                sub.append(tr("image du") + " " + when_text(c["lastmod"]))
            dist = self.app._distance_to(call)
            if dist is not None:
                sub.append(f"{dist:.0f} km")
            cv.create_text(x + 6, y + TH + 28, text="  ·  ".join(sub), anchor="w", fill="#cfe8cf",
                           font=("TkDefaultFont", 8))
            self.cards.append((x, y, x + TW + 8, y + TH + 44, call, url))
        rows = (len(sts) + cols - 1) // cols
        cv.configure(scrollregion=(0, 0, W, max(rows * ch + 16, cv.winfo_height())))
        cv.bind("<Button-1>", self._click)
        cv.bind("<Button-3>", self._menu)
        if not sts:
            cv.create_text(W // 2, 80, fill="#cfe8cf", width=W - 60, justify="center",
                           text=tr("Aucune station en ligne n'a encore de site. Les stations HFImage "
                                             "apparaissent ici dès qu'elles mettent leurs images en ligne "
                                             "(Images → Site web / Digi-Sites). « Ajouter une station… » pour le "
                                             "site d'une station EasyPal."))

    def _hit(self, e):
        x, y = self.cv.canvasx(e.x), self.cv.canvasy(e.y)
        return next((c for c in self.cards if c[0] <= x <= c[2] and c[1] <= y <= c[3]), None)

    def _click(self, e):
        c = self._hit(e)
        if c is None:
            return
        data = self.cache.get(c[5]) or {}
        if data.get("raw") is None:
            return
        w = tk.Toplevel(self)
        w.title(f"{self.app._label(c[4])} — {when_text(data.get('lastmod', ''))}")
        w.geometry("820x640")
        from panel import ImageView
        v = ImageView(w)
        v.pack(fill="both", expand=True)
        v.set_image(data["raw"])

    def _menu(self, e):
        c = self._hit(e)
        if c is None:
            return
        m = tk.Menu(self, tearoff=0)
        page = c[5].rsplit("/", 1)[0] + "/hfimage.html"
        m.add_command(label=tr("Ouvrir la page de la station"),
                      command=lambda: __import__("webbrowser").open(page))
        m.add_command(label=tr("Ouvrir l'image dans le navigateur"),
                      command=lambda: __import__("webbrowser").open(c[5]))
        if any(str(x.get("call", "")).upper() == c[4] for x in self.app.conf.get("sites_extra", [])):
            m.add_separator()
            m.add_command(label=tr("Retirer cette station"), command=lambda: self.remove_site(c[4]))
        m.tk_popup(e.x_root, e.y_root)

    # ------------------------------------------------------------------ sites ajoutés à la main
    def add_site(self):
        call = simpledialog.askstring(tr("Ajouter une station"), tr("Indicatif de la station :"), parent=self)
        if not call:
            return
        url = simpledialog.askstring(tr("Ajouter une station"),
                                     tr("Adresse de son image (celle donnée à Digi-Sites), par exemple :")
                                     + "\nhttps://www.qsl.net/f4gop/image1", parent=self)
        if not url:
            return
        url = url.strip()
        if not valid_url(url):
            messagebox.showerror("HFImage", tr("Adresse refusée : elle doit commencer par http:// ou https://."),
                                 parent=self)
            return
        call = "".join(ch for ch in call.upper() if ch.isalnum() or ch in "/-")[:16]
        lst = [e for e in self.app.conf.get("sites_extra", []) if str(e.get("call", "")).upper() != call]
        lst.append({"call": call, "url": url})
        self.app.conf["sites_extra"] = lst[-100:]
        self.app._save_conf_file()
        self.refresh(force=True)

    def remove_site(self, call):
        self.app.conf["sites_extra"] = [e for e in self.app.conf.get("sites_extra", [])
                                        if str(e.get("call", "")).upper() != call]
        self.app._save_conf_file()
        self.redraw()

    # ------------------------------------------------------------------ cycle
    def _tick(self):
        if self._closing or not self.winfo_exists():
            return
        self.refresh()
        self.after(15000, self._tick)

    def alive(self):
        return not self._closing and self.winfo_exists()

    def close(self):
        self._closing = True
        self.destroy()
