"""Compatibilité EZ Pix (programme de W3WVG, SK).

EZ Pix est un système « hybride » :
  1. l'expéditeur dépose son image sous le nom « EZPix/image1 » sur son propre site ;
  2. il émet un court signal GMSK (MSK 250 bauds, 1500 Hz ± 62,5 Hz, ~5,5 s), TOUJOURS
     IDENTIQUE (le même pour toutes les stations, relevé au bit près sur deux enregistrements) ;
  3. les stations qui l'entendent lisent la liste publique des stations EZ Pix
     (https://www.qsl.net/w/w3wvg/EZPixOnAir/) et téléchargent l'image1 la plus récente.

Ce module : signal (émission), détecteur (réception), liste des stations et recherche de
l'image la plus récente. Aucune écriture sur le serveur de W3WVG.
"""
import concurrent.futures
import email.utils
import html
import re
import time
import urllib.parse
import urllib.request

import numpy as np

MODE = "EZPix"
BAUD = 250
F0 = 1500.0
DEV = BAUD / 4.0                  # MSK : écart de ±62,5 Hz
FS = 8000
SPS = FS // BAUD                  # 32 échantillons par bit

# signal relevé (domaine « différentiel » : 1 = changement de fréquence d'un bit au suivant)
_PRE = 276
_HDR = "0000100101100010100011"
_UNIT = "0100100001101001000011001001001101000100011000000101101010100110010101011"
_DIFF = "1" * _PRE + _HDR * 5 + _UNIT * 12 + _UNIT[:20] + "1" * 62

ONAIR_URL = "https://www.qsl.net/w/w3wvg/EZPixOnAir/"
IMAGE_PATH = "EZPix/image1"
USER_AGENT = "HFImage (EZ Pix compatible)"


def freq_bits(diff=_DIFF):
    """Bits « fréquence haute / basse » (+1 / -1) du signal."""
    out = np.empty(len(diff) + 1)
    v = 1.0
    out[0] = v
    for i, c in enumerate(diff):
        if c == "1":
            v = -v
        out[i + 1] = v
    return out


def _gauss_taps(bt=0.5, span=3):
    t = (np.arange(-span * SPS, span * SPS + 1) + 0.5) / SPS
    a = np.sqrt(np.log(2) / 2) / bt
    h = np.sqrt(np.pi) / a * np.exp(-(np.pi * t / a) ** 2)
    return h / h.sum()


def modulate(level=0.7):
    """Signal EZ Pix complet, 8 kHz, float -level..level (≈ 5,4 s)."""
    nrz = np.repeat(freq_bits(), SPS)
    f = np.convolve(nrz, _gauss_taps(), mode="same")          # GMSK (BT 0,5)
    ph = 2 * np.pi * np.cumsum(F0 + DEV * f) / FS
    x = np.sin(ph)
    ramp = int(0.01 * FS)                                       # pas de clic au début / à la fin
    w = np.ones(len(x))
    w[:ramp] = np.linspace(0, 1, ramp)
    w[-ramp:] = np.linspace(1, 0, ramp)
    return (level * x * w).astype(np.float32)


def modulate_int16(level=0.7):
    return (modulate(level) * 32767).astype(np.int16)


# ------------------------------------------------------------------ réception
def _lowpass(cut, n=129):
    k = np.arange(n) - (n - 1) / 2
    h = np.sinc(2 * cut / FS * k) * np.hamming(n)
    return h / h.sum()


class Detector:
    """Reconnaît le signal EZ Pix dans le son reçu (8 kHz). feed() -> score de corrélation (0..1)
    quand le signal vient d'être entendu, sinon None. Une seule détection par émission."""

    WIN_S = 4.0            # son gardé pour la recherche
    STEP_S = 0.5           # recherche toutes les 0,5 s
    THRESH = 0.55          # corrélation normalisée minimale
    HOLD_S = 8.0           # une seule détection par émission

    DEC = 8                # discriminateur ramené à 1 kHz (4 points par bit) : peu de calcul

    def __init__(self):
        self._lp = _lowpass(220)
        spb = SPS // self.DEC
        tpl = np.repeat(freq_bits()[_PRE:_PRE + 22 * 5 + 73 * 2], spb)     # en-tête + 2 blocs (~1 s)
        tpl = np.convolve(tpl, np.ones(2) / 2, mode="same")
        self._rest = np.zeros(0)
        self.tpl = (tpl - tpl.mean()) / np.linalg.norm(tpl - tpl.mean())
        self.buf = np.zeros(0)
        self.n = 0                 # échantillons reçus
        self._pending = 0
        self._ph = 0.0
        self._prev = 0j
        self._zi = np.zeros(len(self._lp) - 1, complex)
        self._last = -1e9
        self.last_score = 0.0

    def _disc(self, x):
        """Discriminateur FM autour de 1500 Hz -> écart normalisé (±1 = ±62,5 Hz)."""
        n = np.arange(len(x))
        lo = np.exp(-2j * np.pi * F0 * n / FS + 1j * self._ph)
        self._ph = (self._ph - 2 * np.pi * F0 * len(x) / FS) % (2 * np.pi)
        z = np.convolve(np.concatenate([self._zi, x * lo]), self._lp, mode="valid")
        self._zi = np.concatenate([self._zi, x * lo])[-(len(self._lp) - 1):]
        zz = np.concatenate([[self._prev], z])
        self._prev = z[-1] if len(z) else self._prev
        f = np.angle(zz[1:] * np.conj(zz[:-1])) * FS / (2 * np.pi)
        return np.clip(f / DEV, -3, 3), z

    def feed(self, x8k):
        x = np.asarray(x8k, dtype=np.float64)
        if x.size == 0:
            return None
        if np.abs(x).max() > 2.0:              # int16 -> -1..1
            x = x / 32768.0
        f, _z = self._disc(x)
        f = np.concatenate([self._rest, f])
        cut = len(f) - len(f) % self.DEC
        self._rest = f[cut:]
        f = f[:cut].reshape(-1, self.DEC).mean(axis=1)
        keep = int(self.WIN_S * FS / self.DEC)
        self.buf = np.concatenate([self.buf, f])[-keep:]
        self.n += len(x)
        self._pending += len(x)
        if self._pending < self.STEP_S * FS or len(self.buf) < len(self.tpl) + 8:
            return None
        self._pending = 0
        if (self.n - self._last) < self.HOLD_S * FS:
            return None
        b = self.buf - self.buf.mean()
        m = len(self.tpl)
        # corrélation glissante normalisée (FFT)
        L = 1 << int(np.ceil(np.log2(len(b) + m)))
        c = np.fft.irfft(np.fft.rfft(b, L) * np.conj(np.fft.rfft(self.tpl, L)), L)[:len(b) - m + 1]
        cs = np.concatenate([[0.0], np.cumsum(b * b)])
        e = np.sqrt(np.maximum(cs[m:] - cs[:-m], 1e-12))
        r = np.abs(c) / e
        k = int(np.argmax(r))
        self.last_score = float(r[k])
        if r[k] < self.THRESH:
            return None
        self._last = self.n
        return round(self.last_score, 2)


# ------------------------------------------------------------------ liste des stations
_TOK = {"--1": ".", "--2": ",", "--3": ":", "--4": "/", "--5": " ", "%09": "", "\t": ""}


def _untok(s):
    for k, v in _TOK.items():
        s = s.replace(k, v)
    return s


def parse_onair_name(fname):
    """« F1JMJ_3--1733_Joel_http--3--4--4www--1qsl--1net--4f1jmj_.txt » ->
    {call, freq, name, url} (url = adresse du site, se termine par « / »), ou None."""
    n = urllib.parse.unquote(fname)
    if not n.lower().endswith(".txt"):
        return None
    n = n[:-4].rstrip("_")
    parts = n.split("_")
    if len(parts) < 4:
        return None
    call = parts[0].strip().upper()
    freq = _untok(parts[1]).strip()
    url = _untok("_".join(parts[3:])).strip().replace("!", ".")
    name = _untok(parts[2]).strip()
    if not re.match(r"^[A-Z0-9/]{3,12}$", call):
        return None
    if not re.match(r"^https?://", url, re.I):
        url = "http://" + url.lstrip("/")
    u = urllib.parse.urlparse(url)
    if u.scheme not in ("http", "https") or not u.netloc:
        return None
    if not url.endswith("/"):
        url += "/"
    return {"call": call, "freq": freq, "name": name, "url": url}


def parse_onair_listing(page):
    """Page « Index of /w/w3wvg/EZPixOnAir » -> liste de stations (une par indicatif)."""
    out = {}
    for href in re.findall(r'href="([^"?/][^"]*)"', page, re.I):
        st = parse_onair_name(html.unescape(href))
        if st:
            out[st["call"]] = st
    return list(out.values())


def _open(url, method="GET", timeout=8):
    import hybrid
    import netssl
    hybrid._check_url(url)
    hybrid._check_public_url(url)           # jamais une machine du réseau local
    req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=netssl.context()),
                                         hybrid._PublicRedirect())
    return opener.open(req, timeout=timeout)


def fetch_onair(timeout=10):
    with _open(ONAIR_URL, timeout=timeout) as r:
        page = r.read(2_000_000).decode("utf-8", "replace")
    return parse_onair_listing(page)


def image_url(station):
    return station["url"] + IMAGE_PATH


def _age(station, timeout=6):
    """(âge de l'image1 en s d'après l'horloge du serveur, taille) ou None."""
    try:
        with _open(image_url(station), "HEAD", timeout) as r:
            lm = r.headers.get("Last-Modified")
            dt = r.headers.get("Date")
            size = int(r.headers.get("Content-Length") or 0)
        if not lm:
            return None
        t_mod = email.utils.parsedate_to_datetime(lm).timestamp()
        t_now = email.utils.parsedate_to_datetime(dt).timestamp() if dt else time.time()
        return t_now - t_mod, size
    except Exception:
        return None


def find_latest(stations, max_age=600, workers=12):
    """Station dont l'image1 est la plus récente (moins de max_age s ; EZ Pix peut déposer l'image
    un peu avant l'émission) : (station, âge, taille) ou None."""
    best = None
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for st, res in zip(stations, ex.map(_age, stations)):
            if res is None:
                continue
            age, size = res
            if -60 <= age <= max_age and (best is None or age < best[1]):
                best = (st, age, size)
    return best


def download(station, max_bytes, timeout=30):
    with _open(image_url(station), timeout=timeout) as r:
        data = r.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise RuntimeError(f"image trop grande (plus de {max_bytes} octets)")
    head = data[:600].lower()
    if b"<html" in head or b"<!doctype" in head:
        raise RuntimeError("le site renvoie une page web au lieu de l'image")
    return data
