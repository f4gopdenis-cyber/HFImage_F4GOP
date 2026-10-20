"""Glisser-déposer de fichiers depuis l'Explorateur Windows sur une fenêtre Tk (WM_DROPFILES).

hook(widget, callback) : callback(liste de chemins) est appelé dans le fil de l'interface
(par widget.after), pas depuis la procédure de fenêtre. Sans effet hors de Windows.
"""
import sys

_hooks = []          # garde les procédures en vie (sinon le ramasse-miettes les détruit)


def hook(widget, callback, toplevel=False):
    """Accepte les fichiers déposés sur `widget` (toplevel=True : sur toute sa fenêtre)."""
    if not sys.platform.startswith("win"):
        return False
    import ctypes
    from ctypes import wintypes

    user32, shell32 = ctypes.windll.user32, ctypes.windll.shell32
    LRESULT = ctypes.c_ssize_t
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    set_long = getattr(user32, "SetWindowLongPtrW", None) or user32.SetWindowLongW
    set_long.restype = ctypes.c_void_p
    set_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    user32.CallWindowProcW.restype = LRESULT
    user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                       wintypes.LPARAM]
    user32.GetParent.restype = wintypes.HWND
    user32.GetParent.argtypes = [wintypes.HWND]
    shell32.DragQueryFileW.restype = wintypes.UINT
    shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
    shell32.DragFinish.argtypes = [ctypes.c_void_p]
    shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
    WM_DROPFILES, GWLP_WNDPROC = 0x0233, -4

    hwnd = widget.winfo_id()
    if toplevel:
        hwnd = user32.GetParent(hwnd) or hwnd          # cadre Windows de la fenêtre Tk
    old = [None]

    def proc(h, msg, wp, lp):
        if msg == WM_DROPFILES:
            try:
                n = shell32.DragQueryFileW(wp, 0xFFFFFFFF, None, 0)
                paths = []
                for i in range(n):
                    size = shell32.DragQueryFileW(wp, i, None, 0) + 1
                    buf = ctypes.create_unicode_buffer(size)
                    shell32.DragQueryFileW(wp, i, buf, size)
                    paths.append(buf.value)
                shell32.DragFinish(wp)
                if paths:
                    widget.after(0, lambda p=paths: callback(p))
            except Exception:
                pass
            return 0
        return user32.CallWindowProcW(old[0], h, msg, wp, lp)

    cb = WNDPROC(proc)
    shell32.DragAcceptFiles(hwnd, True)
    old[0] = set_long(hwnd, GWLP_WNDPROC, ctypes.cast(cb, ctypes.c_void_p))
    _hooks.append(cb)
    return True
