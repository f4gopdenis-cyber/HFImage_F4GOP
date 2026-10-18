"""Wrapper ctypes autour de hamdrm.dll : le mode image d'EasyPal et de QSSTV.

HamDRM (« DRM radioamateur ») : OFDM de 2,3 ou 2,5 kHz, modes de robustesse
A / B / E, QAM 4 / 16 / 64, fichiers transportés en segments MOT, Reed-Solomon
RS1 à RS4, demande des segments manquants (BSR) et réponse (FIX).

Ce mode sert à échanger des images avec les stations qui utilisent EasyPal ou
QSSTV. Le son est en mono, 48 000 Hz, aussi bien en émission qu'en réception
(directement la fréquence de la carte son, sans rééchantillonnage).

Le modem vient de QSSTV (Johan Maes ON4QZ), Dream (Volker Fischer) et
RXAMADRM (Ties Bos PA0MBO) ; code source dans le dossier hamdrm/ du dépôt.
"""
import ctypes
import os
import sys
import threading

import numpy as np

FS = 48000

MODES = ("A", "B", "E")
QAMS = (4, 16, 64)

# Réglages d'émission conseillés (comme les habitudes EasyPal)
DEFAULTS = {"mode": 1, "bandwidth": 1, "qam": 1, "protection": 0, "interleaver": 0, "rs": 0}


class Params(ctypes.Structure):
    _fields_ = [("mode", ctypes.c_int), ("bandwidth", ctypes.c_int), ("qam", ctypes.c_int),
                ("protection", ctypes.c_int), ("interleaver", ctypes.c_int), ("rs", ctypes.c_int),
                ("callsign", ctypes.c_char * 16)]


class Status(ctypes.Structure):
    _fields_ = [("time_sync", ctypes.c_int), ("frame_sync", ctypes.c_int),
                ("fac_valid", ctypes.c_int), ("msc_valid", ctypes.c_int),
                ("snr", ctypes.c_float), ("freq_offset", ctypes.c_float),
                ("mode", ctypes.c_int), ("bandwidth", ctypes.c_int), ("qam", ctypes.c_int),
                ("protection", ctypes.c_int), ("interleaver", ctypes.c_int),
                ("seg_received", ctypes.c_int), ("seg_total", ctypes.c_int), ("seg_current", ctypes.c_int),
                ("callsign", ctypes.c_char * 16), ("filename", ctypes.c_char * 96)]

    def as_dict(self):
        d = {name: getattr(self, name) for name, _ in self._fields_}
        d["callsign"] = self.callsign.decode("latin-1", "replace").strip()
        d["filename"] = self.filename.decode("latin-1", "replace")
        return d


def _load_lib():
    here = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.environ.get("HAMDRM_LIB", ""),
        os.path.join(here, "hamdrm.dll"),        # exécutable Windows
        os.path.join(here, "libhamdrm.so"),
    ]
    for c in candidates:
        if not c or not os.path.exists(c):
            continue
        try:
            return ctypes.CDLL(c)
        except OSError:
            pass
    return None


lib = _load_lib()
AVAILABLE = lib is not None

if AVAILABLE:
    _i16pp = ctypes.POINTER(ctypes.POINTER(ctypes.c_int16))
    _u8p = ctypes.POINTER(ctypes.c_uint8)
    _u8pp = ctypes.POINTER(_u8p)
    _pp = ctypes.POINTER(Params)
    lib.hamdrm_version.restype = ctypes.c_char_p
    lib.hamdrm_free.argtypes = [ctypes.c_void_p]
    lib.hamdrm_tx_file.argtypes = [_u8p, ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, _pp, _i16pp]
    lib.hamdrm_tx_file.restype = ctypes.c_int
    lib.hamdrm_bsr_check.argtypes = [_u8p, ctypes.c_int]
    lib.hamdrm_bsr_check.restype = ctypes.c_int
    lib.hamdrm_tx_fix.argtypes = [_u8p, ctypes.c_int, _i16pp]
    lib.hamdrm_tx_fix.restype = ctypes.c_int
    lib.hamdrm_tx_bsr.argtypes = [_pp, _i16pp]
    lib.hamdrm_tx_bsr.restype = ctypes.c_int
    lib.hamdrm_estimate.argtypes = [ctypes.c_int, _pp]
    lib.hamdrm_estimate.restype = ctypes.c_double
    lib.hamdrm_rx_reset.argtypes = []
    lib.hamdrm_rx_process.argtypes = [ctypes.POINTER(ctypes.c_int16), ctypes.c_int]
    lib.hamdrm_rx_status.argtypes = [ctypes.POINTER(Status)]
    lib.hamdrm_rx_get_file.argtypes = [_u8pp, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                                       ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_float)]
    lib.hamdrm_rx_get_file.restype = ctypes.c_int
    lib.hamdrm_rx_get_bsr.argtypes = [_u8pp]
    lib.hamdrm_rx_get_bsr.restype = ctypes.c_int
    lib.hamdrm_mode_string.argtypes = [ctypes.c_uint, ctypes.c_char_p, ctypes.c_int]


def version():
    return lib.hamdrm_version().decode() if AVAILABLE else "absent"


def make_params(callsign, mode=1, bandwidth=1, qam=1, protection=0, interleaver=0, rs=0):
    p = Params(mode, bandwidth, qam, protection, interleaver, rs)
    p.callsign = (callsign or "").upper().encode("latin-1", "replace")[:15]
    return p


def describe(p: Params):
    """Ex. « B / 2,5 kHz / QAM16 / HI / Long / RS2 »."""
    # largeurs affichées comme dans EasyPal : 2,2 / 2,4 kHz (QSSTV dit 2,3 / 2,5 ; même signal)
    s = (f"{MODES[p.mode]} / {'2,2' if p.bandwidth == 0 else '2,4'} kHz / QAM{QAMS[p.qam]} / "
         f"{'HI' if p.protection == 0 else 'LO'} / {'Long' if p.interleaver == 0 else 'Court'}")
    return s + (f" / RS{p.rs}" if p.rs else "")


def mode_string(code):
    """Code de mode reçu -> texte façon EasyPal, ex. « B/2.4/Hi/16/Long »."""
    buf = ctypes.create_string_buffer(32)
    lib.hamdrm_mode_string(code, buf, 32)
    return buf.value.decode().replace("/2.3/", "/2.2/").replace("/2.5/", "/2.4/")


def _bytes_arg(data: bytes):
    buf = (ctypes.c_uint8 * max(1, len(data))).from_buffer_copy(data or b"\0")
    return ctypes.cast(buf, ctypes.POINTER(ctypes.c_uint8)), buf


def _take_audio(n, ptr):
    if n <= 0 or not ptr:
        return None
    try:
        a = np.ctypeslib.as_array(ptr, shape=(n,)).astype(np.float32) / 32768.0
    finally:
        lib.hamdrm_free(ptr)
    return a


def _take_bytes(n, ptr):
    try:
        return ctypes.string_at(ptr, n) if n > 0 else b""
    finally:
        if ptr:
            lib.hamdrm_free(ptr)


# Le modem garde un état global (dernier fichier émis, réception en cours) :
# tous les appels passent par ce verrou.
_lock = threading.Lock()


def tx_file(data: bytes, name: str, ext: str, params: Params):
    """Signal d'émission (float32, 48 kHz, crête ~0,8) pour un fichier."""
    ptr = ctypes.POINTER(ctypes.c_int16)()
    d, keep = _bytes_arg(data)
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:60] or "image"
    with _lock:
        n = lib.hamdrm_tx_file(d, len(data), safe.encode("latin-1", "replace"), ext.encode("ascii", "replace"),
                               ctypes.byref(params), ctypes.byref(ptr))
    return _take_audio(n, ptr)


def bsr_check(bsr: bytes):
    """Nombre de segments demandés si ce BSR concerne notre dernière image, sinon -1."""
    d, keep = _bytes_arg(bsr)
    with _lock:
        return lib.hamdrm_bsr_check(d, len(bsr))


def tx_fix(bsr: bytes):
    """Signal de réponse (FIX) à un BSR : seulement les segments demandés."""
    ptr = ctypes.POINTER(ctypes.c_int16)()
    d, keep = _bytes_arg(bsr)
    with _lock:
        n = lib.hamdrm_tx_fix(d, len(bsr), ctypes.byref(ptr))
    return _take_audio(n, ptr)


def tx_bsr(params: Params):
    """Signal de demande des segments manquants de la dernière image incomplète (None si rien)."""
    ptr = ctypes.POINTER(ctypes.c_int16)()
    with _lock:
        n = lib.hamdrm_tx_bsr(ctypes.byref(params), ctypes.byref(ptr))
    return _take_audio(n, ptr)


def estimate(nbytes: int, params: Params):
    """Durée exacte d'émission en secondes."""
    with _lock:
        return lib.hamdrm_estimate(int(nbytes), ctypes.byref(params))


class Receiver:
    """Réception HamDRM en continu à partir du son de la carte (48 kHz)."""

    def reset(self):
        with _lock:
            lib.hamdrm_rx_reset()

    def process(self, x48: np.ndarray):
        """x48 : float32 de -1 à 1 (ou int16), mono, 48 kHz."""
        if x48 is None or len(x48) == 0:
            return
        if x48.dtype != np.int16:
            x48 = np.clip(np.asarray(x48, dtype=np.float32) * 32767.0, -32768, 32767).astype(np.int16)
        x48 = np.ascontiguousarray(x48)
        with _lock:
            lib.hamdrm_rx_process(x48.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)), len(x48))

    def status(self):
        st = Status()
        with _lock:
            lib.hamdrm_rx_status(ctypes.byref(st))
        return st.as_dict()

    def files(self):
        """Fichiers reçus complets : liste de dict(name, data, callsign, mode, snr)."""
        out = []
        while True:
            ptr = _u8p()
            name = ctypes.create_string_buffer(128)
            call = ctypes.create_string_buffer(16)
            code = ctypes.c_uint()
            snr = ctypes.c_float()
            with _lock:
                n = lib.hamdrm_rx_get_file(ctypes.byref(ptr), name, 128, call, 16, ctypes.byref(code),
                                           ctypes.byref(snr))
            if n <= 0:
                return out
            out.append({"name": name.value.decode("latin-1", "replace"), "data": _take_bytes(n, ptr),
                        "callsign": call.value.decode("latin-1", "replace").strip(),
                        "mode": mode_string(code.value), "snr": float(snr.value)})

    def bsrs(self):
        """BSR reçus d'autres stations (à passer à bsr_check / tx_fix)."""
        out = []
        while True:
            ptr = _u8p()
            with _lock:
                n = lib.hamdrm_rx_get_bsr(ctypes.byref(ptr))
            if n <= 0:
                return out
            out.append(_take_bytes(n, ptr))


def selftest(log=print):
    """Émission puis réception d'une petite image par le modem : True si identique."""
    if not AVAILABLE:
        log("HamDRM: hamdrm.dll absente -> ÉCHEC")
        return False
    data = bytes((i * 37 + 11) % 256 for i in range(3000))
    p = make_params("F4GOP")
    sig = tx_file(data, "selftest", "bin", p)
    rx = Receiver()
    rx.reset()
    pad = np.zeros(FS, dtype=np.float32)
    x = np.concatenate([pad, sig * 0.8, pad, pad])
    for i in range(0, len(x), 4800):
        rx.process(x[i:i + 4800])
    got = rx.files()
    ok = any(f["data"] == data for f in got)
    log(f"HamDRM (EasyPal): {describe(p)}, {len(sig) / FS:.1f} s -> {'OK' if ok else 'ÉCHEC'}")
    rx.reset()
    return ok
