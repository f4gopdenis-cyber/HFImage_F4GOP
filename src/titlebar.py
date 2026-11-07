"""2.22 : barres de titre des fenêtres aux couleurs de l'ambiance (style Moderne).

Windows 11 : barre de titre, texte du titre et contour de la fenêtre colorés (DWM).
Windows 10 : barre de titre sombre seulement (les couleurs n'y existent pas).
Windows 7, Linux, macOS : rien (la barre reste celle du système). Un refus de Windows ne casse rien.
"""
import sys

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19      # premières versions de Windows 10
DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36
DWMWA_COLOR_DEFAULT = 0xFFFFFFFF


def colorref(hex_color):
    """« #rrggbb » -> COLORREF Windows (0x00BBGGRR)."""
    c = str(hex_color).lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return (b << 16) | (g << 8) | r


def plan(P):
    """Palette (ou None : style Classique) -> [(attribut, valeur)] à donner à Windows."""
    if not P:
        return [(DWMWA_USE_IMMERSIVE_DARK_MODE, 0), (DWMWA_BORDER_COLOR, DWMWA_COLOR_DEFAULT),
                (DWMWA_CAPTION_COLOR, DWMWA_COLOR_DEFAULT), (DWMWA_TEXT_COLOR, DWMWA_COLOR_DEFAULT)]
    top = P.get("top", P["bg"])
    return [(DWMWA_USE_IMMERSIVE_DARK_MODE, 1 if P.get("dark") else 0),
            (DWMWA_CAPTION_COLOR, colorref(top)),
            (DWMWA_TEXT_COLOR, colorref(P.get("top_fg", P["fg"]))),
            (DWMWA_BORDER_COLOR, colorref(P.get("border", top)))]


def apply(win, P):
    """Colore la barre de titre de la fenêtre Tk `win`. -> True si Windows a accepté quelque chose."""
    if not sys.platform.startswith("win"):
        return False
    try:
        import ctypes
        from ctypes import wintypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
        dwm = ctypes.windll.dwmapi
        ok = False
        for attr, val in plan(P):
            v = wintypes.DWORD(val)
            r = dwm.DwmSetWindowAttribute(wintypes.HWND(hwnd), wintypes.DWORD(attr), ctypes.byref(v),
                                          ctypes.sizeof(v))
            if r != 0 and attr == DWMWA_USE_IMMERSIVE_DARK_MODE:
                r = dwm.DwmSetWindowAttribute(wintypes.HWND(hwnd), wintypes.DWORD(DWMWA_USE_IMMERSIVE_DARK_MODE_OLD),
                                              ctypes.byref(v), ctypes.sizeof(v))
            ok = ok or r == 0
        return ok
    except Exception:
        return False
