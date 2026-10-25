"""Mise à jour automatique depuis les « Releases » GitHub du projet.

- check()     : dernière version publiée (numéro, nouveautés, lien de l'exe, taille, empreinte)
- download()  : télécharge l'exe à côté de l'actuel, vérifie taille et SHA-256
- install()   : remplace l'exe en cours (renommé en .old, ce que Windows permet même
                pendant qu'il tourne), relance la nouvelle version ; l'ancien est effacé
                au démarrage suivant (cleanup()).

Seuls les fichiers publiés sur github.com/f4gopdenis-cyber/HFImage_F4GOP sont acceptés.
"""
import netssl
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = "f4gopdenis-cyber/HFImage_F4GOP"
LATEST_URL = os.environ.get("HFIMAGE_UPDATE_URL") or f"https://api.github.com/repos/{REPO}/releases/latest"
PAGE_URL = f"https://github.com/{REPO}/releases/latest"
try:
    from buildinfo import LEGACY
except ImportError:
    LEGACY = False
WIN = sys.platform.startswith("win")
LINUX_BIN = "HFImage_F4GOP_Linux"                 # Linux : un seul fichier exécutable…
LINUX_ASSET = LINUX_BIN + ".tar.gz"               # …publié dans une archive (garde le droit d'exécution)
ASSET_NAME = ("HFImage_F4GOP_Win7.exe" if LEGACY else "HFImage_F4GOP.exe") if WIN else LINUX_ASSET
ALLOWED = (f"https://github.com/{REPO}/releases/download/",)
DOWNLOAD_BASE = ALLOWED[0]
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


RATE_LIMIT_MSG = "GitHub limite le nombre de vérifications : réessayez dans une heure."


def check(timeout=10):
    """-> dict(version, notes, url, size, sha256, page) de la dernière version publiée.
    L'API GitHub n'accepte que 60 questions par heure pour une même connexion Internet (sans
    compte) : si elle refuse, on lit la page « dernière version » du site, qui n'a pas cette limite."""
    try:
        return _check_api(timeout)
    except urllib.error.HTTPError as e:
        if os.environ.get("HFIMAGE_UPDATE_URL"):              # essais : pas de secours
            raise
        try:
            return check_page(timeout)
        except Exception:
            if e.code in (403, 429):
                raise RuntimeError(RATE_LIMIT_MSG) from e
            raise e


def _check_api(timeout):
    req = urllib.request.Request(LATEST_URL, headers=UA)
    with netssl.urlopen(req, timeout) as r:
        d = json.loads(r.read().decode("utf-8"))
    asset = next((a for a in d.get("assets", []) if a.get("name") == ASSET_NAME), None)
    if asset is None and not LEGACY and WIN:   # la version Windows 7 ne prend jamais l'exe normal
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


def check_page(timeout=10, page=None, opener=None):
    """Secours sans l'API : github.com/…/releases/latest renvoie vers …/releases/tag/vX.YY ; le
    fichier est alors à l'adresse standard …/releases/download/vX.YY/<nom>. Sa taille est lue
    sans le télécharger (premier octet seulement). Pas de nouveautés ni d'empreinte SHA-256."""
    op = opener or urllib.request.build_opener()
    req = urllib.request.Request(page or PAGE_URL, headers={"User-Agent": UA["User-Agent"]})
    with op.open(req, timeout=timeout) as r:
        final = r.geturl()
    m = re.search(r"/releases/tag/([^/?#]+)", final)
    if not m:
        raise RuntimeError("page des versions GitHub illisible")
    tag = urllib.parse.unquote(m.group(1))
    v = parse_version(tag)
    info = {"version": ".".join(map(str, v)) if v else tag, "notes": "", "page": final,
            "url": None, "size": None, "sha256": None, "pending": False}
    url = f"{DOWNLOAD_BASE}{urllib.parse.quote(tag)}/{ASSET_NAME}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"], "Range": "bytes=0-0"})
        with op.open(req, timeout=timeout) as r:
            cr = r.headers.get("Content-Range") or ""
            size = int(cr.rsplit("/", 1)[1]) if "/" in cr and cr.rsplit("/", 1)[1].isdigit() else (
                int(r.headers.get("Content-Length") or 0) if r.status == 200 else 0)
        info["url"] = url
        info["size"] = size or None
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        info["pending"] = LEGACY                # exe Windows 7 fabriqué quelques minutes après
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
    dest = os.path.join(folder, f"HFImage_F4GOP_{info['version']}" + (".exe" if WIN else ".tar.gz"))
    part = dest + ".part"
    h = hashlib.sha256()
    got = 0
    req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]})
    with netssl.urlopen(req, 30) as r, open(part, "wb") as f:
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
    if not WIN:
        dest = _extract_linux(dest)
    return dest


def _extract_linux(archive):
    """Linux : sort l'exécutable de l'archive téléchargée (un seul fichier attendu, rien d'autre)."""
    import tarfile
    out = archive[:-len(".tar.gz")] + "_Linux"
    with tarfile.open(archive, "r:gz") as t:
        m = next((m for m in t.getmembers() if m.isfile() and os.path.basename(m.name) == LINUX_BIN), None)
        if m is None:
            raise ValueError("archive Linux sans le programme")
        with t.extractfile(m) as src, open(out + ".part", "wb") as dst:
            while True:
                b = src.read(256 * 1024)
                if not b:
                    break
                dst.write(b)
    os.chmod(out + ".part", 0o755)
    os.replace(out + ".part", out)
    try:
        os.remove(archive)
    except OSError:
        pass
    return out


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
    os.replace(exe, old)                     # Windows (et Linux) permettent de renommer l'exe en cours
    try:
        os.replace(new_exe, exe)
        if not WIN:
            os.chmod(exe, 0o755)
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
