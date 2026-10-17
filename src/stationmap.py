"""Carte des stations (façon « Digi-Sites » d'EasyPal).

Fond de carte dessiné par le programme à partir de Natural Earth (domaine public) :
pays en couleurs pastel, frontières, lacs, villes, méridiens/parallèles. Notre station
(étiquette blanche) et les stations qui ont reçu l'image (étiquettes vertes, reliées à
nous par un trait), placées d'après leur locator.

Projection équirectangulaire corrigée par cos(latitude du centre) : simple et fidèle
à l'échelle d'un continent ; trajets en arc de grand cercle.
"""
import json
import math
import os
import sys
import zlib

from PIL import Image, ImageDraw, ImageFont

_DATA = None

OCEAN = (190, 226, 247)
BORDER = (110, 110, 110)
LAKE = (170, 214, 242)
GRID = (150, 190, 215)
# couleurs « carte politique » (MAPCOLOR7 de Natural Earth : pays voisins différents)
PALETTE = {1: (247, 214, 222), 2: (214, 238, 198), 3: (251, 240, 180), 4: (253, 214, 178),
           5: (222, 214, 240), 6: (250, 226, 200), 7: (205, 232, 222)}
GREEN = (51, 214, 51)
LINE = (20, 140, 20)

# vues prédéfinies : (centre lon, centre lat, largeur en degrés de longitude)
VIEWS = {
    "Europe": (14.0, 52.0, 70.0),
    "France": (2.5, 46.6, 17.0),
    "Monde": (10.0, 20.0, 360.0),
    "Amérique du Nord": (-95.0, 45.0, 90.0),
    "Atlantique Nord": (-35.0, 45.0, 120.0),
    "Asie": (100.0, 35.0, 110.0),
    "Océanie": (145.0, -25.0, 80.0),
}


def _font(size, bold=False):
    names = (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"])
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def load():
    global _DATA
    if _DATA is None:
        here = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(here, "carte.bin"), "rb") as f:
            _DATA = json.loads(zlib.decompress(f.read()))
        # décodage des contours (deltas en centièmes de degré)
        def dec(r):
            x, y = r[0], r[1]
            pts = [(x / 100, y / 100)]
            for i in range(2, len(r), 2):
                x += r[i]
                y += r[i + 1]
                pts.append((x / 100, y / 100))
            return pts
        for c in _DATA["countries"]:
            c["r"] = [dec(r) for r in c["r"]]
            xs = [p[0] for r in c["r"] for p in r]
            ys = [p[1] for r in c["r"] for p in r]
            c["bb"] = (min(xs), min(ys), max(xs), max(ys)) if xs else (0, 0, 0, 0)
        _DATA["lakes"] = [dec(r) for r in _DATA["lakes"]]
    return _DATA


def distance_km(a, b):
    """Distance orthodromique entre deux (lat, lon)."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(h)))


def bearing(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def _great_circle(a, b, n=48):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    d = 2 * math.asin(min(1.0, math.sqrt(math.sin((la2 - la1) / 2) ** 2 +
                                         math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)))
    if d < 1e-9:
        return [a, b]
    pts = []
    for i in range(n + 1):
        f = i / n
        A = math.sin((1 - f) * d) / math.sin(d)
        B = math.sin(f * d) / math.sin(d)
        x = A * math.cos(la1) * math.cos(lo1) + B * math.cos(la2) * math.cos(lo2)
        y = A * math.cos(la1) * math.sin(lo1) + B * math.cos(la2) * math.sin(lo2)
        z = A * math.sin(la1) + B * math.sin(la2)
        pts.append((math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))))
    return pts


class View:
    """Centre (lon, lat) + échelle (pixels par degré de longitude)."""

    def __init__(self, lon, lat, span_deg, w, h):
        self.lon, self.lat, self.w, self.h = lon, lat, w, h
        self.ppd = w / span_deg
        self._k = max(0.2, math.cos(math.radians(max(-70, min(70, lat)))))

    @property
    def kx(self):
        return self.ppd

    def xy(self, lon, lat, wrap=True):
        dl = lon - self.lon
        if wrap:
            if dl > 180:
                dl -= 360
            elif dl < -180:
                dl += 360
        return (self.w / 2 + dl * self.ppd, self.h / 2 - (lat - self.lat) * self.ppd / self._k)

    def lonlat(self, x, y):
        return (self.lon + (x - self.w / 2) / self.ppd, self.lat - (y - self.h / 2) * self._k / self.ppd)

    def span(self):
        return self.w / self.ppd

    def bbox(self):
        lo0, la1 = self.lonlat(0, 0)
        lo1, la0 = self.lonlat(self.w, self.h)
        return lo0, la0, lo1, la1


def fit_view(points, w, h, margin=0.25, min_span=8.0):
    """Vue qui contient tous les points (lat, lon)."""
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    lat = (min(lats) + max(lats)) / 2
    lon = (min(lons) + max(lons)) / 2
    k = max(0.2, math.cos(math.radians(lat)))
    span_x = (max(lons) - min(lons)) * (1 + 2 * margin)
    span_y = (max(lats) - min(lats)) * (1 + 2 * margin) / k * (w / h)
    return View(lon, lat, min(360.0, max(min_span, span_x, span_y)), w, h)


def render(view, stations=(), me=None, lang="fr", show_lines=True):
    """-> image PIL de la carte.
    stations : [{"call", "pos": (lat, lon), "ok": bool, "info": str}] ; me : idem pour nous."""
    d_ = load()
    W, H = view.w, view.h
    img = Image.new("RGB", (W, H), OCEAN)
    g = ImageDraw.Draw(img)
    lo0, la0, lo1, la1 = view.bbox()
    wide = view.span() > 300

    def shifts(bb):
        """Décalages de ±360° pour lesquels ce contour est dans la vue (aucun : invisible)."""
        if bb[3] < la0 - 1 or bb[1] > la1 + 1:
            return []
        return [k for k in (-360, 0, 360)
                if not (bb[2] + k < lo0 - 1 or bb[0] + k > lo1 + 1)]

    def rings_of(rings, bb):
        # contours projetés sans « repli » point par point (sinon traits parasites
        # le long de la ligne de changement de date), répétés à ±360° si besoin
        for k in shifts(bb):
            for r in rings:
                pts = [view.xy(x + k, y, wrap=False) for x, y in r]
                if len(pts) > 2:
                    yield pts

    # pays
    for c in d_["countries"]:
        col = PALETTE.get(c["c"], (240, 236, 220))
        for pts in rings_of(c["r"], c["bb"]):
            g.polygon(pts, fill=col)
    for r in d_["lakes"]:
        xs, ys = [p[0] for p in r], [p[1] for p in r]
        for pts in rings_of([r], (min(xs), min(ys), max(xs), max(ys))):
            g.polygon(pts, fill=LAKE)
    for c in d_["countries"]:
        for pts in rings_of(c["r"], c["bb"]):
            g.line(pts + [pts[0]], fill=BORDER, width=1)

    # méridiens / parallèles
    step = 30 if view.span() > 150 else (10 if view.span() > 40 else 5)
    for lon in range(-180, 181, step):
        x = view.xy(lon, view.lat)[0]
        if 0 <= x <= W:
            g.line([(x, 0), (x, H)], fill=GRID, width=1)
    for lat in range(-80, 81, step):
        y = view.xy(view.lon, lat)[1]
        if 0 <= y <= H:
            g.line([(0, y), (W, y)], fill=GRID, width=1)

    # noms des pays
    span = view.span()
    max_rank = 2 if span > 200 else (4 if span > 60 else (6 if span > 20 else 9))
    fc = _font(13 if span < 100 else 11)
    for c in d_["countries"]:
        x, y, rank = c["l"]
        if rank > max_rank:
            continue
        px, py = view.xy(x / 100, y / 100)
        if 0 <= px <= W and 0 <= py <= H:
            name = (c["nf"] if lang == "fr" else c["n"]).upper()
            g.text((px, py), name, fill=(130, 130, 130), font=fc, anchor="mm")

    # villes
    city_rank = 1 if span > 200 else (3 if span > 60 else 4)
    fcity = _font(12 if span < 100 else 10)
    fcap = _font(14 if span < 100 else 11, bold=True)
    taken = []
    for name, x, y, rank, cap in sorted(d_["cities"], key=lambda c: (-c[4], c[3])):
        if rank > city_rank and not (cap and span < 200):
            continue
        px, py = view.xy(x / 100, y / 100)
        if not (0 <= px <= W and 0 <= py <= H):
            continue
        f = fcap if cap else fcity
        tw = g.textlength(name, font=f)
        box = (px - 4, py - 8, px + 6 + tw, py + 8)
        if any(not (box[2] < b[0] or box[0] > b[2] or box[3] < b[1] or box[1] > b[3]) for b in taken):
            continue
        taken.append(box)
        if cap:
            _star(g, px, py, 4)
            g.text((px + 5, py - 1), name, fill="black", font=f, anchor="lm")
        else:
            g.ellipse([px - 2, py - 2, px + 2, py + 2], fill="black")
            g.text((px + 4, py), name, fill="black", font=f, anchor="lm")

    # trajets puis étiquettes
    flab = _font(13)
    if me and me.get("pos") and show_lines:
        for s in stations:
            if s.get("ok") and s.get("pos"):
                path = [view.xy(lo, la) for la, lo in _great_circle(me["pos"], s["pos"])]
                for a, b in zip(path, path[1:]):
                    if abs(a[0] - b[0]) < W / 2:
                        g.line([a, b], fill=LINE, width=4)
    boxes = []
    for s in list(stations) + ([me] if me and me.get("pos") else []):
        if not s.get("pos"):
            continue
        px, py = view.xy(s["pos"][1], s["pos"][0])
        is_me = s is me
        col = (255, 255, 255) if is_me else (GREEN if s.get("ok") else (255, 224, 102))
        g.ellipse([px - 6, py - 6, px + 6, py + 6], fill=LINE if not is_me else (40, 40, 40))
        tw = g.textlength(s["call"], font=flab)
        bw, bh = tw + 16, 20
        bx, by = px - 10 - bw, py - bh / 2
        for _ in range(8):                         # évite que deux étiquettes se chevauchent
            if any(not (bx + bw < x0 or bx > x1 or by + bh < y0 or by > y1) for x0, y0, x1, y1 in boxes):
                by += bh + 2
            else:
                break
        boxes.append((bx, by, bx + bw, by + bh))
        if abs(by + bh / 2 - py) > 1:              # étiquette déplacée : petit trait vers le point
            g.line([(bx + bw, by + bh / 2), (px, py)], fill=(60, 60, 60), width=1)
        g.rectangle([bx, by, bx + bw, by + bh], fill=col, outline=(30, 30, 30))
        g.text((bx + bw / 2, by + bh / 2), s["call"], fill="black", font=flab, anchor="mm")
        s["_hit"] = (bx, by, bx + bw, by + bh, px, py)
    return img


def _star(g, x, y, r):
    pts = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((x + rr * math.cos(a), y - rr * math.sin(a)))
    g.polygon(pts, fill="black")


# ----------------------------------------------------------------------- fenêtre Tk
class MapWindow:
    """Fenêtre « Carte des stations ». provider() -> (moi, [stations]) ; tr : traduction."""

    def __init__(self, master, provider, tr=lambda s: s, lang=lambda: "fr", on_paste=None,
                 show_all=False, on_show_all=None):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.provider, self.tr, self.lang, self.on_paste = tk, provider, tr, lang, on_paste
        w = self.win = tk.Toplevel(master)
        w.title("HFImage — " + tr("Carte des stations"))
        w.geometry("1100x760")
        w.protocol("WM_DELETE_WINDOW", self.close)
        bar = tk.Frame(w, bg="#33d633")
        bar.pack(fill="x")
        self.v_view = tk.StringVar(value="Europe")
        names = [tr("Toutes les stations")] + [tr(n) for n in VIEWS]
        self._names = dict(zip(names, ["*"] + list(VIEWS)))
        cb = ttk.Combobox(bar, textvariable=self.v_view, values=names, state="readonly", width=20)
        cb.set(tr("Europe"))
        cb.pack(side="left", padx=6, pady=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.set_view(self._names[self.v_view.get()]))
        # par défaut : seulement les stations qui ont reçu notre image (en vert, avec le trait)
        self.v_heard = tk.BooleanVar(value=show_all)
        self.on_show_all = on_show_all

        def toggled():
            if self.on_show_all:
                self.on_show_all(self.v_heard.get())
            if self._preset == "*" and not self._moved:
                self.set_view("*")              # recadre sur les stations affichées
            else:
                self.redraw()
        tk.Checkbutton(bar, text=tr("Aussi les autres stations (en jaune)"),
                       variable=self.v_heard, bg="#33d633", activebackground="#33d633",
                       command=toggled).pack(side="left", padx=6)
        if on_paste:
            tk.Button(bar, text=tr("Coller la carte dans la fenêtre TX"),
                      command=self._paste).pack(side="left", padx=6)
        tk.Label(bar, text=tr("Bouton gauche maintenu : déplacer la carte — molette : zoom"),
                 bg="#33d633").pack(side="left", padx=10)
        self.cv = tk.Canvas(w, bg="#bee2f7", highlightthickness=0, cursor="fleur")
        self.cv.pack(fill="both", expand=True)
        self.info = tk.Label(w, text="", anchor="w", bg="#e8f7e6")
        self.info.pack(fill="x")
        self.view = None
        self._img = self._ph = None
        self._drag = None
        self._job = None
        self._last = ([], None)
        self.cv.bind("<Configure>", lambda e: self._later())
        self.cv.bind("<ButtonPress-1>", self._press)
        self.cv.bind("<B1-Motion>", self._motion)
        self.cv.bind("<ButtonRelease-1>", self._release)
        self.cv.bind("<MouseWheel>", lambda e: self._zoom(e, 1 if e.delta > 0 else -1))
        self.cv.bind("<Button-4>", lambda e: self._zoom(e, 1))
        self.cv.bind("<Button-5>", lambda e: self._zoom(e, -1))
        self._preset = "Europe"
        self._focus = None          # station sur laquelle la carte est centrée
        self._moved = False         # l'utilisateur a déplacé / zoomé : on garde sa vue
        self._cb = cb

    def alive(self):
        try:
            return bool(self.win.winfo_exists())
        except Exception:
            return False

    def close(self):
        self.win.destroy()

    def _size(self):
        return max(200, self.cv.winfo_width()), max(150, self.cv.winfo_height())

    def _stations(self):
        me, st = self.provider()
        if not self.v_heard.get():
            st = [s for s in st if s.get("ok")]
        return me, st

    def set_view(self, name, focus=None):
        self._preset, self._focus, self._moved = name, None, False
        if name == "*":
            self._cb.set(self.tr("Toutes les stations"))
        W, H = self._size()
        me, st = self._stations()
        if name == "*":
            pts = [s["pos"] for s in st if s.get("pos")] + ([me["pos"]] if me and me.get("pos") else [])
            self.view = fit_view(pts, W, H) if pts else View(*VIEWS["Europe"], W, H)
        else:
            self.view = View(*VIEWS[name], W, H)
        if focus:
            self.view = View(focus[1], focus[0], self.view.span(), W, H)
        self.redraw()

    def focus(self, call):
        """Centre la carte sur une station (double-clic dans les listes)."""
        me, st = self._stations()
        for s in st:
            if s["call"] == call and s.get("pos"):
                pts = [s["pos"]] + ([me["pos"]] if me and me.get("pos") else [])
                W, H = self._size()
                self._focus, self._moved = call, False
                self.view = fit_view(pts, W, H, margin=0.6, min_span=14)
                self.redraw()
                self._show_info(s)
                return True
        self.info.configure(text=self.tr("{0} : position inconnue (pas de locator reçu)").replace("{0}", call))
        return False

    def _later(self):
        if self._job:
            self.win.after_cancel(self._job)
        self._job = self.win.after(120, self._resize)

    def _resize(self):
        self._job = None
        W, H = self._size()
        if self.view is None or not self._moved:
            # la fenêtre a pris sa taille : on recalcule la vue demandée pour cette taille
            focus = self._focus
            self.set_view(self._preset)
            if focus:
                self.focus(focus)
            return
        self.view = View(self.view.lon, self.view.lat, self.view.span(), W, H)
        self.redraw()

    def redraw(self):
        from PIL import ImageTk
        if self.view is None:
            return self.set_view(self._preset)
        me, st = self._stations()
        st = [dict(s) for s in st]
        me = dict(me) if me else None
        self._img = render(self.view, st, me, self.lang())
        self._last = (st, me)
        self._ph = ImageTk.PhotoImage(self._img)
        self.cv.delete("all")
        self.cv.create_image(0, 0, image=self._ph, anchor="nw", tags="map")
        self.cv.create_text(self.view.w - 6, self.view.h - 6, anchor="se", fill="#555",
                            text=self.tr("Fond de carte : Natural Earth (domaine public)"),
                            font=("TkDefaultFont", 8))
        if not me or not me.get("pos"):
            self.info.configure(text=self.tr("Indiquez votre locator dans les Réglages pour placer votre station."))

    # déplacement / zoom
    def _press(self, e):
        self._drag = (e.x, e.y, e.x, e.y)

    def _motion(self, e):
        if self._drag:
            x0, y0, lx, ly = self._drag
            self.cv.move("all", e.x - lx, e.y - ly)
            self._drag = (x0, y0, e.x, e.y)

    def _release(self, e):
        if not self._drag or self.view is None:
            return
        x0, y0, _, _ = self._drag
        self._drag = None
        dx, dy = e.x - x0, e.y - y0
        if abs(dx) < 3 and abs(dy) < 3:
            return self._click(e.x, e.y)
        lon, lat = self.view.lonlat(self.view.w / 2 - dx, self.view.h / 2 - dy)
        lat = max(-80, min(80, lat))
        self._moved = True
        self.view = View(lon, lat, self.view.span(), self.view.w, self.view.h)
        self.redraw()

    def _zoom(self, e, d):
        if self.view is None:
            return
        f = 0.7 if d > 0 else 1 / 0.7
        self._moved = True
        lon, lat = self.view.lonlat(e.x, e.y)
        span = max(3.0, min(360.0, self.view.span() * f))
        v = View(self.view.lon, self.view.lat, span, self.view.w, self.view.h)
        # garde le point sous la souris au même endroit
        lon2, lat2 = v.lonlat(e.x, e.y)
        self.view = View(self.view.lon + lon - lon2, max(-80, min(80, self.view.lat + lat - lat2)),
                         span, self.view.w, self.view.h)
        self.redraw()

    def _click(self, x, y):
        st, me = self._last
        for s in st + ([me] if me else []):
            h = s.get("_hit")
            if h and (h[0] <= x <= h[2] and h[1] <= y <= h[3] or math.hypot(x - h[4], y - h[5]) < 9):
                self._show_info(s, me)
                return

    def _show_info(self, s, me=None):
        if me is None:
            me = self.provider()[0]
        parts = [s["call"]]
        if s.get("loc"):
            parts.append(s["loc"])
        if me and me.get("pos") and s.get("pos") and s is not me and s["call"] != me.get("call"):
            parts.append(f"{distance_km(me['pos'], s['pos']):.0f} km, {bearing(me['pos'], s['pos']):.0f}°")
        if s.get("info"):
            parts.append(s["info"])
        self.info.configure(text="   —   ".join(parts))

    def _paste(self):
        if self._img is not None and self.on_paste:
            self.on_paste(self._img.copy())
