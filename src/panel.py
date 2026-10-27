"""Panneau d'état façon EasyPal : indicatif, barres RX / SNR, voyants, paramètres TX / RX."""
import tkinter as tk

from i18n import tr

BG = "#9fe39a"
FG = "#0d3b0d"
LED_OFF, LED_GREEN, LED_AMBER, LED_RED = "#5f8f5c", "#18c718", "#f2b200", "#e53030"


class StatusPanel(tk.Frame):
    LEDS = ("Signal", "Sync", "Trame", "Image", "BSR")

    def __init__(self, master):
        super().__init__(master, bg=BG, bd=2, relief="groove")
        self.call = tk.Label(self, text="—", bg=BG, fg=FG, font=("TkDefaultFont", 16, "bold"))
        self.call.grid(row=0, column=0, columnspan=2, sticky="w", padx=6, pady=(4, 2))
        self.freq = tk.Label(self, text="", bg=BG, fg="#063806", font=("TkDefaultFont", 11, "bold"),
                             justify="right", anchor="e")
        self.freq.grid(row=0, column=2, columnspan=2, sticky="e", padx=6, pady=(4, 0))
        # 1.78 : S-mètre du poste, à la place de la fréquence (déjà en haut de la fenêtre)
        self.smeter = tk.Canvas(self, width=self.SM_W, height=30, bg=BG, highlightthickness=0)
        self._sm_on, self._sm_key = False, None
        for w in (self, self.smeter):
            w.bind("<Configure>", lambda e: self._sm_redraw(self._sm_key) if self._sm_key else None, add="+")
        self.bars = {}
        for r, (name, unit) in enumerate((("RX", "dBFS"), ("SNR", "dB")), start=1):
            c = tk.Canvas(self, width=110, height=12, bg="#e8f7e6", highlightthickness=1,
                          highlightbackground=FG)
            c.grid(row=r, column=0, columnspan=2, sticky="w", padx=6, pady=1)
            lab = tk.Label(self, text=f"{name}", bg=BG, fg=FG, font=("TkDefaultFont", 8))
            lab.grid(row=r, column=2, sticky="w")
            val = tk.Label(self, text="", bg=BG, fg=FG, font=("TkDefaultFont", 8), width=8, anchor="e")
            val.grid(row=r, column=3, sticky="e", padx=(0, 6))
            self.bars[name] = (c, val, unit)

        # tableau TX | RX
        tbl = tk.Frame(self, bg=BG)
        tbl.grid(row=3, column=0, columnspan=4, sticky="we", padx=6, pady=(6, 2))
        heads = ("", "TX", "RX")
        for j, h in enumerate(heads):
            tk.Label(tbl, text=h, bg=BG, fg=FG, font=("TkDefaultFont", 8, "bold underline")).grid(
                row=0, column=j, sticky="w", padx=3)
        self.cells = {}
        for i, row in enumerate(("Mode", "Bande kHz", "Débit b/s", "Total", "Segs OK", "Position"), start=1):
            tk.Label(tbl, text=row, bg=BG, fg=FG, font=("TkDefaultFont", 8)).grid(row=i, column=0, sticky="w")
            for j, side in enumerate(("TX", "RX"), start=1):
                lab = tk.Label(tbl, text="—", bg=BG, fg=FG, font=("TkDefaultFont", 8), width=7, anchor="w")
                lab.grid(row=i, column=j, sticky="w", padx=3)
                self.cells[(row, side)] = lab

        # vignette de la dernière image reçue, dans la place libre à droite du tableau ; elle prend
        # la place disponible sans élargir le panneau (cachée s'il n'y a pas assez de place)
        tbl.columnconfigure(3, weight=1)
        self.thumb = tk.Canvas(tbl, width=1, height=1, bg=BG, highlightthickness=0, cursor="hand2")
        self.thumb.grid(row=0, column=3, rowspan=7, sticky="nsew", padx=(6, 0))
        self.thumb.bind("<Configure>", lambda e: self._draw_thumb())
        self.thumb.bind("<Button-1>", lambda e: self.on_thumb() if self._thumb_img is not None else None)
        self._thumb_img, self._thumb_txt, self._thumb_ph = None, "", None
        self.on_thumb = lambda: None

        # voyants
        lf = tk.Frame(self, bg=BG)
        lf.grid(row=4, column=0, columnspan=4, sticky="w", padx=6, pady=(4, 6))
        self.leds = {}
        for k, name in enumerate(self.LEDS):
            c = tk.Canvas(lf, width=12, height=12, bg=BG, highlightthickness=0)
            c.grid(row=0, column=2 * k)
            oval = c.create_oval(1, 1, 11, 11, fill=LED_OFF, outline=FG)
            tk.Label(lf, text=name, bg=BG, fg=FG, font=("TkDefaultFont", 8)).grid(row=0, column=2 * k + 1,
                                                                                   padx=(1, 5))
            self.leds[name] = (c, oval)

    modern = None                # palette du style Moderne (None : Classique)

    def set_modern(self, P):
        """Style Moderne : jauges arrondies, voyants sans contour ; None : comme EasyPal."""
        self.modern = P
        for name, (c, val, unit) in self.bars.items():
            if P:
                c.configure(highlightthickness=0, bg=P["panel"], height=10)
            else:
                c.configure(highlightthickness=1, bg="#e8f7e6", height=12)
            last = getattr(self, "_bar_last", {}).get(name)
            if last:
                self.set_bar(name, *last)
            else:
                self._track(c)
        for name, (c, oval) in self.leds.items():
            fill = c.itemcget(oval, "fill")
            c.itemconfigure(oval, outline=fill if P else FG)
        if self._sm_key is not None:                   # S-mètre redessiné aux nouvelles couleurs
            self._sm_redraw(self._sm_key)

    def _track(self, c):
        c.delete("t")
        P = self.modern
        if P:
            self._pill(c, 1, 1, 109, 10, P["field"], "t")

    @staticmethod
    def _pill(c, x0, y0, x1, y1, color, tag):
        r = (y1 - y0) / 2
        if x1 - x0 < 2 * r:
            x1 = x0 + 2 * r
        c.create_oval(x0, y0, x0 + 2 * r, y1, fill=color, outline="", tags=tag)
        c.create_oval(x1 - 2 * r, y0, x1, y1, fill=color, outline="", tags=tag)
        c.create_rectangle(x0 + r, y0, x1 - r, y1, fill=color, outline="", tags=tag)

    def set_bar(self, name, value, lo, hi, text):
        c, val, unit = self.bars[name]
        self.__dict__.setdefault("_bar_last", {})[name] = (value, lo, hi, text)
        c.delete("b")
        P = self.modern
        if P:
            self._track(c)
        if value is not None:
            f = max(0.0, min(1.0, (value - lo) / (hi - lo)))
            col = LED_RED if name == "RX" and value > -3 else ("#2f9e2f" if f > 0.25 else LED_AMBER)
            if P:                                   # jauge arrondie, couleur d'accent
                col = P["bad"] if name == "RX" and value > -3 else (P["accent"] if f > 0.25 else "#ffb84d")
                if f > 0.01:
                    self._pill(c, 1, 1, 1 + max(10, f * 108), 10, col, "b")
            else:
                c.create_rectangle(1, 1, 1 + f * 108, 12, fill=col, outline="", tags="b")
        val.configure(text=text)

    def set_led(self, name, color):
        c, oval = self.leds[name]
        c.itemconfigure(oval, fill=color, outline=color if self.modern else FG)

    def set_cell(self, row, side, text):
        self.cells[(row, side)].configure(text=text)

    def set_freq(self, freq, sub=""):
        """Fréquence du poste (lue par CAT), avec mode et bande en petit."""
        # ▾ : la fréquence se clique (menu des fréquences)
        self.freq.configure(text=f"{freq} ▾\n{sub}" if freq else "",
                            font=("TkDefaultFont", 11, "bold"))

    SM_W = 108                  # largeur demandée : tient aussi dans un panneau étroit

    def show_smeter(self, on):
        """S-mètre (True) ou fréquence (False) à droite de l'indicatif."""
        on = bool(on)
        if on == self._sm_on:
            return
        self._sm_on = on
        if on:
            self.freq.grid_remove()
            self.smeter.grid(row=0, column=2, columnspan=2, sticky="ew", padx=6, pady=(4, 0))
            self._sm_key = None
            self.set_smeter(None)
        else:
            self.smeter.grid_remove()
            self.freq.grid()

    def set_smeter(self, db, frozen=False):
        """db : dB par rapport à S9 (None : pas encore lu) ; frozen : émission en cours (grisé).
        Rien n'est redessiné si la valeur affichée ne change pas."""
        from radio import s_text
        self._sm_db = db
        txt = s_text(db)
        W = self._sm_width()
        key = (txt, round(db) if db is not None else None, frozen, id(self.modern), W)
        if key == self._sm_key:
            return
        self._sm_key = key
        c, P = self.smeter, self.modern
        bg = P["panel"] if P else BG
        fg = P["fg"] if P else FG
        muted = P["muted"] if P else "#3d6b3d"
        track = P["field"] if P else "#e8f7e6"
        green = (P["accent"] if P else "#2f9e2f") if not frozen else "#8a8f96"
        red = (P["bad"] if P else LED_RED) if not frozen else "#a0a4aa"
        c.configure(bg=bg)
        c.delete("all")
        x0, x1, y0, y1 = 1, W - 2, 15, 22

        def pos(v):                        # v en dB / S9 : S0..S9 sur 60 %, S9..+60 sur 40 %
            v = max(-54.0, min(60.0, float(v)))
            return x0 + (x1 - x0) * (0.6 * (v + 54) / 54 if v <= 0 else 0.6 + 0.4 * v / 60)

        c.create_text(x0, 0, text=tr("S-mètre"), anchor="nw", fill=muted, font=("TkDefaultFont", 7))
        c.create_text(x1, -1, text=txt, anchor="ne", fill=muted if frozen or db is None else fg,
                      font=("TkDefaultFont", 10, "bold"))
        c.create_rectangle(x0, y0, x1, y1, fill=track, outline="" if P else FG)
        if db is not None:
            e = pos(db)
            c.create_rectangle(x0 + 1, y0 + 1, min(e, pos(0)), y1 - (0 if P else 1), fill=green, outline="")
            if db > 0:
                c.create_rectangle(pos(0), y0 + 1, e, y1 - (0 if P else 1), fill=red, outline="")
        for v, lab in ((-48, "1"), (-36, "3"), (-24, "5"), (-12, "7"), (0, "9"), (20, "+20"), (40, "+40"),
                       (60, "+60")):
            x = pos(v)
            c.create_line(x, y1, x, y1 + 2, fill=muted)
            if v == 40:
                continue                   # pas assez de place pour toutes les étiquettes
            c.create_text(min(x, x1 - 7) if v == 60 else x, y1 + 1, text=lab, anchor="n",
                          fill=(red if v > 0 and not frozen else muted), font=("TkDefaultFont", 6))

    def _sm_width(self):
        """Largeur où dessiner : celle du canevas, mais sans dépasser le bord visible du panneau
        (panneau étroit, style Moderne : sinon « S9+10 » et « +60 » seraient coupés)."""
        c = self.smeter
        w = c.winfo_width()
        if w <= 1:
            return self.SM_W
        vis = self.winfo_width() - c.winfo_x() - 6
        return max(60, min(w, vis)) if vis > 1 else w

    def _sm_redraw(self, key):
        self._sm_key = None
        self.set_smeter(getattr(self, "_sm_db", None), key[2])

    def set_thumb(self, img, text=""):
        """Dernière image reçue (PIL) + petite ligne (indicatif, prénom, distance)."""
        self._thumb_img, self._thumb_txt = img, text or ""
        self._draw_thumb()

    def _draw_thumb(self):
        c = self.thumb
        c.delete("all")
        im = self._thumb_img
        w, h = c.winfo_width(), c.winfo_height()
        if im is None or w < 60 or h < 50:
            return
        from PIL import Image, ImageTk
        import tkinter.font as tkfont
        f = tkfont.Font(family="TkDefaultFont", size=8)
        lines = []
        for ln in [x for x in self._thumb_txt.split("\n") if x]:
            while ln and f.measure(ln) > w - 2:              # trop long : coupé avec « … »
                ln = ln[:-2] + "…" if len(ln) > 2 else ""
            lines.append(ln)
        lh = f.metrics("linespace")
        th = h - lh * len(lines)
        if th < 30:
            return
        t = im.copy()
        t.thumbnail((w - 2, th - 2), Image.LANCZOS)
        self._thumb_ph = ImageTk.PhotoImage(t)
        c.create_image(w // 2, (th - t.height) // 2, image=self._thumb_ph, anchor="n")
        c.create_rectangle(w // 2 - t.width // 2 - 1, (th - t.height) // 2 - 1,
                           w // 2 + (t.width + 1) // 2, (th - t.height) // 2 + t.height, outline=FG)
        for k, ln in enumerate(lines):
            c.create_text(w // 2, th + k * lh, text=ln, fill=FG, font=f, anchor="n")

    def set_call(self, call):
        self.call.configure(text=call or "—")


class ImageView(tk.Canvas):
    """Grande zone d'image sur fond noir : l'image est agrandie/réduite pour remplir
    la place disponible (comme EasyPal), centrée, sans déformation.
    set_animation() joue un GIF animé en boucle.
    Molette de la souris : zoom autour du pointeur ; clic gauche maintenu : déplacer
    l'image agrandie ; clic droit : retour à l'image entière."""

    ZOOM_MAX = 16.0

    def __init__(self, master, placeholder="", **kw):
        super().__init__(master, bg="#000", highlightthickness=0, **kw)
        self.pil = None
        self._ph = None
        self.placeholder = placeholder
        self.frames, self.durs, self.k = None, None, 0
        self._job = None
        self._cache = {}
        self.zoom = 1.0                 # 1 = image entière dans la fenêtre
        self.view = None                # centre affiché (coordonnées dans l'image)
        self._drag = None
        self.menu_cb = None             # clic droit : menu (sinon retour à l'image entière)
        self.wheel_cb = None            # molette : rend True si elle a servi (édition), sinon zoom
        self.after_draw = None          # dessin en plus après l'image (cadre de sélection…)
        self.bind("<Configure>", lambda e: (self._cache.clear(), self._redraw()))
        self.bind("<MouseWheel>", lambda e: self._wheel_any(e, 1 if e.delta > 0 else -1))   # Windows
        self.bind("<Button-4>", lambda e: self._wheel_any(e, 1))                            # Linux
        self.bind("<Button-5>", lambda e: self._wheel_any(e, -1))
        self.bind("<ButtonPress-1>", self._drag_start, add="+")
        self.bind("<B1-Motion>", self._drag_move, add="+")
        self.bind("<ButtonRelease-1>", lambda e: setattr(self, "_drag", None), add="+")
        self.bind("<Button-3>", lambda e: self.menu_cb(e) if self.menu_cb else self.reset_zoom(), add="+")

    def _stop(self):
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        self.frames, self.durs = None, None
        self._cache.clear()

    def reset_zoom(self):
        if self.zoom != 1.0:
            self.zoom, self.view = 1.0, None
            self._redraw()

    def _fit(self):
        w, h = max(10, self.winfo_width()), max(10, self.winfo_height())
        r = min((w - 20) / self.pil.width, (h - 20) / self.pil.height)
        return w, h, max(r, 0.01)

    def _clamp_view(self, s, w, h):
        """Garde l'image dans la fenêtre (pas de bord noir inutile quand elle déborde)."""
        W, H = self.pil.width, self.pil.height
        vx, vy = self.view
        hw, hh = w / (2 * s), h / (2 * s)
        vx = W / 2 if hw * 2 >= W else min(max(vx, hw), W - hw)
        vy = H / 2 if hh * 2 >= H else min(max(vy, hh), H - hh)
        self.view = (vx, vy)

    def _wheel_any(self, e, step):
        if self.wheel_cb is not None and self.zoom <= 1.0 and self.wheel_cb(e, step):
            return
        if e.state & 0x0001:                                 # Maj + molette : réservé à l'édition
            return
        self._wheel(e, step)

    def image_box(self):
        """Place de l'image entière à l'écran -> (x, y, largeur, hauteur), ou None (zoom, pas d'image)."""
        if self.pil is None or self.zoom > 1.0:
            return None
        w, h = max(10, self.winfo_width()), max(10, self.winfo_height())
        r = max(min((w - 20) / self.pil.width, (h - 20) / self.pil.height), 0.01)
        dw, dh = max(1, int(self.pil.width * r)), max(1, int(self.pil.height * r))
        return w // 2 - dw // 2, h // 2 - dh // 2, dw, dh

    def _wheel(self, e, step):
        if self.pil is None:
            return
        w, h, r = self._fit()
        old = self.zoom
        new = min(self.ZOOM_MAX, max(1.0, old * (1.25 if step > 0 else 0.8)))
        if abs(new - old) < 1e-9:
            return
        if new < 1.02:
            return self.reset_zoom()
        if self.view is None:
            self.view = (self.pil.width / 2, self.pil.height / 2)
        s0, s1 = r * old, r * new
        # le point de l'image sous le pointeur reste sous le pointeur
        px = self.view[0] + (e.x - w / 2) / s0
        py = self.view[1] + (e.y - h / 2) / s0
        self.zoom = new
        self.view = (px - (e.x - w / 2) / s1, py - (e.y - h / 2) / s1)
        self._clamp_view(s1, w, h)
        self._redraw()

    def _drag_start(self, e):
        self._drag = (e.x, e.y) if self.zoom > 1.0 and self.pil is not None else None

    def _drag_move(self, e):
        if self._drag is None or self.zoom <= 1.0 or self.pil is None:
            return
        w, h, r = self._fit()
        s = r * self.zoom
        dx, dy = e.x - self._drag[0], e.y - self._drag[1]
        self._drag = (e.x, e.y)
        self.view = (self.view[0] - dx / s, self.view[1] - dy / s)
        self._clamp_view(s, w, h)
        self._redraw()

    def set_image(self, pil_img):
        self._stop()
        self.zoom, self.view = 1.0, None
        self.pil = pil_img.convert("RGB") if pil_img is not None else None
        self._redraw()

    def set_animation(self, frames, durations):
        """frames : images PIL RGB ; durations : ms par image."""
        self._stop()
        self.zoom, self.view = 1.0, None
        if not frames:
            return self.set_image(None)
        self.frames, self.durs, self.k = frames, durations, 0
        self.pil = frames[0]
        self._tick()

    def _tick(self):
        if not self.frames:
            return
        self.pil = self.frames[self.k]
        self._redraw(self.k)
        d = self.durs[self.k]
        self.k = (self.k + 1) % len(self.frames)
        self._job = self.after(max(20, int(d)), self._tick)

    def _redraw(self, key=None):
        from PIL import Image, ImageTk
        self.delete("all")
        w, h = max(10, self.winfo_width()), max(10, self.winfo_height())
        if self.pil is None:
            self.create_text(w // 2, h // 2, text=self.placeholder, fill="#777",
                             font=("TkDefaultFont", 11))
            return
        if self.zoom > 1.0:
            return self._redraw_zoom(w, h)
        ph = self._cache.get(key) if key is not None else None
        if ph is None:
            r = min((w - 20) / self.pil.width, (h - 20) / self.pil.height)
            r = max(r, 0.01)
            size = (max(1, int(self.pil.width * r)), max(1, int(self.pil.height * r)))
            # animation : redimensionnement rapide, images gardées en cache
            meth = Image.BILINEAR if key is not None else (Image.LANCZOS if r < 1 else Image.BICUBIC)
            ph = ImageTk.PhotoImage(self.pil.resize(size, meth))
            if key is not None:
                self._cache[key] = ph
        self._ph = ph
        self.create_image(w // 2, h // 2, image=ph)
        if self.after_draw is not None:
            try:
                self.after_draw(self)
            except Exception:
                pass

    def _redraw_zoom(self, w, h):
        """Image agrandie : on ne redimensionne que la partie visible."""
        from PIL import Image, ImageTk
        _, _, r = self._fit()
        s = r * self.zoom
        if self.view is None:
            self.view = (self.pil.width / 2, self.pil.height / 2)
        self._clamp_view(s, w, h)
        vx, vy = self.view
        W, H = self.pil.width, self.pil.height
        x0, y0 = max(0.0, vx - w / (2 * s)), max(0.0, vy - h / (2 * s))
        x1, y1 = min(float(W), vx + w / (2 * s)), min(float(H), vy + h / (2 * s))
        if x1 - x0 < 0.5 or y1 - y0 < 0.5:
            return
        dw, dh = max(1, round((x1 - x0) * s)), max(1, round((y1 - y0) * s))
        meth = Image.NEAREST if s >= 4 else Image.BICUBIC
        crop = self.pil.resize((dw, dh), meth, box=(x0, y0, x1, y1))
        self._ph = ImageTk.PhotoImage(crop)
        sx, sy = w / 2 + (x0 - vx) * s, h / 2 + (y0 - vy) * s
        self.create_image(round(sx), round(sy), image=self._ph, anchor="nw")
        self.create_text(w - 8, 8, text=f"Zoom ×{self.zoom:.1f}  (clic droit : image entière)", fill="#ffe066",
                         anchor="ne",
                         font=("TkDefaultFont", 9, "bold"))
