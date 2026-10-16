"""Code fontaine systématique sur GF(256), en numpy pur (pas de dépendance compilée).

- Symboles 0..K-1 : les données d'origine (systématique : sans pertes, aucun calcul).
- Symboles >= K   : combinaisons linéaires aléatoires de tous les symboles sources,
  coefficients tirés d'un générateur LCG initialisé par le numéro de symbole
  (ESI) -> l'émetteur et le récepteur calculent les mêmes coefficients sans
  les transmettre, et l'algorithme est trivial à porter en C.
- Décodage : élimination de Gauss incrémentale. Avec K symboles reçus quelconques,
  la probabilité d'échec est ~1/256 ; avec K+2 elle est ~1/16 millions.

Paquet : SBN (1 octet, toujours 0) + ESI (3 octets) + symbole (T octets),
même format que RaptorQ pour ne rien changer au protocole.
"""
import numpy as np

# Tables GF(256), polynôme 0x11D
EXP = np.zeros(512, dtype=np.uint8)
LOG = np.zeros(256, dtype=np.int32)
_x = 1
for _i in range(255):
    EXP[_i] = _x
    LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
EXP[255:510] = EXP[:255]


def gf_mul_scalar(vec: np.ndarray, c: int) -> np.ndarray:
    """vec (uint8) * c dans GF(256)."""
    if c == 0:
        return np.zeros_like(vec)
    if c == 1:
        return vec.copy()
    out = EXP[LOG[vec] + LOG[c]]
    out[vec == 0] = 0
    return out


def gf_inv(c: int) -> int:
    return int(EXP[255 - LOG[c]])


def coefficients(esi: int, K: int) -> np.ndarray:
    """Coefficients du symbole `esi` (vecteur de K octets)."""
    if esi < K:
        v = np.zeros(K, dtype=np.uint8)
        v[esi] = 1
        return v
    # graine : mélange "splitmix32" de l'ESI (non linéaire grâce aux multiplications)
    s = (esi + 0x9E3779B9) & 0xFFFFFFFF
    s = ((s ^ (s >> 16)) * 0x85EBCA6B) & 0xFFFFFFFF
    s = ((s ^ (s >> 13)) * 0xC2B2AE35) & 0xFFFFFFFF
    s ^= s >> 16
    v = np.empty(K, dtype=np.uint8)
    for i in range(K):
        # LCG (Numerical Recipes) : on garde l'octet de poids fort, le meilleur
        s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
        v[i] = s >> 24
    if not v.any():
        v[0] = 1
    return v


def _combine(coef: np.ndarray, src: np.ndarray) -> np.ndarray:
    """somme_i coef[i] * src[i] dans GF(256). src : (K, T)."""
    acc = np.zeros(src.shape[1], dtype=np.uint8)
    nz = np.nonzero(coef)[0]
    for i in nz:
        acc ^= gf_mul_scalar(src[i], int(coef[i]))
    return acc


class Encoder:
    def __init__(self, data: bytes, T: int):
        self.T = T
        self.K = max(1, -(-len(data) // T))
        buf = np.zeros(self.K * T, dtype=np.uint8)
        buf[:len(data)] = np.frombuffer(data, dtype=np.uint8)
        self.src = buf.reshape(self.K, T)

    def packet(self, esi: int) -> bytes:
        if esi < self.K:
            sym = self.src[esi]
        else:
            sym = _combine(coefficients(esi, self.K), self.src)
        return b"\x00" + esi.to_bytes(3, "big") + sym.tobytes()

    def packets(self, start: int, n: int):
        return [self.packet(e) for e in range(start, start + n)]


class Decoder:
    """Élimination de Gauss en ligne : chaque paquet est réduit dès son arrivée."""

    def __init__(self, size: int, T: int):
        self.size, self.T = size, T
        self.K = max(1, -(-size // T))
        self.rows = {}        # pivot -> (coef normalisé, symbole)
        self.seen = set()
        self.result = None

    @property
    def rank(self):
        return len(self.rows)

    def add(self, pkt: bytes):
        """Ajoute un paquet ; retourne les données dès qu'elles sont complètes."""
        if self.result is not None:
            return self.result
        esi = int.from_bytes(pkt[1:4], "big")
        if esi in self.seen or len(pkt) < 4 + self.T:
            return None
        self.seen.add(esi)
        c = coefficients(esi, self.K).copy()
        s = np.frombuffer(pkt[4:4 + self.T], dtype=np.uint8).copy()
        for p in sorted(self.rows):                 # réduction par les pivots connus
            if c[p]:
                rc, rs = self.rows[p]
                f = int(c[p])
                c ^= gf_mul_scalar(rc, f)
                s ^= gf_mul_scalar(rs, f)
        nz = np.nonzero(c)[0]
        if len(nz) == 0:
            return None                             # paquet redondant
        p = int(nz[0])
        inv = gf_inv(int(c[p]))
        c, s = gf_mul_scalar(c, inv), gf_mul_scalar(s, inv)
        for q, (rc, rs) in self.rows.items():       # garde la forme réduite
            if rc[p]:
                f = int(rc[p])
                self.rows[q] = (rc ^ gf_mul_scalar(c, f), rs ^ gf_mul_scalar(s, f))
        self.rows[p] = (c, s)
        if len(self.rows) == self.K:
            out = np.stack([self.rows[i][1] for i in range(self.K)]).tobytes()
            self.result = out[:self.size]
        return self.result
