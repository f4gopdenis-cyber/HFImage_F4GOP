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

# ---------------------------------------------------------------- style « Moderne » (1.54)
# Tout plat (sans relief 3D), une seule couleur d'accent, police moderne, barre du haut.
# Trois ambiances ; le style « Classique » reste celui d'EasyPal, avec ses couleurs ci-dessus.
MODERN = {
    "Vert EasyPal": dict(bg="#e3f5e3", panel="#c8edc8", field="#ffffff", bar="#33d633", bar_fg="#062e06",
                         fg="#0b2a0f", muted="#3f6b45", border="#8fd68f", button="#ffffff", button_fg="#0b2a0f",
                         accent="#1f9e2f", accent_fg="#ffffff", bad="#e53935", dark=False, top="#33d633",
                         top_fg="#062e06", top_muted="#14501c"),
    "Sombre": dict(bg="#1d2127", panel="#242931", field="#1a1e24", bar="#2b313a", bar_fg="#e9edf2",
                   fg="#e3e7ec", muted="#98a3af", border="#363d47", button="#2f3640", button_fg="#e3e7ec",
                   accent="#2fbf71", accent_fg="#ffffff", bad="#ff5d6c", dark=True, top="#15191e"),
    "Clair": dict(bg="#eef1f5", panel="#f8fafc", field="#ffffff", bar="#ffffff", bar_fg="#1c2430",
                  fg="#1c2430", muted="#6b7684", border="#d8dee6", button="#e7ecf2", button_fg="#1c2430",
                  accent="#2f7de1", accent_fg="#ffffff", bad="#e0414f", dark=False, top="#ffffff"),
    "Vert radio": dict(bg="#10231b", panel="#143024", field="#0e1f17", bar="#18382a", bar_fg="#e6f4ec",
                       fg="#e6f4ec", muted="#8fb3a0", border="#1f4434", button="#1b3d2e", button_fg="#e6f4ec",
                       accent="#2fd17a", accent_fg="#06110a", bad="#ff6b6b", dark=True, top="#0a1611"),
}
MODERN_FONTS = ("Segoe UI", "Inter", "Noto Sans", "DejaVu Sans")
# réglages de forme gardés pour revenir au style Classique
SHAPE_OPTS = ("relief", "borderwidth", "highlightthickness", "sashrelief", "sashwidth", "selectcolor",
              "overrelief")


def modern_role(c, opt):
    """Couleur d'origine (palette EasyPal) -> rôle dans le style Moderne."""
    h, l, s = _hls(c)
    green = s > 0.15 and 0.17 < h < 0.5
    if opt in ("background", "activebackground", "highlightbackground", "troughcolor", "readonlybackground"):
        if l < 0.06:
            return "keep"                        # noir : image, waterfall
        if green and l < 0.42:
            return "border"
        if green and l < 0.62:
            return "bar"
        if green:
            return "panel"
        if l > 0.97:
            return "field"
        if s < 0.12:
            return "bg"
        return "keep"
    if opt == "selectbackground":
        return "accent"
    if opt in ("foreground", "activeforeground", "insertbackground", "disabledforeground"):
        if s < 0.25 and l > 0.85:
            return "bar_fg"
        if (s < 0.25 and l < 0.5) or l < 0.2:
            return "fg"
        return "color"
    return "keep"


def modern_color(P, c, opt, bg_role=None, cls=""):
    """Couleur d'origine -> couleur du style Moderne (bg_role : rôle du fond du widget)."""
    r = modern_role(c, opt)
    if cls == "Button" and opt == "background" and r in ("field", "bg", "panel", "bar"):
        return P["button"]
    if cls == "Button" and opt == "foreground" and r in ("fg", "bar_fg"):
        return P["button_fg"]
    if r == "keep":
        return c
    if r == "color":                             # rouge d'alerte, bleu « HYB »… : gardés, éclaircis si sombre
        if P["dark"]:
            h, l, s = _hls(c)
            return _from_hls(h, max(l, 0.66), s)
        return c
    if r == "bar" and cls == "Button":
        return P["button"]
    if r in ("fg", "bar_fg") and bg_role == "bar" and cls != "Button":
        return P["bar_fg"]                       # texte posé sur une barre de titre
    if r == "bar_fg" and bg_role != "bar":
        return P["fg"]
    return P[r]
# taille du texte en points (9 = taille normale de Windows) -> facteur appliqué aux polices
FONT_SIZES = {str(p): p / 9.0 for p in range(8, 15)}
OLD_SIZES = {"Petite": "8", "Normale": "9", "Grande": "11", "Très grande": "13"}   # anciens réglages


def size_name(v):
    """Réglage de taille (ancien nom ou nombre) -> "8" … "14"."""
    v = OLD_SIZES.get(str(v), str(v))
    return v if v in FONT_SIZES else "9"
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
        self.modern = None              # style Moderne : nom de l'ambiance (None : Classique)
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

    def palette(self):
        """Palette du style Moderne en cours (None : style Classique)."""
        return MODERN.get(self.modern) if self.modern else None

    def modern_font(self):
        try:
            have = {f.lower() for f in tkfont.families(self.root)}
        except tk.TclError:
            have = set()
        return next((f for f in MODERN_FONTS if f.lower() in have), None)

    def set(self, theme=None, custom=None, family=None, scale=None, text=None, bold=None, modern=False):
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
        if modern is not False:
            self.modern = modern if modern in MODERN else None
        P = self.palette()
        if P:
            base = lambda c, opt: modern_color(P, c, opt, "field")       # éléments de listes, etc.
        else:
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

    def _family(self):
        """Police choisie ; en style Moderne sans choix : une police moderne (Segoe UI…)."""
        if self.family:
            return self.family
        return self.modern_font() if self.modern else None

    def _named_fonts(self):
        fam_sel = self._family()
        for n, (f, a) in self.named.items():
            fam = a["family"]
            if fam_sel and n != "TkFixedFont":
                fam = fam_sel
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
        fam_sel = self._family()
        if fam.lower() in MONO:
            new_fam = fam                                  # listes alignées : on garde le chasse fixe
        elif fam in self.named or fam.startswith("Tk"):
            new_fam = fam_sel or self.named.get("TkDefaultFont", (None, {"family": fam}))[1]["family"]
        else:
            new_fam = fam_sel or fam
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
                shape = {}
                for opt in SHAPE_OPTS:
                    if opt in keys:
                        try:
                            shape[opt] = str(w.cget(opt))
                        except tk.TclError:
                            pass
                o["_shape"] = shape
                self.orig[w] = o
            P = self.palette()
            cls = w.winfo_class()
            bg_role = modern_role(o["background"], "background") if P and "background" in o else None
            for opt, c in o.items():
                if opt == "_shape":
                    continue
                try:
                    if opt == "font":
                        f = self._font(c)
                        if f is not None:
                            w.configure(font=f)
                    elif P:
                        new = modern_color(P, c, opt, bg_role, cls)
                        if opt == "activebackground" and cls == "Button":
                            new = P["accent"]
                        elif opt == "activeforeground" and cls == "Button":
                            new = P["accent_fg"]
                        w.configure(**{opt: new})
                    else:
                        w.configure(**{opt: self.map(c, opt)})
                except tk.TclError:
                    pass
            try:
                if P:
                    self._flat(w, cls, P, bg_role)
                elif o.get("_shape"):
                    w.configure(**o["_shape"])             # style Classique : formes d'origine
            except tk.TclError:
                pass
        # les widgets détruits ne gardent pas leurs réglages
        for w in [w for w in self.orig if not self._alive(w)]:
            del self.orig[w]

    @staticmethod
    def _flat(w, cls, P, bg_role):
        """Style Moderne : plus de relief 3D, bordures fines."""
        if cls == "Button":
            w.configure(relief="flat", bd=0, highlightthickness=0, overrelief="flat")
        elif cls in ("Checkbutton", "Radiobutton"):
            w.configure(bd=0, highlightthickness=0,
                        selectcolor=P["field"] if bg_role != "bar" else P["bar"])
        elif cls in ("Listbox", "Text", "Entry", "Spinbox"):
            w.configure(relief="flat", bd=0, highlightthickness=1, highlightbackground=P["border"],
                        highlightcolor=P["accent"])
        elif cls == "Panedwindow":
            w.configure(sashrelief="flat")
        elif cls in ("Frame", "Label", "Labelframe", "Canvas", "Scale"):
            if str(w.cget("relief")) not in ("flat", ""):
                w.configure(relief="flat")

    @staticmethod
    def _alive(w):
        try:
            return bool(w.winfo_exists())
        except tk.TclError:
            return False

    # ---------------------------------------------------------------- ttk
    def _ttk_modern(self, P):
        s = self.style
        if "hfmoderne" not in s.theme_names():
            s.theme_create("hfmoderne", parent="clam")
        s.theme_use("hfmoderne")
        fam = self._family() or "TkDefaultFont"
        size = max(8, int(round(9 * self.scale)))
        s.configure(".", background=P["bg"], foreground=P["fg"], fieldbackground=P["field"], bordercolor=P["border"],
                    lightcolor=P["bg"], darkcolor=P["bg"], troughcolor=P["field"], selectbackground=P["accent"],
                    selectforeground=P["accent_fg"], insertcolor=P["fg"], focuscolor=P["accent"])
        for st in ("TFrame", "TLabelframe", "TLabelframe.Label", "TLabel", "TCheckbutton", "TRadiobutton"):
            s.configure(st, background=P["bg"], foreground=P["fg"])
        s.configure("TLabelframe", bordercolor=P["border"])
        for st in ("TCheckbutton", "TRadiobutton"):
            s.configure(st, padding=(0, 2, 4, 2), indicatormargin=(0, 0, 4, 0), indicatorbackground=P["field"],
                        indicatorforeground=P["accent_fg"], upperbordercolor=P["border"],
                        lowerbordercolor=P["border"])
        for st in ("TCheckbutton", "TRadiobutton"):
            s.map(st, background=[("active", P["bg"])],
                  indicatorbackground=[("selected", P["accent"]), ("disabled", P["bg"])],
                  indicatorforeground=[("selected", P["accent_fg"])])
        s.configure("TButton", background=P["button"], foreground=P["button_fg"], borderwidth=0, relief="flat",
                    padding=(10, 4), bordercolor=P["button"], lightcolor=P["button"], darkcolor=P["button"])
        s.map("TButton", background=[("disabled", P["bg"]), ("active", P["accent"])],
              foreground=[("disabled", P["muted"]), ("active", P["accent_fg"])])
        s.configure("Accent.TButton", background=P["accent"], foreground=P["accent_fg"], padding=(14, 5),
                    font=(fam, size + 1, "bold"), bordercolor=P["accent"], lightcolor=P["accent"],
                    darkcolor=P["accent"])
        s.map("Accent.TButton", background=[("disabled", P["button"]), ("active", P["accent"])],
              foreground=[("disabled", P["muted"]), ("active", P["accent_fg"])])
        s.configure("TNotebook", background=P["bg"], borderwidth=0, tabmargins=(6, 6, 6, 0), bordercolor=P["bg"],
                    lightcolor=P["bg"], darkcolor=P["bg"])
        s.configure("TNotebook.Tab", background=P["bg"], foreground=P["muted"], padding=(18, 6), borderwidth=0,
                    font=(fam, size + 1, "bold"), bordercolor=P["bg"], lightcolor=P["bg"], darkcolor=P["bg"])
        s.map("TNotebook.Tab", background=[("selected", P["accent"]), ("active", P["button"])],
              foreground=[("selected", P["accent_fg"]), ("active", P["fg"])], padding=[("selected", (18, 6))],
              expand=[("selected", (0, 0, 0, 0))], lightcolor=[("selected", P["accent"])],
              bordercolor=[("selected", P["accent"])])
        for st in ("TEntry", "TCombobox", "TSpinbox"):
            s.configure(st, fieldbackground=P["field"], foreground=P["fg"], background=P["button"],
                        bordercolor=P["border"], lightcolor=P["field"], darkcolor=P["field"], arrowcolor=P["fg"],
                        insertcolor=P["fg"])
        s.map("TCombobox", fieldbackground=[("readonly", P["field"]), ("disabled", P["bg"])],
              foreground=[("readonly", P["fg"]), ("disabled", P["muted"])],
              background=[("readonly", P["button"])], bordercolor=[("focus", P["accent"])])
        s.map("TEntry", fieldbackground=[("disabled", P["bg"])], foreground=[("disabled", P["muted"])],
              bordercolor=[("focus", P["accent"])])
        s.configure("Treeview", background=P["field"], fieldbackground=P["field"], foreground=P["fg"],
                    bordercolor=P["border"])
        s.map("Treeview", background=[("selected", P["accent"])], foreground=[("selected", P["accent_fg"])])
        s.configure("Treeview.Heading", background=P["bar"], foreground=P["bar_fg"], bordercolor=P["border"],
                    relief="flat")
        s.configure("Horizontal.TProgressbar", background=P["accent"], troughcolor=P["field"],
                    bordercolor=P["border"], lightcolor=P["accent"], darkcolor=P["accent"])
        s.configure("Horizontal.TScale", background=P["button"], troughcolor=P["field"], bordercolor=P["border"])
        for o in ("Vertical", "Horizontal"):
            s.configure(f"{o}.TScrollbar", background=P["button"], troughcolor=P["bg"], arrowcolor=P["muted"],
                        bordercolor=P["bg"], lightcolor=P["button"], darkcolor=P["button"])
        s.configure("TMenubutton", background=P["button"], foreground=P["button_fg"], bordercolor=P["border"])

    def _ttk(self):
        s = self.style
        P = self.palette()
        if P:
            return self._ttk_modern(P)
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
