"""Mise à jour automatique depuis les « Releases » GitHub du projet.

- check()     : dernière version publiée (numéro, nouveautés, lien de l'exe, taille, empreinte)
- download()  : télécharge l'exe à côté de l'actuel, vérifie taille et SHA-256
- install()   : remplace l'exe en cours (renommé en .old, ce que Windows permet même
                pendant qu'il tourne), relance la nouvelle version ; l'ancien est effacé
                au démarrage suivant (cleanup()).

Seuls les fichiers publiés sur github.com/f4gopdenis-cyber/HFImage_F4GOP sont acceptés.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request

REPO = "f4gopdenis-cyber/HFImage_F4GOP"
LATEST_URL = os.environ.get("HFIMAGE_UPDATE_URL") or f"https://api.github.com/repos/{REPO}/releases/latest"
PAGE_URL = f"https://github.com/{REPO}/releases/latest"
try:
    from buildinfo import LEGACY
except ImportError:
    LEGACY = False
ASSET_NAME = "HFImage_F4GOP_Win7.exe" if LEGACY else "HFImage_F4GOP.exe"
ALLOWED = (f"https://github.com/{REPO}/releases/download/",)
UA = {"User-Agent": "HFImage-F4GOP-updater", "Accept": "application/vnd.github+json"}


def parse_version(s):
    """« v0.19 » / « 0.19.1 » -> (0, 19, 1) ; None si illisible."""
    m = re.search(r"(\d+(?:\.\d+)+)", s or "")
    return tuple(int(x) for x in m.group(1).split(".")) if m else None


def newer(remote, local):
    r, l = parse_version(remote), parse_version(local)
    if not r or not l:
        return False
    n = max(len(r), len(l))
    return r + (0,) * (n - len(r)) > l + (0,) * (n - len(l))


def check(timeout=10):
    """-> dict(version, notes, url, size, sha256, page) de la dernière version publiée."""
    req = urllib.request.Request(LATEST_URL, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode("utf-8"))
    asset = next((a for a in d.get("assets", []) if a.get("name") == ASSET_NAME), None)
    if asset is None and not LEGACY:      # la version Windows 7 ne prend jamais l'exe normal
        asset = next((a for a in d.get("assets", []) if a.get("name", "").lower().endswith(".exe")
                      and "win7" not in a.get("name", "").lower()), None)
    info = {"version": (parse_version(d.get("tag_name")) and ".".join(map(str, parse_version(d["tag_name"]))))
            or d.get("tag_name", "?"),
            "notes": (d.get("body") or "").strip(), "page": d.get("html_url") or PAGE_URL,
            "url": None, "size": None, "sha256": None, "pending": asset is None and LEGACY}
    if asset:
        info["url"] = asset.get("browser_download_url")
        info["size"] = asset.get("size")
        dig = asset.get("digest") or ""
        if dig.startswith("sha256:"):
            info["sha256"] = dig.split(":", 1)[1].lower()
    return info


def frozen():
    """Programme lancé depuis l'exe (et non depuis les sources Python) ?"""
    return bool(getattr(sys, "frozen", False))


def download(info, progress=lambda f: None, stop=None):
    """Télécharge le nouvel exe à côté de l'actuel. -> chemin du fichier téléchargé."""
    url = info.get("url") or ""
    test = bool(os.environ.get("HFIMAGE_UPDATE_URL"))      # essais : serveur local autorisé
    if not test and not url.startswith(ALLOWED):
        raise ValueError(f"adresse de téléchargement refusée : {url}")
    folder = os.path.dirname(os.path.abspath(sys.executable if frozen() else __file__))
    dest = os.path.join(folder, f"HFImage_F4GOP_{info['version']}.exe")
    part = dest + ".part"
    h = hashlib.sha256()
    got = 0
    req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]})
    with urllib.request.urlopen(req, timeout=30) as r, open(part, "wb") as f:
        total = info.get("size") or int(r.headers.get("Content-Length") or 0)
        while True:
            if stop is not None and stop.is_set():
                raise RuntimeError("téléchargement annulé")
            b = r.read(256 * 1024)
            if not b:
                break
            f.write(b)
            h.update(b)
            got += len(b)
            if total:
                progress(min(1.0, got / total))
    if info.get("size") and got != info["size"]:
        os.remove(part)
        raise ValueError(f"fichier incomplet ({got} octets au lieu de {info['size']})")
    if info.get("sha256") and h.hexdigest() != info["sha256"]:
        os.remove(part)
        raise ValueError("empreinte SHA-256 différente : fichier abîmé, mise à jour refusée")
    os.replace(part, dest)
    return dest


def install(new_exe):
    """Remplace l'exe en cours par new_exe et lance la nouvelle version.
    -> True si la nouvelle version a été lancée (l'appelant doit alors se fermer)."""
    if not frozen():
        return False
    exe = os.path.abspath(sys.executable)
    old = exe + ".old"
    try:
        if os.path.exists(old):
            os.remove(old)
    except OSError:
        old = exe + f".{os.getpid()}.old"
    os.replace(exe, old)                     # Windows permet de renommer l'exe en cours
    try:
        os.replace(new_exe, exe)
    except OSError:
        os.replace(old, exe)                 # on remet l'ancien en place
        raise
    env = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT="1")   # nouvel exe : environnement neuf
    flags = 0x00000008 | 0x00000200 if sys.platform.startswith("win") else 0   # DETACHED | NEW_GROUP
    subprocess.Popen([exe], cwd=os.path.dirname(exe), env=env, close_fds=True, creationflags=flags)
    return True


def refresh_icon(path):
    """Prévient l'explorateur Windows que le fichier a changé (nouvelle icône)."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        SHCNE_UPDATEITEM, SHCNE_ASSOCCHANGED, SHCNF_PATHW, SHCNF_IDLIST = 0x2000, 0x08000000, 0x0005, 0
        ctypes.windll.shell32.SHChangeNotify(SHCNE_UPDATEITEM, SHCNF_PATHW, ctypes.c_wchar_p(path), None)
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
    except Exception:
        pass


def cleanup():
    """Au démarrage : efface l'ancien exe laissé par une mise à jour."""
    if not frozen():
        return
    exe = os.path.abspath(sys.executable)
    folder = os.path.dirname(exe)
    try:
        if os.path.exists(exe + ".old"):
            os.remove(exe + ".old")
            refresh_icon(exe)                 # l'explorateur affiche la nouvelle icône
    except OSError:
        pass
    for n in os.listdir(folder):
        if n.startswith("HFImage_F4GOP") and (n.endswith(".old") or n.endswith(".part")):
            try:
                os.remove(os.path.join(folder, n))
            except OSError:
                pass
