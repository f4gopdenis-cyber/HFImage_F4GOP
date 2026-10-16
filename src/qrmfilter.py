"""Coupe-QRM de réception (devant chaque démodulateur).

Un signal OFDM a un spectre plat dans sa bande. Le filtre, mode par mode :
1. efface tout ce qui est hors de la bande du mode (BLU voisine, signaux forts à côté) ;
2. dans la bande, efface les raies qui dépassent le niveau médian du signal de plus de
   10 dB (porteuses, CW, RTTY, « birdies »). Les porteuses OFDM touchées deviennent des
   effacements que le code LDPC sait corriger, au lieu de fausser toute la démodulation.

Mesures au simulateur (SNR 12 dB) : une simple porteuse aussi forte que le signal, ou une
BLU 20 dB plus forte juste à côté de la bande, faisait perdre 100 % des trames ; avec le
filtre, 80 à 100 % passent. Sans QRM, le filtre ne change presque rien.

Traitement par blocs de 0,5 s avec 0,25 s de contexte de chaque côté (retard ~0,75 s).
"""
import numpy as np

NC = {"DATAC1X": 35, "DATAC1": 27, "DATAC3": 9, "DATAC4": 4, "DATAC0": 9}
RS = 62.5           # espacement des porteuses (Hz) des modes datac
CENTRE = 1500.0
N, HOP = 512, 128
THR_DB = 10.0
SMOOTH = 5          # trames (~80 ms) pour lisser la puissance par raie
_W = np.hanning(N)
_NORM = np.sum(_W ** 2) / HOP


def band(mode, margin=80.0):
    h = (NC.get(mode, 35) + 1) * RS / 2
    return CENTRE - h - margin, CENTRE + h + margin


def _box(a, size, axis):
    """Moyenne glissante centrée (comme scipy.ndimage.uniform_filter1d, bords répétés)."""
    pad = [(0, 0)] * a.ndim
    pad[axis] = (size // 2, size - 1 - size // 2)
    ap = np.pad(a, pad, mode="edge")
    c = np.cumsum(ap, axis=axis)
    c = np.concatenate([np.zeros_like(np.take(c, [0], axis=axis)), c], axis=axis)
    n = a.shape[axis]
    return (np.take(c, np.arange(size, size + n), axis=axis) - np.take(c, np.arange(0, n), axis=axis)) / size


def _dilate(b, rt, rf):
    """Étend le masque de ±rt trames et ±rf raies."""
    out = b.copy()
    for d in range(1, rt + 1):
        out[d:] |= b[:-d]
        out[:-d] |= b[d:]
    b2 = out.copy()
    for d in range(1, rf + 1):
        out[:, d:] |= b2[:, :-d]
        out[:, :-d] |= b2[:, d:]
    return out


def clean(x, mode, fs=8000, thr_db=THR_DB):
    """Filtre un bloc complet (float) -> float de même longueur."""
    x = np.asarray(x, dtype=np.float64)
    pad = np.concatenate([np.zeros(N), x, np.zeros(N)])
    frames = np.lib.stride_tricks.sliding_window_view(pad, N)[::HOP] * _W
    S = np.fft.rfft(frames, axis=1)
    f = np.fft.rfftfreq(N, 1 / fs)
    lo, hi = band(mode)
    inb = (f >= lo) & (f <= hi)
    S[:, ~inb] = 0
    sub = S[:, inb]
    P = sub.real ** 2 + sub.imag ** 2
    Pt = _box(P, SMOOTH, 0)
    base = np.median(Pt, axis=1, keepdims=True)
    bad = Pt > base * 10 ** (thr_db / 10)
    if bad.any():
        bad = _dilate(bad, 2, 2)
        sub[bad] = 0
        S[:, inb] = sub
    y = np.fft.irfft(S, N, axis=1) * _W
    out = np.zeros(len(pad) + N)
    for i, fr in enumerate(y):
        out[i * HOP:i * HOP + N] += fr
    return out[N:N + len(x)] / _NORM


class QrmFilter:
    """Version en flux de clean() : on donne des morceaux, on récupère des morceaux
    (avec un retard fixe)."""
    BLOCK, CTX = 4000, 2048

    def __init__(self, mode):
        self.mode = mode
        self.buf = np.zeros(self.CTX)

    def process(self, x):
        self.buf = np.concatenate([self.buf, np.asarray(x, dtype=np.float64)])
        out = []
        need = self.CTX + self.BLOCK + self.CTX
        while len(self.buf) >= need:
            y = clean(self.buf[:need], self.mode)
            out.append(y[self.CTX:self.CTX + self.BLOCK])
            self.buf = self.buf[self.BLOCK:]
        if not out:
            return np.zeros(0, np.int16)
        return np.clip(np.concatenate(out), -32767, 32767).astype(np.int16)
