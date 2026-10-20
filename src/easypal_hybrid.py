"""Mode hybride façon EasyPal / QSSTV (en mode EasyPal).

L'émetteur dépose l'image par FTP dans <dossier>/HybridFiles1/de_INDICATIF-n-nom.ext,
puis émet en HamDRM un petit fichier du même nom qui contient, brouillés,
le serveur, l'identifiant, le mot de passe et le dossier FTP. Les stations qui le
reçoivent téléchargent l'image sur ce serveur.

Le brouillage est celui d'EasyPal, repris de QSSTV (hybridcrypt.cpp, GPL v3,
Johan Maes ON4QZ). Ce n'est PAS un chiffrement : n'importe quelle station qui
reçoit l'annonce peut relire l'identifiant et le mot de passe. Il faut donc un
compte FTP dédié, limité à un seul dossier.
"""
import ftplib
import io
import time

import hybrid

FILES_DIR = "HybridFiles1"          # dossier commun d'EasyPal / QSSTV
_K1, _K2, _K3, _K4 = 4, 5, 7, 1    # clés d'EasyPal


def is_announce(name: str) -> bool:
    """Nom d'une annonce hybride EasyPal / QSSTV (« de_F4GOP-3-photo.jpg »)."""
    return bool(name) and (name.startswith("de_") or name.startswith(".de"))


def file_name(callsign: str, n: int, base: str, ext: str) -> str:
    """Nom du fichier déposé et annoncé, comme EasyPal : de_INDICATIF-n-nom.ext."""
    call = "".join(c for c in callsign.upper() if c.isalnum() or c == "/").replace("/", "-") or "NOCALL"
    base = "".join(c if c.isalnum() or c in "-_" else "_" for c in base)[:30] or "image"
    return f"de_{call}-{n}-{base}.{ext}"


def _s16(v):
    """Arithmétique 16 bits signée, comme le « short int » du code d'origine."""
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def encrypt(host: str, login: str, password: str, directory: str) -> bytes:
    """Contenu de l'annonce : accès FTP brouillé à la manière d'EasyPal.
    Seuls les caractères ASCII passent (EasyPal / QSSTV codent mal les accents)."""
    plain = "?" + host + '"' + login + "<" + password + ">" + directory + ":"
    if any(ord(c) > 126 or ord(c) < 32 for c in plain):
        raise ValueError("serveur, identifiant, mot de passe et dossier FTP ne doivent contenir ni accents "
                         "ni caractères spéciaux en mode hybride EasyPal")
    hexs = "".join(f"{ord(c) & 0xFF:02x}" for c in reversed(plain))
    codes = [ord(c) for c in hexs]
    while len(codes) % 4:
        codes.append(0)
    out = bytearray()
    for i in range(0, len(codes), 4):
        n1, n2, n3, n4 = codes[i:i + 4]
        res = (_s16(n1 * _K1 + n2 * _K3), _s16(n1 * _K2 + n2 * _K4),
               _s16(n3 * _K1 + n4 * _K3), _s16(n3 * _K2 + n4 * _K4))
        for r in res:
            r1, r2 = (r >> 8) & 0xFF, r & 0xFF
            if r1 == 0 and r2 == 0:
                r1 = r2 = 0xFF
            if r1 == 0xFF:
                r1 = 0xFE
            if r2 == 0:
                r1, r2 = 0xFD, r1
            out += bytes((r1, r2))
    return bytes(out) + b"\r\n"


def decrypt(blob: bytes):
    """-> dict(host, user, password, dir) ou None si ce n'est pas une annonce valable."""
    size = len(blob)
    if size != 3:
        size -= 2                              # \r\n final
        if size % 2:
            return None
    if size < 20:
        return None
    divzr = _K1 * _K4 - _K3 * _K2
    chars = []
    i = 0
    try:
        while i < size:
            res = []
            for _ in range(4):
                r1, r2 = blob[i], blob[i + 1]
                i += 2
                if r1 == 0xFF:
                    r1 = r2 = 0
                if r1 == 0xFE:
                    r1 = 0
                if r1 == 0xFD:
                    r1, r2 = r2, 0
                res.append(_s16(r1 * 256 + r2))
            r_1, r_2, r_3, r_4 = res
            nums = (int((r_1 * _K4 - r_2 * _K3) / divzr), int((r_2 * _K1 - r_1 * _K2) / divzr),
                    int((r_3 * _K4 - r_4 * _K3) / divzr), int((r_4 * _K1 - r_3 * _K2) / divzr))
            for a, b in ((nums[0], nums[1]), (nums[2], nums[3])):
                try:
                    chars.append(chr(int(chr(a) + chr(b), 16)))
                except ValueError:
                    chars.append("\0")         # remplissage
    except IndexError:
        return None
    s = "".join(reversed(chars))
    a = s.find("?")
    b = s.find('"', a + 1)
    c = s.find("<", b + 1)
    d = s.find(">", c + 1)
    e = s.find(":", d + 1)
    if min(a, b, c, d, e) < 0:
        return None
    host = s[a + 1:b].strip()
    if not host or any(ord(ch) < 32 for ch in host):
        return None
    return {"host": host, "user": s[b + 1:c], "password": s[c + 1:d], "dir": s[d + 1:e]}


def _files_path(directory: str) -> str:
    d = (directory or "").rstrip("/")
    return f"{d}/{FILES_DIR}" if d else FILES_DIR


def upload(cfg, name: str, data: bytes, progress=None):
    """Dépose l'image dans <dossier>/HybridFiles1 du serveur FTP de l'onglet Réglages."""
    ftp = hybrid._ftp_connect(cfg)
    try:
        hybrid._ftp_cd(ftp, _files_path(cfg.get("dir")))
        sent = [0]

        def cb(block):
            sent[0] += len(block)
            if progress:
                progress(sent[0] / max(1, len(data)))

        ftp.storbinary(f"STOR {name}", io.BytesIO(data), blocksize=8192, callback=cb)
    except ftplib.all_errors as e:
        raise RuntimeError(f"envoi FTP impossible : {e}") from e
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()


class _TooBig(Exception):
    pass


def _download_once(acc, name, tls, timeout, ip=None):
    ftp = ftplib.FTP_TLS(timeout=timeout) if tls else ftplib.FTP(timeout=timeout)
    try:
        # ip : adresse déjà vérifiée (publique) ; on s'y connecte directement pour que le
        # nom du serveur ne puisse pas désigner une autre machine entre-temps
        ftp.connect(ip or acc["host"], 21)
        ftp.login(acc["user"], acc["password"])
        if tls:
            ftp.prot_p()
        path = _files_path(acc["dir"])
        try:
            ftp.cwd(path)
        except ftplib.error_perm:
            for part in path.strip("/").split("/"):
                ftp.cwd(part)
        try:
            announced = ftp.size(name)
        except (ftplib.all_errors + (ValueError,)):
            announced = None
        if announced is not None and announced > hybrid.MAX_DOWNLOAD:
            raise _TooBig(announced)
        buf = io.BytesIO()

        def keep(block):
            if buf.tell() + len(block) > hybrid.MAX_DOWNLOAD:
                raise _TooBig(buf.tell() + len(block))
            buf.write(block)

        ftp.retrbinary(f"RETR {name}", keep)
        return buf.getvalue()
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()


def download(acc, name: str, tries=4, wait=5.0, timeout=20, log=None) -> bytes:
    """Télécharge l'image annoncée (FTP simple comme EasyPal, puis FTP sécurisé).

    Le serveur vient de l'annonce radio : adresses locales / privées refusées, et
    fichier limité à 8 Mo comme l'hybride HFImage."""
    ip = hybrid.public_address(acc.get("host"), 21)
    last = None
    for k in range(tries):
        for tls in (False, True):
            try:
                data = _download_once(acc, name, tls, timeout, ip)
                if data:
                    return data
            except _TooBig as e:
                raise hybrid.Refused(f"fichier {name} refusé : trop gros ({e.args[0]} octets, "
                                     f"maximum {hybrid.MAX_DOWNLOAD // (1024 * 1024)} Mo, voir Réglages)") from None
            except ftplib.all_errors as e:
                last = e
        if k + 1 < tries:
            if log:
                log(f"Hybride EasyPal : {name} pas encore disponible ({last}), nouvel essai dans {wait:.0f} s")
            time.sleep(wait)
    raise RuntimeError(f"téléchargement de {name} impossible sur {acc['host']} : {last}")


def public_label(acc, name: str) -> str:
    """Emplacement affiché dans le journal (sans le mot de passe)."""
    return f"ftp://{acc['host']}/{_files_path(acc['dir']).lstrip('/')}/{name}"
