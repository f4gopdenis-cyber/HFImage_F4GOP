"""Mode hybride : l'image est déposée par FTP sur un hébergement web, et seule
une courte trame radio (indicatif, taille, CRC32, lien public http/https) est
émise. Les stations qui reçoivent la trame téléchargent l'image et vérifient
qu'elle est identique (taille + CRC32) avant de l'afficher.

Aucun identifiant de serveur n'est transmis par radio.
"""
import base64
import ftplib
import io
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

MAX_DOWNLOAD = 8 * 1024 * 1024
USER_AGENT = "HFImage-F4GOP"


# ---------------------------------------------------------------- mot de passe
def protect(secret: str) -> str:
    """Chiffre le mot de passe pour le fichier de réglages (DPAPI sous Windows :
    seul ce compte Windows peut le relire)."""
    if not secret:
        return ""
    raw = secret.encode("utf-8")
    if sys.platform.startswith("win"):
        try:
            return "dpapi:" + base64.b64encode(_dpapi(raw, True)).decode()
        except Exception:
            pass
    return "b64:" + base64.b64encode(raw).decode()


def unprotect(stored: str) -> str:
    if not stored:
        return ""
    try:
        kind, _, data = stored.partition(":")
        raw = base64.b64decode(data)
        if kind == "dpapi":
            return _dpapi(raw, False).decode("utf-8")
        if kind == "b64":
            return raw.decode("utf-8")
    except Exception:
        return ""
    return stored


def _dpapi(data: bytes, encrypt: bool) -> bytes:
    import ctypes
    from ctypes import wintypes

    class BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    src = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    dst = BLOB()
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    fn = crypt32.CryptProtectData if encrypt else crypt32.CryptUnprotectData
    if not fn(ctypes.byref(src), None, None, None, None, 0, ctypes.byref(dst)):
        raise OSError("DPAPI")
    try:
        return ctypes.string_at(dst.pbData, dst.cbData)
    finally:
        kernel32.LocalFree(dst.pbData)


# ---------------------------------------------------------------- envoi
def remote_name(callsign: str, fmt: str) -> str:
    call = "".join(c for c in callsign.upper() if c.isalnum()) or "NOCALL"
    return f"{call}_{time.strftime('%Y%m%d_%H%M%S', time.gmtime())}.{fmt}"


def public_url(base: str, name: str) -> str:
    return base.rstrip("/") + "/" + urllib.parse.quote(name)


def _ftp_connect(cfg, timeout=20):
    host, port = cfg["host"].strip(), int(cfg.get("port") or 21)
    if not host:
        raise RuntimeError("serveur FTP non renseigné (onglet Réglages)")
    try:
        if cfg.get("tls"):
            ftp = ftplib.FTP_TLS(timeout=timeout)
            ftp.connect(host, port)
            ftp.login(cfg.get("user", ""), cfg.get("password", ""))
            ftp.prot_p()
        else:
            ftp = ftplib.FTP(timeout=timeout)
            ftp.connect(host, port)
            ftp.login(cfg.get("user", ""), cfg.get("password", ""))
    except ftplib.error_perm as e:
        raise RuntimeError(f"connexion FTP refusée : {e} (identifiant / mot de passe ?)") from e
    except OSError as e:
        raise RuntimeError(f"serveur FTP injoignable ({host}:{port}) : {e}") from e
    return ftp


def _ftp_cd(ftp, directory):
    """Va dans le dossier distant, en le créant si besoin."""
    d = (directory or "").strip().strip("/")
    if not d:
        return
    for part in d.split("/"):
        try:
            ftp.cwd(part)
        except ftplib.error_perm:
            ftp.mkd(part)
            ftp.cwd(part)


def upload(cfg, name: str, data: bytes, progress=None) -> str:
    """Dépose `data` sous `name` et retourne le lien public."""
    if not cfg.get("url", "").strip().lower().startswith(("http://", "https://")):
        raise RuntimeError("lien public (http/https) non renseigné (onglet Réglages)")
    ftp = _ftp_connect(cfg)
    try:
        _ftp_cd(ftp, cfg.get("dir"))
        sent = [0]

        def cb(block):
            sent[0] += len(block)
            if progress:
                progress(sent[0] / len(data))

        ftp.storbinary(f"STOR {name}", io.BytesIO(data), blocksize=8192, callback=cb)
    except ftplib.all_errors as e:
        raise RuntimeError(f"envoi FTP impossible : {e}") from e
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()
    return public_url(cfg["url"], name)


# ---------------------------------------------------------------- réception
def _check_url(url: str):
    u = urllib.parse.urlparse(url)
    if u.scheme not in ("http", "https") or not u.netloc:
        raise RuntimeError(f"lien refusé (seuls http et https sont acceptés) : {url!r}")


def download(url: str, size: int, crc: int, timeout=20) -> bytes:
    """Télécharge et vérifie (taille annoncée, CRC32). Lève RuntimeError sinon."""
    _check_url(url)
    if size <= 0 or size > MAX_DOWNLOAD:
        raise RuntimeError(f"taille annoncée invalide ({size} octets)")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = r.read(size + 1)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"téléchargement refusé : HTTP {e.code}") from e
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(f"téléchargement impossible : {getattr(e, 'reason', e)}") from e
    if len(data) != size:
        head = data[:600].lower()
        if b"<html" in head or b"<!doctype" in head or b"<head" in head:
            raise RuntimeError("le serveur renvoie une page web (erreur 404 ?) au lieu de l'image : "
                               "fichier absent à ce lien")
        raise RuntimeError(f"taille reçue {len(data)} au lieu de {size} octets")
    if zlib.crc32(data) != crc:
        raise RuntimeError("CRC32 différent : ce n'est pas l'image annoncée")
    return data


def download_retry(url, size, crc, tries=4, wait=5.0, log=None):
    last = None
    for k in range(tries):
        try:
            return download(url, size, crc)
        except RuntimeError as e:
            last = e
            if log:
                log(f"Hybride : essai {k + 1}/{tries} échoué ({e})")
            if k + 1 < tries:
                time.sleep(wait)
    raise last


def _candidates(cfg, name):
    """Liens possibles du fichier : le lien public réglé, puis ce lien + le dossier FTP
    (erreur fréquente : lien public vers la racine du site, dépôt dans un sous-dossier)."""
    base = cfg["url"].strip()
    out = [public_url(base, name)]
    d = (cfg.get("dir") or "").strip().strip("/")
    if d:
        parts = d.split("/")
        for k in range(len(parts)):              # base/dossier, base/sous/dossier, …
            sub = "/".join(parts[k:])
            if not base.rstrip("/").endswith("/" + sub):
                out.append(public_url(base.rstrip("/") + "/" + sub + "/", name))
    return list(dict.fromkeys(out))


def verify_public(cfg, name, data):
    """Vérifie que le fichier déposé est bien lisible par le lien public.
    Retourne (lien_fichier, lien_public_de_base) ; le second diffère du réglage
    quand le lien a dû être corrigé. Lève RuntimeError si introuvable."""
    errors = []
    for k in range(3):                           # quelques secondes de délai côté serveur
        for url in _candidates(cfg, name):
            try:
                download(url, len(data), zlib.crc32(data))
                return url, url[: url.rindex("/") + 1]
            except RuntimeError as e:
                errors.append(f"{url} : {e}")
        time.sleep(2)
    raise RuntimeError("le fichier est bien déposé par FTP, mais introuvable par le lien public. "
                       f"Vérifiez « Lien public » : il doit être l'adresse web du dossier "
                       f"« {cfg.get('dir') or '(racine)'} ». Essais :\n" + "\n".join(errors[-3:]))


def test_server(cfg, log=None):
    """Dépose un petit fichier, le relit par le lien public, puis l'efface.
    Retourne (lien_fichier, lien_public_correct)."""
    payload = f"HFImage test {time.time()}".encode()
    name = f"hfimage_test_{int(time.time())}.txt"
    upload(cfg, name, payload)
    try:
        return verify_public(cfg, name, payload)
    finally:
        try:
            ftp = _ftp_connect(cfg)
            _ftp_cd(ftp, cfg.get("dir"))
            ftp.delete(name)
            ftp.quit()
        except Exception:
            pass
