"""Wrapper ctypes autour des modes data OFDM de codec2 (DATAC0/1/3/4).

Le modem transporte des trames de taille fixe. Les 2 derniers octets de
chaque trame sont un CRC16 (calculé ici), le reste est la charge utile
fournie par la couche protocole.
"""
import ctypes
import time
import ctypes.util
import os
import numpy as np

MODES = {"DATAC0": 14, "DATAC1": 10, "DATAC3": 12, "DATAC4": 18}
# modes ajoutés à libcodec2 par HFImage (hfi_modes.c, FREEDV_MODE_DATA_CUSTOM)
CUSTOM = {"DATAC1X": b"datac1x"}
# trames par rafale : doit être identique à l'émission et à la réception
# Une trame par rafale : chaque trame a son préambule et se resynchronise seule
# (robuste aux micro-coupures de carte son et aux évanouissements ; ~4 % de durée)
MODE_FPB = {"DATAC0": 1, "DATAC1": 1, "DATAC3": 1, "DATAC4": 1, "DATAC1X": 1}
# débit utile approximatif (bit/s), pour l'affichage
MODE_BPS = {"DATAC0": 290, "DATAC1": 980, "DATAC3": 320, "DATAC4": 85, "DATAC1X": 1520}
# largeur de bande occupée (kHz), pour l'affichage
MODE_BW = {"DATAC0": 0.6, "DATAC1": 1.7, "DATAC3": 0.6, "DATAC4": 0.25, "DATAC1X": 2.2}


# Étalonnage du SNR : l'estimation de codec2 est comprimée (12 dB réels -> ~8,5 dB
# estimés en DATAC1X, ~6 dB en DATAC3) et sature vers le haut. Mesuré au simulateur
# (canaux sans évanouissement, CCIR bon et moyen, moyenne) : (SNR réel, SNR estimé).
# On affiche et on échange le SNR réel sur 3 kHz, comparable d'un mode à l'autre.
# (Près du seuil de décodage, seules les trames réussies sont mesurées : estimation trop
# optimiste ; les premiers points sont donc pris avec une pente proche de 1.)
SNR_CAL = {
    "DATAC1X": [(6, 4.99), (9, 6.78), (12, 8.76), (15, 10.33), (18, 11.48), (21, 12.24), (24, 12.54)],
    "DATAC1": [(3, 2.80), (6, 4.32), (9, 6.42), (12, 8.26), (15, 9.70), (18, 10.63), (21, 11.14), (24, 11.42)],
    "DATAC3": [(-4, -3.00), (0, -0.49), (3, 1.28), (6, 3.28), (9, 4.64), (12, 6.02), (15, 6.97),
               (18, 7.46), (21, 7.72), (24, 7.79)],
    "DATAC4": [(-6, -5.35), (-3, -3.57), (0, -0.69), (3, 2.35), (6, 5.34), (9, 7.99), (12, 10.25),
               (15, 12.43), (18, 13.77), (21, 14.77), (24, 15.54)],
    "DATAC0": [(-3, -2.48), (0, -0.85), (3, 1.10), (6, 3.00), (9, 4.69), (12, 6.39), (15, 7.44), (18, 8.06),
               (21, 8.20), (24, 8.48)],
}
SNR_MAX = 25.0
# au-delà, l'estimation du mode sature (une petite variation donnerait des écarts énormes) :
# on plafonne au dernier point fiable (affiché « +15 dB » = 15 dB ou plus)
SNR_CAP = {"DATAC1X": 21.0, "DATAC1": 21.0, "DATAC3": 15.0, "DATAC4": 21.0, "DATAC0": 15.0}


def true_snr(mode, est):
    """SNR estimé par codec2 -> SNR réel (dB sur 3 kHz) d'après l'étalonnage du mode."""
    pts = SNR_CAL.get(mode)
    if not pts or est is None:
        return est
    est = float(est)
    t = np.array([p[0] for p in pts], float)
    e = np.maximum.accumulate(np.array([p[1] for p in pts], float))
    e = e + np.arange(len(e)) * 1e-3                      # strictement croissant
    if est <= e[0]:
        return float(t[0] - (e[0] - est))                 # en dessous : pente 1
    cap = SNR_CAP.get(mode, SNR_MAX)
    if est >= e[-1]:
        return cap
    return float(min(cap, np.interp(est, e, t)))


def _load_lib():
    import sys
    here = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.environ.get("CODEC2_LIB", ""),
        os.path.join(here, "libcodec2.dll"),       # exécutable Windows
        os.path.join(here, "libcodec2.so"),
        os.path.expanduser("~/src/codec2/build/src/libcodec2.so"),
        ctypes.util.find_library("codec2") or "",
    ]
    for c in candidates:
        if not c or (c.startswith("/") and not os.path.exists(c)):
            continue
        try:
            return ctypes.CDLL(c)
        except OSError:
            pass
    raise OSError("libcodec2 introuvable (définir CODEC2_LIB)")


lib = _load_lib()
_vp, _i, _sp, _bp = ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.POINTER(ctypes.c_ubyte)
lib.freedv_open.restype = _vp
lib.freedv_open.argtypes = [_i]
for name in ("freedv_close",):
    getattr(lib, name).argtypes = [_vp]
for name in ("freedv_get_bits_per_modem_frame", "freedv_get_n_tx_modem_samples",
             "freedv_get_n_max_modem_samples", "freedv_get_modem_sample_rate",
             "freedv_nin", "freedv_get_sync",
             "freedv_get_n_tx_preamble_modem_samples",
             "freedv_get_n_tx_postamble_modem_samples"):
    getattr(lib, name).argtypes = [_vp]
    getattr(lib, name).restype = _i
lib.freedv_rawdatatx.argtypes = [_vp, _sp, _bp]
lib.freedv_rawdatapreambletx.argtypes = [_vp, _sp]
lib.freedv_rawdatapreambletx.restype = _i
lib.freedv_rawdatapostambletx.argtypes = [_vp, _sp]
lib.freedv_rawdatapostambletx.restype = _i
lib.freedv_rawdatarx.argtypes = [_vp, _bp, _sp]
lib.freedv_rawdatarx.restype = _i
lib.freedv_gen_crc16.argtypes = [_bp, _i]
lib.freedv_gen_crc16.restype = ctypes.c_ushort
lib.freedv_set_frames_per_burst.argtypes = [_vp, _i]
if hasattr(lib, "hfi_open"):
    lib.hfi_open.restype = _vp
    lib.hfi_open.argtypes = [ctypes.c_char_p]
lib.freedv_get_modem_stats.argtypes = [_vp, ctypes.POINTER(_i), ctypes.POINTER(ctypes.c_float)]


def crc16(data: bytes) -> int:
    buf = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    return lib.freedv_gen_crc16(buf, len(data))


class Modem:
    def __init__(self, mode="DATAC1", frames_per_burst=1):
        self.mode = mode
        self.fpb = frames_per_burst
        if mode in CUSTOM:
            if not hasattr(lib, "hfi_open"):
                raise RuntimeError(f"{mode} : libcodec2 trop ancienne (hfi_open absent)")
            self.f = lib.hfi_open(CUSTOM[mode])
        else:
            self.f = lib.freedv_open(MODES[mode])
        if not self.f:
            raise RuntimeError(f"freedv_open({mode}) a échoué")
        lib.freedv_set_frames_per_burst(self.f, frames_per_burst)
        self.fs = lib.freedv_get_modem_sample_rate(self.f)
        self.frame_bytes = lib.freedv_get_bits_per_modem_frame(self.f) // 8
        self.payload_bytes = self.frame_bytes - 2
        self.n_tx = lib.freedv_get_n_tx_modem_samples(self.f)
        self.n_max = lib.freedv_get_n_max_modem_samples(self.f)
        self._rxbuf = np.zeros(0, dtype=np.int16)
        self.sync = 0           # 1 = démodulateur synchronisé
        self.crc_fail = 0       # trames démodulées mais fausses
        self.ok = 0             # trames justes
        self.last_ok = 0.0      # heure de la dernière trame juste
        self.last_fail = 0.0

    def close(self):
        if self.f:
            lib.freedv_close(self.f)
            self.f = None

    # ---------- émission ----------
    def _frame_samples(self, payload: bytes) -> np.ndarray:
        assert len(payload) <= self.payload_bytes
        payload = payload.ljust(self.payload_bytes, b"\0")
        c = crc16(payload)
        frame = payload + bytes([c >> 8, c & 0xFF])
        out = (ctypes.c_short * self.n_tx)()
        lib.freedv_rawdatatx(self.f, out, (ctypes.c_ubyte * len(frame)).from_buffer_copy(frame))
        return np.frombuffer(out, dtype=np.int16).copy()

    def _amble(self, fn) -> np.ndarray:
        out = (ctypes.c_short * self.n_max)()
        n = fn(self.f, out)
        return np.frombuffer(out, dtype=np.int16)[:n].copy()

    LEAD_S, GAP_S, TAIL_S = 0.2, 0.1, 0.5

    def duration_s(self, bursts):
        """Durée exacte d'une émission de `bursts` rafales pleines."""
        pre = lib.freedv_get_n_tx_preamble_modem_samples(self.f)
        post = lib.freedv_get_n_tx_postamble_modem_samples(self.f)
        per = pre + self.fpb * self.n_tx + post + int(self.fs * self.GAP_S)
        return (int(self.fs * self.LEAD_S) + bursts * per + int(self.fs * self.TAIL_S)) / self.fs

    def modulate_iter(self, payloads, gap_s=None):
        """Comme modulate(), mais rafale par rafale (générateur de tableaux int16)."""
        gap_s = self.GAP_S if gap_s is None else gap_s
        yield np.zeros(int(self.fs * self.LEAD_S), np.int16)
        for i in range(0, len(payloads), self.fpb):
            burst = payloads[i:i + self.fpb]
            parts = [self._amble(lib.freedv_rawdatapreambletx)]
            parts += [self._frame_samples(p) for p in burst]
            parts += [self._frame_samples(b"") for _ in range(self.fpb - len(burst))]
            parts.append(self._amble(lib.freedv_rawdatapostambletx))
            parts.append(np.zeros(int(self.fs * gap_s), np.int16))
            yield np.concatenate(parts)
        yield np.zeros(int(self.fs * self.TAIL_S), np.int16)

    def modulate(self, payloads, gap_s=None):
        """Liste de charges utiles -> échantillons audio int16.
        Les trames sont groupées en rafales de `frames_per_burst`, chacune
        précédée d'un préambule et suivie d'un postambule."""
        gap_s = self.GAP_S if gap_s is None else gap_s
        chunks = [np.zeros(int(self.fs * self.LEAD_S), np.int16)]
        for i in range(0, len(payloads), self.fpb):
            burst = payloads[i:i + self.fpb]
            chunks.append(self._amble(lib.freedv_rawdatapreambletx))
            chunks += [self._frame_samples(p) for p in burst]
            # rafale incomplète : on bourre pour que le récepteur reste cohérent
            chunks += [self._frame_samples(b"") for _ in range(self.fpb - len(burst))]
            chunks.append(self._amble(lib.freedv_rawdatapostambletx))
            chunks.append(np.zeros(int(self.fs * gap_s), np.int16))
        chunks.append(np.zeros(int(self.fs * self.TAIL_S), np.int16))
        return np.concatenate(chunks)

    # ---------- réception ----------
    def demodulate(self, samples: np.ndarray):
        """Échantillons int16 -> générateur de (charge utile, snr).
        Utilisable en flux : les échantillons restants sont gardés."""
        buf = np.concatenate([self._rxbuf, samples.astype(np.int16)])
        pos = 0
        out = (ctypes.c_ubyte * self.frame_bytes)()
        sync, snr = ctypes.c_int(), ctypes.c_float()
        while True:
            nin = lib.freedv_nin(self.f)
            if pos + nin > len(buf):
                break
            chunk = np.ascontiguousarray(buf[pos:pos + nin])
            n = lib.freedv_rawdatarx(self.f, out, chunk.ctypes.data_as(_sp))
            pos += nin
            self.sync = lib.freedv_get_sync(self.f)
            if n:
                frame = bytes(out)[:n]
                payload, rx_crc = frame[:-2], (frame[-2] << 8) | frame[-1]
                if crc16(payload) == rx_crc:
                    lib.freedv_get_modem_stats(self.f, ctypes.byref(sync), ctypes.byref(snr))
                    self.ok += 1
                    self.last_ok = time.time()
                    yield payload, true_snr(self.mode, snr.value)
                else:
                    self.crc_fail += 1
                    self.last_fail = time.time()
        self._rxbuf = buf[pos:]
