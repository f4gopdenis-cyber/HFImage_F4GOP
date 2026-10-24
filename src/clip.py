"""Copie d'une image dans le presse-papiers (demande de VK6ATI : coller l'image dans MS Teams,
un e-mail, WhatsApp… pour les stations qui ne l'ont pas décodée).

Windows : deux formats à la fois, « PNG » (pleine qualité, transparence gardée : Teams, Office,
navigateurs) et CF_DIB (le format image classique : Paint, anciens programmes).
Linux : xclip (X11) ou wl-copy (Wayland), en image/png.
Un GIF animé est copié comme image fixe : le presse-papiers ne garde pas l'animation."""
import io
import shutil
import subprocess
import sys

from PIL import Image

LINUX_HINT = "sudo apt install xclip"


class ClipError(RuntimeError):
    pass


def _rgb(img):
    if img.mode in ("RGB", "RGBA"):
        return img
    if img.mode in ("P", "LA", "PA") or "transparency" in img.info:
        return img.convert("RGBA")
    return img.convert("RGB")


def png_bytes(img):
    b = io.BytesIO()
    _rgb(img).save(b, "PNG")
    return b.getvalue()


def dib_bytes(img):
    """Image -> CF_DIB : un BMP sans son en-tête de fichier (14 octets)."""
    im = _rgb(img)
    if im.mode == "RGBA":                      # CF_DIB : pas de transparence fiable -> fond blanc
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.getchannel("A"))
        im = bg
    b = io.BytesIO()
    im.save(b, "BMP")
    return b.getvalue()[14:]


def load(path):
    """Fichier image (y compris AVIF, WebP, JPEG 2000, GIF animé) -> image PIL (première image)."""
    import imgfmt
    try:
        im = imgfmt.open_upright(path)
    except Exception:
        im = Image.open(path)
    try:
        im.seek(0)
    except Exception:
        pass
    im.load()
    return im


def copy_image(img):
    """Met l'image dans le presse-papiers. ClipError (message en français) si impossible."""
    if sys.platform.startswith("win"):
        return _copy_windows(img)
    return _copy_linux(img)


# ------------------------------------------------------------------ Linux
def _copy_linux(img):
    data = png_bytes(img)
    for cmd in (["wl-copy", "--type", "image/png"], ["xclip", "-selection", "clipboard", "-t", "image/png", "-i"]):
        if cmd[0] == "wl-copy" and not _wayland():
            continue
        exe = shutil.which(cmd[0])
        if not exe:
            continue
        try:
            # xclip / wl-copy restent en arrière-plan pour servir le presse-papiers
            subprocess.run([exe] + cmd[1:], input=data, timeout=10, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except (OSError, subprocess.SubprocessError) as e:
            raise ClipError(f"copie impossible ({cmd[0]} : {e})") from e
    raise ClipError("Pour copier une image sous Linux, installez xclip : " + LINUX_HINT)


def _wayland():
    import os
    return bool(os.environ.get("WAYLAND_DISPLAY"))


# ------------------------------------------------------------------ Windows
def _copy_windows(img):
    import ctypes
    from ctypes import wintypes
    import time

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
    user32.RegisterClipboardFormatW.restype = wintypes.UINT
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    GMEM_MOVEABLE, CF_DIB = 0x0002, 8

    def hglobal(data):
        h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not h:
            raise ClipError("copie impossible : mémoire insuffisante")
        p = kernel32.GlobalLock(h)
        ctypes.memmove(p, data, len(data))
        kernel32.GlobalUnlock(h)
        return h

    items = [(user32.RegisterClipboardFormatW("PNG"), png_bytes(img)), (CF_DIB, dib_bytes(img))]
    for _ in range(10):                        # un autre programme peut tenir le presse-papiers
        if user32.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        raise ClipError("copie impossible : le presse-papiers est occupé par un autre programme")
    try:
        user32.EmptyClipboard()
        for fmt, data in items:
            h = hglobal(data)
            if not user32.SetClipboardData(fmt, h):
                kernel32.GlobalFree(h)         # sinon Windows en devient propriétaire
                raise ClipError("copie impossible (SetClipboardData)")
    finally:
        user32.CloseClipboard()
