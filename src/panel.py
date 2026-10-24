"""Panneau d'état façon EasyPal : indicatif, barres RX / SNR, voyants, paramètres TX / RX."""
import tkinter as tk

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

    def set_bar(self, name, value, lo, hi, text):
        c, val, unit = self.bars[name]
        c.delete("b")
        if value is not None:
            f = max(0.0, min(1.0, (value - lo) / (hi - lo)))
            col = LED_RED if name == "RX" and value > -3 else ("#2f9e2f" if f > 0.25 else LED_AMBER)
            c.create_rectangle(1, 1, 1 + f * 108, 12, fill=col, outline="", tags="b")
        val.configure(text=text)

    def set_led(self, name, color):
        c, oval = self.leds[name]
        c.itemconfigure(oval, fill=color)

    def set_cell(self, row, side, text):
        self.cells[(row, side)].configure(text=text)

    def set_freq(self, freq, sub=""):
        """Fréquence du poste (lue par CAT), avec mode et bande en petit."""
        # ▾ : la fréquence se clique (menu des fréquences)
        self.freq.configure(text=f"{freq} ▾\n{sub}" if freq else "",
                            font=("TkDefaultFont", 11, "bold"))

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
        self.bind("<Configure>", lambda e: (self._cache.clear(), self._redraw()))
        self.bind("<MouseWheel>", lambda e: self._wheel(e, 1 if e.delta > 0 else -1))   # Windows
        self.bind("<Button-4>", lambda e: self._wheel(e, 1))                            # Linux
        self.bind("<Button-5>", lambda e: self._wheel(e, -1))
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
