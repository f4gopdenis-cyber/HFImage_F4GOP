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
        self.freq.configure(text=f"{freq}\n{sub}" if freq else "",
                            font=("TkDefaultFont", 11, "bold"))

    def set_call(self, call):
        self.call.configure(text=call or "—")


class ImageView(tk.Canvas):
    """Grande zone d'image sur fond noir : l'image est agrandie/réduite pour remplir
    la place disponible (comme EasyPal), centrée, sans déformation.
    set_animation() joue un GIF animé en boucle."""

    def __init__(self, master, placeholder="", **kw):
        super().__init__(master, bg="#000", highlightthickness=0, **kw)
        self.pil = None
        self._ph = None
        self.placeholder = placeholder
        self.frames, self.durs, self.k = None, None, 0
        self._job = None
        self._cache = {}
        self.bind("<Configure>", lambda e: (self._cache.clear(), self._redraw()))

    def _stop(self):
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        self.frames, self.durs = None, None
        self._cache.clear()

    def set_image(self, pil_img):
        self._stop()
        self.pil = pil_img.convert("RGB") if pil_img is not None else None
        self._redraw()

    def set_animation(self, frames, durations):
        """frames : images PIL RGB ; durations : ms par image."""
        self._stop()
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
