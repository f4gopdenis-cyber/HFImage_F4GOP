"""Apparence : thème de couleurs et police de toute l'interface.

Le programme est dessiné avec les couleurs « EasyPal » (verts). Un thème transforme
ces couleurs d'origine : les verts prennent la teinte choisie, les blancs / gris restent
neutres ; le thème « Nuit » assombrit tout (texte clair sur fond sombre) sauf le noir
de l'image et du waterfall. On garde les réglages d'origine de chaque widget, pour
pouvoir changer de thème autant de fois qu'on veut sans redémarrer.
"""
import colorsys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

# nom -> couleur de base (None = couleurs d'origine) ; « Nuit » est un cas à part
THEMES = {
    "Vert EasyPal": None,
    "Bleu": "#3a8ee6",
    "Gris": "#9aa0a6",
    "Sable": "#d9a441",
    "Bordeaux": "#b5485d",
    "Violet": "#8a63d2",
    "Nuit": "night",
}
BASE_GREEN = "#33d633"
FONT_SIZES = {"Petite": 0.9, "Normale": 1.0, "Grande": 1.2, "Très grande": 1.45}
FONTS = ["(par défaut)", "Segoe UI", "Arial", "Tahoma", "Verdana", "Calibri", "Trebuchet MS",
         "Times New Roman", "Georgia", "Consolas", "Courier New"]
MONO = {"consolas", "courier new", "courier", "tkfixedfont", "lucida console", "dejavu sans mono"}

COLOR_OPTS = ("background", "foreground", "activebackground", "activeforeground", "selectbackground",
              "selectforeground", "highlightbackground", "highlightcolor", "insertbackground",
              "disabledforeground", "troughcolor", "readonlybackground")
# styles ttk dont on change la couleur du texte
TTK_TEXT = (".", "TLabel", "TCheckbutton", "TRadiobutton", "TLabelframe.Label", "TButton", "TNotebook.Tab",
            "TEntry", "TCombobox", "TSpinbox", "Treeview", "Treeview.Heading")


def is_text_color(c):
    """Couleur d'origine d'un texte « normal » (noir, gris foncé, vert très foncé),
    pas d'un texte coloré exprès (rouge d'alerte, blanc sur bandeau…)."""
    try:
        h, l, s = _hls(c)
    except (ValueError, IndexError):
        return False
    return (s < 0.25 and l < 0.5) or l < 0.2


BG_OPTS = {"background", "activebackground", "highlightbackground", "troughcolor", "readonlybackground",
           "selectbackground"}


def _hex(rgb16):
    return "#%02x%02x%02x" % tuple(v // 257 for v in rgb16)


def _hls(hx):
    r, g, b = (int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)


def _from_hls(h, l, s):
    r, g, b = colorsys.hls_to_rgb(h % 1.0, max(0, min(1, l)), max(0, min(1, s)))
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def make_mapper(theme, custom=None):
    """-> fonction (couleur d'origine « #rrggbb », option) -> nouvelle couleur."""
    base = custom if theme == "Personnalisée" else THEMES.get(theme)
    if base is None:
        return lambda c, opt: c
    gh, gl, gs = _hls(BASE_GREEN)

    if base == "night":
        def night(c, opt):
            h, l, s = _hls(c)
            if opt in BG_OPTS and l < 0.06:
                return c                                  # noir de l'image / du waterfall : gardé
            green = s > 0.15 and 0.17 < h < 0.5
            if opt in BG_OPTS:
                if green:                                 # verts EasyPal -> vert-de-gris très sombre
                    return _from_hls(0.42, 0.10 + (l - 0.3) * 0.25, 0.30)
                return _from_hls(0.40, 0.08 + (1 - l) * 0.12, 0.10)     # blancs -> presque noir
            # textes : clairs, légèrement teintés
            if green:
                return _from_hls(0.38, 0.62 + (1 - l) * 0.15, 0.55)
            if s > 0.3:
                return _from_hls(h, max(l, 0.62), s)     # rouges, jaunes : gardés lisibles
            return _from_hls(0.33, 0.86 - l * 0.25, 0.08)
        return night

    th, tl, ts = _hls(base)

    def tint(c, opt):
        h, l, s = _hls(c)
        if s < 0.12 or not (0.17 < h < 0.5):
            return c                                      # neutres (blanc, gris, noir) et rouges/jaunes
        # vert -> teinte choisie, même « position » relative en clarté / saturation
        nl = l + (tl - gl) * (1 - abs(l - gl) * 1.6) if abs(l - gl) < 0.6 else l
        ns = s * (ts / gs) if gs else ts
        return _from_hls(th, nl, min(1.0, ns))
    return tint


class Appearance:
    """Applique et ré-applique thème + police à une fenêtre et à tous ses enfants."""

    def __init__(self, root):
        self.root = root
        self.orig = {}                  # widget -> {option: valeur d'origine}
        self.theme, self.custom, self.family, self.scale = "Vert EasyPal", None, None, 1.0
        self.text = None                # couleur du texte choisie (None : celle du thème)
        self.bold = False               # tout le texte en gras
        self.map = make_mapper(self.theme)
        self.named = {}
        for n in ("TkDefaultFont", "TkTextFont", "TkFixedFont", "TkMenuFont", "TkHeadingFont",
                  "TkCaptionFont", "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"):
            try:
                try:
                    f = tkfont.nametofont(n, root=root)
                except TypeError:                 # Python < 3.10 (version Windows 7)
                    f = tkfont.Font(root=root, name=n, exists=True)
                self.named[n] = (f, dict(f.actual()))
            except tk.TclError:
                pass
        self.style = ttk.Style(root)
        self.ttk_theme0 = self.style.theme_use()
        self.ttk_fg0 = {st: self.style.lookup(st, "foreground") for st in TTK_TEXT}

    def set(self, theme=None, custom=None, family=None, scale=None, text=None, bold=None):
        if theme is not None:
            self.theme = theme
        if custom is not None:
            self.custom = custom
        if family is not None:
            self.family = None if family in ("", "(par défaut)") else family
        if scale is not None:
            self.scale = float(scale)
        if text is not None:
            self.text = text or None             # "" : couleur du thème
        if bold is not None:
            self.bold = bool(bold)
        base = make_mapper(self.theme, self.custom)
        txt = self.text

        def mapper(c, opt):
            if txt and opt in ("foreground", "insertbackground") and is_text_color(c):
                return txt
            return base(c, opt)
        self.map = mapper
        self._named_fonts()
        self._ttk()
        self.apply(self.root)

    # ---------------------------------------------------------------- polices
    def _size(self, size):
        size = int(size)
        new = int(round(abs(size) * self.scale)) or 1
        return -new if size < 0 else new

    def _named_fonts(self):
        for n, (f, a) in self.named.items():
            fam = a["family"]
            if self.family and n != "TkFixedFont":
                fam = self.family
            f.configure(family=fam, size=self._size(a["size"]),
                        weight="bold" if self.bold else a.get("weight", "normal"))

    def _font(self, desc):
        try:
            parts = list(self.root.tk.splitlist(desc))
        except tk.TclError:
            return None
        if len(parts) == 1 and parts[0] in self.named:
            return None                                    # police nommée : déjà réglée
        if len(parts) < 2:
            return None
        fam, rest = parts[0], parts[1:]
        try:
            size = int(rest[0])
        except ValueError:
            return None
        if fam.lower() in MONO:
            new_fam = fam                                  # listes alignées : on garde le chasse fixe
        elif fam in self.named or fam.startswith("Tk"):
            new_fam = self.family or self.named.get("TkDefaultFont", (None, {"family": fam}))[1]["family"]
        else:
            new_fam = self.family or fam
        styles = [s for s in rest[1:] if s != "normal"]
        if self.bold and "bold" not in styles:
            styles.append("bold")
        return (new_fam, self._size(size), *styles)

    # ---------------------------------------------------------------- couleurs
    def _norm(self, w, c):
        try:
            return _hex(w.winfo_rgb(c))
        except tk.TclError:
            return None

    def apply(self, top):
        """Applique le thème courant à top et à tous ses descendants."""
        stack = [top]
        while stack:
            w = stack.pop()
            if getattr(w, "_no_theme", False):
                continue
            try:
                stack.extend(w.winfo_children())
            except tk.TclError:
                continue
            if getattr(w, "_no_theme", False):
                continue                                   # ex. bandeau de mise à jour : couleurs fixes
            if isinstance(w, ttk.Widget):
                continue                                   # réglés par le style ttk
            try:
                keys = set(w.keys())
            except tk.TclError:
                continue
            o = self.orig.get(w)
            if o is None:
                o = {}
                for opt in COLOR_OPTS:
                    if opt in keys:
                        try:
                            v = w.cget(opt)
                        except tk.TclError:
                            continue
                        n = self._norm(w, v) if v else None
                        if n:
                            o[opt] = n
                if "font" in keys:
                    try:
                        o["font"] = str(w.cget("font"))
                    except tk.TclError:
                        pass
                self.orig[w] = o
            for opt, c in o.items():
                try:
                    if opt == "font":
                        f = self._font(c)
                        if f is not None:
                            w.configure(font=f)
                    else:
                        w.configure(**{opt: self.map(c, opt)})
                except tk.TclError:
                    pass
        # les widgets détruits ne gardent pas leurs réglages
        for w in [w for w in self.orig if not self._alive(w)]:
            del self.orig[w]

    @staticmethod
    def _alive(w):
        try:
            return bool(w.winfo_exists())
        except tk.TclError:
            return False

    # ---------------------------------------------------------------- ttk
    def _ttk(self):
        s = self.style
        if self.theme == "Nuit":
            if s.theme_use() != "clam":
                s.theme_use("clam")
            bg, fg, field, sel, acc = "#1b2420", "#d8e8dc", "#26322c", "#2f6b48", "#3f7f5a"
            s.configure(".", background=bg, foreground=fg, fieldbackground=field, bordercolor="#3a4a42",
                        lightcolor=bg, darkcolor=bg, troughcolor=field, selectbackground=sel,
                        selectforeground="white", insertcolor=fg)
            for st in ("TFrame", "TLabelframe", "TLabelframe.Label", "TLabel", "TCheckbutton", "TRadiobutton",
                       "TNotebook"):
                s.configure(st, background=bg, foreground=fg)
            s.configure("TButton", background="#2c3a33", foreground=fg)
            s.map("TButton", background=[("active", acc)])
            s.configure("TNotebook.Tab", background="#26322c", foreground=fg)
            s.map("TNotebook.Tab", background=[("selected", acc)], foreground=[("selected", "white")])
            s.configure("TEntry", fieldbackground=field, foreground=fg)
            s.configure("TCombobox", fieldbackground=field, foreground=fg, background="#2c3a33")
            s.map("TCombobox", fieldbackground=[("readonly", field)], foreground=[("readonly", fg)])
            s.configure("TSpinbox", fieldbackground=field, foreground=fg, background="#2c3a33")
            s.configure("Treeview", background=field, fieldbackground=field, foreground=fg)
            s.configure("Treeview.Heading", background="#2c3a33", foreground=fg)
            s.configure("Horizontal.TProgressbar", background=acc, troughcolor=field)
            s.configure("Horizontal.TScale", background=bg, troughcolor=field)
        else:
            if s.theme_use() != self.ttk_theme0:
                s.theme_use(self.ttk_theme0)               # thème natif (Windows) d'origine
        # couleur du texte choisie (ou celle d'origine)
        for st in TTK_TEXT:
            try:
                if self.text:
                    s.configure(st, foreground=self.text)
                elif self.theme != "Nuit":
                    s.configure(st, foreground=self.ttk_fg0.get(st) or "")
            except tk.TclError:
                pass
        # barre de progression aux couleurs du thème
        acc = self.map("#2f9e2f", "background")
        try:
            s.configure("Horizontal.TProgressbar", background=acc)
        except tk.TclError:
            pass
