"""Page HTML -> image : capture par Microsoft Edge (ou Google Chrome) en mode « headless ».

Edge est présent sur Windows 10 et 11 ; il charge la page comme un navigateur normal
(images sur Internet comprises), attend quelques secondes, puis enregistre une capture
PNG de la taille demandée. La capture s'envoie ensuite comme n'importe quelle image :
tous les correspondants la voient telle quelle, EasyPal et QSSTV compris.
Les animations (marquee, GIF) sont figées à l'instant de la capture.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

SIZES = {"800×600": (800, 600), "1024×768": (1024, 768), "1280×960": (1280, 960), "1280×720": (1280, 720)}
DEFAULT_SIZE = "1024×768"
WAIT_MS = 6000            # temps laissé à la page pour charger ses images
TIMEOUT_S = 60


def _registry_app_path(exe):
    if not sys.platform.startswith("win"):
        return None
    try:
        import winreg
    except ImportError:
        return None
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(root, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}") as k:
                p = winreg.QueryValue(k, None)
                if p and os.path.exists(p.strip('"')):
                    return p.strip('"')
        except OSError:
            pass
    return None


def find_browser():
    """Chemin de Microsoft Edge (de préférence) ou de Google Chrome, ou None."""
    env = os.environ.get("HFIMAGE_BROWSER")
    if env and os.path.exists(env):
        return env
    roots = [os.environ.get(k) for k in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
    rel = [r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe"]
    for exe, sub in (("msedge.exe", rel[0]), ("chrome.exe", rel[1])):
        for r in roots:
            if r and os.path.exists(os.path.join(r, sub)):
                return os.path.join(r, sub)
        p = _registry_app_path(exe)
        if p:
            return p
    for name in ("microsoft-edge", "google-chrome", "chromium", "chromium-browser"):
        p = shutil.which(name)
        if p:
            return p
    return None


def _utf8_copy(html_path, folder):
    """Page en UTF-8 qui ne le déclare pas (cas fréquent des pages écrites à la main) : le
    navigateur la lirait en Windows-1252 (« DÃ©partement »). On capture alors une copie
    qui déclare UTF-8, avec <base> vers le dossier d'origine pour les images relatives.
    -> chemin de la copie, ou None si la page est correcte telle quelle."""
    try:
        with open(html_path, "rb") as f:
            raw = f.read()
    except OSError:
        return None
    if b"charset" in raw[:4096].lower() or raw.startswith(b"\xef\xbb\xbf"):
        return None
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return None                              # vraiment en Windows-1252 : le navigateur a raison
    if raw.isascii():
        return None
    base = pathlib.Path(os.path.dirname(os.path.abspath(html_path))).as_uri() + "/"
    head = f'<meta charset="utf-8"><base href="{base}">'.encode()
    cp = os.path.join(folder, "page.html")
    with open(cp, "wb") as f:
        f.write(head + raw)
    return cp


def render(html_path, out_png, size=(1024, 768), wait_ms=WAIT_MS, timeout=TIMEOUT_S, browser=None):
    """Capture de la page html_path -> out_png (PNG de la taille demandée). Lève RuntimeError."""
    exe = browser or find_browser()
    if not exe:
        raise RuntimeError("Microsoft Edge (ou Google Chrome) est introuvable : il sert à transformer la page en image.")
    w, h = size
    out_png = os.path.abspath(out_png)
    if os.path.exists(out_png):
        os.remove(out_png)
    # profil temporaire : ne touche pas au navigateur de l'utilisateur, même s'il est ouvert
    prof = tempfile.mkdtemp(prefix="hfimage_html_")
    uri = pathlib.Path(_utf8_copy(html_path, prof) or os.path.abspath(html_path)).as_uri()
    cmd = [exe, "--headless", "--disable-gpu", "--hide-scrollbars", "--mute-audio", "--no-first-run",
           "--no-default-browser-check", "--disable-extensions", "--disable-sync", f"--user-data-dir={prof}",
           f"--window-size={w},{h}", f"--virtual-time-budget={int(wait_ms)}", f"--screenshot={out_png}", uri]
    flags = 0x08000000 if sys.platform.startswith("win") else 0          # CREATE_NO_WINDOW
    try:
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=flags)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"la page n'a pas pu être capturée en {timeout} s") from None
        except OSError as e:
            raise RuntimeError(f"le navigateur ne démarre pas : {e}") from None
        for _ in range(20):                    # le fichier peut arriver juste après la fin du processus
            if os.path.exists(out_png) and os.path.getsize(out_png) > 0:
                break
            time.sleep(0.1)
        else:
            err = (r.stderr or b"").decode(errors="replace").strip().splitlines()[-3:]
            raise RuntimeError("le navigateur n'a pas produit de capture" + (" : " + " / ".join(err) if err else ""))
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    return out_png


def is_html(path):
    return os.path.splitext(path or "")[1].lower() in (".html", ".htm", ".xhtml", ".mht", ".mhtml")
