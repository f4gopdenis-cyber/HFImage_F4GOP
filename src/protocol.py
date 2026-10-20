"""Couche transport v2 : trames DATA autoportantes + code fontaine (fountain.py).

Format commun : octet 0 = (type << 4) | version, octets 1-2 = ID image.

DATA (T + 14 o) : type | id | taille u24 | CRC32 u32 | SBN 1 o + ESI 3 o | symbole (T o)
HDR  (24 o)     : type | id | indicatif[8] | format | taille u32 | T u16 | CRC32 u32 | K u16
HYB (21 o + L)  : type | id | indicatif[8] | taille u32 | CRC32 u32 | format | L | lien (L o)
NACK (13 o)     : type | id | indicatif[8] | nb symboles demandés u16   -> tient en DATAC0
ACK  (11 o)     : type | id | indicatif[8]                              -> tient en DATAC0

Chaque trame DATA porte la taille et le CRC du fichier : le récepteur peut
décoder sans avoir reçu d'en-tête (T se déduit de la taille de trame du mode).
Le HDR n'est émis qu'une fois, en fin d'émission : il donne l'indicatif
(identification de la station) et le format.
"""
import hashlib
import math
import struct
import zlib

from fountain import Decoder, Encoder

VERSION = 2
T_HDR, T_DATA, T_NACK, T_ACK, T_HYB, T_PDATA = 1, 2, 3, 4, 5, 6   # T_PDATA = DATA d'un aperçu
T_QRV = 7                         # présence : « je suis à l'écoute avec HFImage »
T_HYB0 = 8                        # annonce hybride éclair (DATAC0) : le lien passe par Internet
MY_LOCATOR = ""                   # locator de la station (réglé par l'interface) : HDR, ACK
FORMATS = {"avif": 1, "webp": 2, "jpeg": 3, "txt": 4, "hft": 5, "svg": 6, "png": 7, "gif": 8, "file": 9}
FORMATS_INV = {v: k for k, v in FORMATS.items()}
HDR_FMT = ">BH8sBIHIH"           # 24 octets
HDR_LEN = struct.calcsize(HDR_FMT)
DATA_HEAD = 1 + 2 + 3 + 4         # type, id, taille, CRC32
DATA_OVERHEAD = DATA_HEAD + 4     # + identifiant de symbole


def _call(cs: str) -> bytes:
    return cs.upper().encode("ascii", "replace")[:8].ljust(8, b" ")


def symbol_size(payload_bytes: int) -> int:
    return payload_bytes - DATA_OVERHEAD


TEXT_MAGIC = b"HFTX"


def pack_text(text: str, image: bytes = b"") -> bytes:
    """Texte (+ image éventuelle) dans un seul fichier : « HFTX » | longueur u16 | texte | image."""
    t = text.encode("utf-8")[:65535]
    return TEXT_MAGIC + len(t).to_bytes(2, "big") + t + image


def unpack_text(data: bytes):
    """-> (texte, image) si c'est un paquet texte, sinon (None, data)."""
    if data[:4] != TEXT_MAGIC or len(data) < 6:
        return None, data
    n = int.from_bytes(data[4:6], "big")
    return data[6:6 + n].decode("utf-8", errors="replace"), data[6 + n:]


FILE_MAGIC = b"HFFL"


def pack_file(name: str, data: bytes) -> bytes:
    """Fichier quelconque : nom + contenu (compressé si ça le rend plus petit)."""
    import os
    n = os.path.basename(name).encode("utf-8")[:200]
    z = zlib.compress(data, 9)
    flags, body = (1, z) if len(z) < len(data) else (0, data)
    return FILE_MAGIC + bytes([flags, len(n)]) + n + body


def unpack_file(data: bytes):
    """-> (nom, contenu) si c'est un fichier, sinon None."""
    if data[:4] != FILE_MAGIC or len(data) < 6:
        return None
    flags, n = data[4], data[5]
    name = data[6:6 + n].decode("utf-8", errors="replace") or "fichier"
    body = data[6 + n:]
    if flags & 1:
        body = zlib.decompress(body)
    return name, body


def detect_format(data: bytes) -> str:
    if data[:4] == TEXT_MAGIC:
        return "hft"
    if data[:4] == FILE_MAGIC:
        return "file"
    if data[4:12] in (b"ftypavif", b"ftypavis"):
        return "avif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:2] == b"\xff\xd8":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:12] == b"\x00\x00\x00\x0cjP  \r\n\x87\n" or data[:4] == b"\xff\x4f\xff\x51":
        return "jp2"                                  # JPEG 2000 (images EasyPal / QSSTV)
    from imgfmt import is_svg
    if is_svg(data):
        return "svg"
    return "bin"


class Sender:
    """Prépare les trames d'une image pour une taille de charge utile donnée."""

    def __init__(self, data: bytes, fmt: str, callsign: str, payload_bytes: int, image_id: int,
                 preview=False):
        if payload_bytes < HDR_LEN:
            raise ValueError("mode trop petit (DATAC0 = ACK/NACK seulement)")
        if len(data) >= 1 << 24:
            raise ValueError("fichier trop gros (16 Mo max)")
        self.data, self.id = data, image_id & 0xFFFF
        self.T = symbol_size(payload_bytes)
        self.enc = Encoder(data, self.T)
        self.K = self.enc.K
        self.sent = 0  # nombre de symboles (ESI) déjà émis
        crc = zlib.crc32(data)
        typ = T_PDATA if preview else T_DATA
        self.data_head = struct.pack(">BH", (typ << 4) | VERSION, self.id) + \
            len(data).to_bytes(3, "big") + struct.pack(">I", crc)
        self.hdr = struct.pack(HDR_FMT, (T_HDR << 4) | VERSION, self.id, _call(callsign),
                               FORMATS[fmt], len(data), self.T, crc, self.K)
        if payload_bytes >= HDR_LEN + 4:          # + locator (pour la carte des stations)
            self.hdr += struct.pack(">I", pack_locator(MY_LOCATOR))

    def _data_frames(self, n: int):
        """n nouveaux symboles : d'abord les sources, puis des réparations jamais émises."""
        pkts = self.enc.packets(self.sent, n)
        self.sent += n
        return [self.data_head + p for p in pkts]

    def frames(self, overhead=0.1, extra=None, multiple=1):
        """Émission initiale (K*(1+overhead) symboles) ou complément après NACK
        (extra = nombre de symboles demandés), suivie d'un HDR d'identification.
        Le total est arrondi au multiple de `multiple` (trames par rafale) avec des
        symboles de réparation, plutôt qu'avec des trames vides."""
        n = extra if extra is not None else math.ceil(self.K * (1 + overhead))
        while (n + 1) % multiple:
            n += 1
        return self._data_frames(n) + [self.hdr]


class Receiver:
    """Accumule les trames reçues, rend les images complètes."""
    KEEP = 64            # images gardées en mémoire (programme ouvert des jours : pas de croissance sans fin)

    def __init__(self, callsign="RX"):
        self.call = callsign
        self.sessions = {}   # id -> dict
        self.done = {}       # id -> (info, data)  (les KEEP derniers)
        self.total = 0       # images complètes depuis le début

    def feed(self, payload: bytes):
        """Retourne (info, octets) quand une image vient d'être reconstituée."""
        if len(payload) < 3:
            return None
        typ, ver = payload[0] >> 4, payload[0] & 0x0F
        iid = struct.unpack(">H", payload[1:3])[0]
        if ver != VERSION:
            return None
        if typ == T_HDR:
            _, _, call, fmt, size, T, crc, K = struct.unpack(HDR_FMT, payload[:HDR_LEN])
            call = call.decode(errors="replace").strip()
            loc = unpack_locator(struct.unpack(">I", payload[HDR_LEN:HDR_LEN + 4])[0]) \
                if len(payload) >= HDR_LEN + 4 else ""
            s = self.sessions.get(iid)
            if s:
                s["info"]["call"] = call
                s["info"]["loc"] = loc
            elif iid not in self.done:
                self.sessions[iid] = {"info": self._info(iid, size, crc, T, call), "dec": None,
                                      "esi": set()}
                self.sessions[iid]["info"]["loc"] = loc
            if iid in self.done:
                self.done[iid][0]["call"] = call
                self.done[iid][0]["loc"] = loc
            return None
        if typ not in (T_DATA, T_PDATA) or iid in self.done:
            return None
        size = int.from_bytes(payload[3:6], "big")
        crc = struct.unpack(">I", payload[6:10])[0]
        T = len(payload) - DATA_OVERHEAD
        s = self.sessions.get(iid)
        if s is None or s["dec"] is None:
            info = s["info"] if s else self._info(iid, size, crc, T, None)
            s = self.sessions[iid] = {"info": info, "dec": Decoder(size, T),
                                      "esi": s["esi"] if s else set()}
        s["info"]["preview"] = typ == T_PDATA
        pkt = payload[DATA_HEAD:]
        s["esi"].add(int.from_bytes(pkt[1:4], "big"))
        data = s["dec"].add(pkt)
        if data is None or zlib.crc32(data) != s["info"]["crc"]:
            return None
        s["info"]["fmt"] = detect_format(data)
        self.done[iid] = (s["info"], data)
        self.total += 1
        s["dec"] = None                      # image complète : le décodeur (gros) n'est plus utile
        s["rank"] = s["info"]["K"]
        self._trim()
        return s["info"], data

    def _trim(self):
        for d in (self.sessions, self.done):
            for k in list(d)[:-self.KEEP]:
                del d[k]

    @staticmethod
    def _info(iid, size, crc, T, call):
        return {"id": iid, "call": call or "?", "size": size, "crc": crc, "T": T,
                "K": max(1, math.ceil(size / T)), "fmt": "?"}

    def progress(self, iid):
        """(symboles utiles reçus, K) ou None si rien de cette image."""
        s = self.sessions.get(iid)
        if not s:
            return None
        return (s["dec"].rank if s["dec"] else s.get("rank", 0)), s["info"]["K"]

    def loss_rate(self, iid):
        """Taux de pertes estimé d'après les trous dans les numéros de symboles."""
        esi = self.sessions[iid]["esi"]
        return 1 - len(esi) / (max(esi) + 1) if esi else 1.0

    def nack(self, iid, margin=1):
        """Trame NACK : symboles manquants (+ marge), majorés selon les pertes
        observées pour que le complément ait de bonnes chances de suffire."""
        got, K = self.progress(iid)
        ok = max(0.25, 1 - self.loss_rate(iid))
        need = max(1, math.ceil((K - got + margin) / ok))
        return struct.pack(">BH8sH", (T_NACK << 4) | VERSION, iid, _call(self.call), need)

    def ack(self, iid, snr=None):
        """ACK + report (SNR mesuré à la réception, octet 0 = pas de report)
        + locator à 4 caractères (2 octets) : 14 octets, une trame DATAC0 pleine."""
        rep = 0 if snr is None else max(1, min(255, int(round(snr)) + 100))
        return struct.pack(">BH8sBH", (T_ACK << 4) | VERSION, iid, _call(self.call), rep,
                           pack_loc4(MY_LOCATOR))


HYB_FMT = ">BH8sIIBB"           # 21 octets, suivis du lien
HYB_LEN = struct.calcsize(HYB_FMT)


def hybrid_frame(image_id: int, callsign: str, data: bytes, fmt: str, url: str) -> bytes:
    """Trame d'annonce hybride : tout ce qu'il faut pour télécharger et vérifier."""
    u = url.encode("utf-8")
    if len(u) > 255:
        raise ValueError("lien trop long (255 caractères max)")
    return struct.pack(HYB_FMT, (T_HYB << 4) | VERSION, image_id & 0xFFFF, _call(callsign),
                       len(data), zlib.crc32(data), FORMATS.get(fmt, 0), len(u)) + u


def parse_hybrid(payload: bytes):
    """Trame HYB -> dict, ou None si ce n'en est pas une (ou si elle est tronquée)."""
    if len(payload) < HYB_LEN or payload[0] != ((T_HYB << 4) | VERSION):
        return None
    _, iid, call, size, crc, fmt, n = struct.unpack(HYB_FMT, payload[:HYB_LEN])
    u = payload[HYB_LEN:HYB_LEN + n]
    if len(u) != n:
        return None
    return {"id": iid, "call": call.decode(errors="replace").strip(), "size": size, "crc": crc,
            "fmt": FORMATS_INV.get(fmt, "bin"), "url": u.decode("utf-8", errors="replace")}


# ---------------------------------------------------------------- hybride éclair
# Une seule trame DATAC0 (14 octets utiles) : empreinte de l'image, taille, format, ID.
# Le lien de téléchargement part en même temps par le serveur de présence (MQTT), rangé
# sous cette empreinte. L'image téléchargée doit avoir exactement cette empreinte
# (SHA-256, 48 premiers bits) : une fausse annonce Internet ne peut pas la remplacer.
FLASH_FMT = ">B6s3sBH"          # 13 octets
FLASH_LEN = struct.calcsize(FLASH_FMT)


def flash_key(data: bytes) -> str:
    """Empreinte de l'image pour l'hybride éclair (12 caractères hexadécimaux)."""
    return hashlib.sha256(data).digest()[:6].hex()


def flash_frame(image_id: int, data: bytes, fmt: str) -> bytes:
    if len(data) >= 1 << 24:
        raise ValueError("image trop grande pour l'hybride éclair")
    return struct.pack(FLASH_FMT, (T_HYB0 << 4) | VERSION, bytes.fromhex(flash_key(data)),
                       len(data).to_bytes(3, "big"), FORMATS.get(fmt, 0), image_id & 0xFFFF)


def parse_flash(payload: bytes):
    """Trame éclair -> {id, key, size, fmt}, ou None."""
    if len(payload) < FLASH_LEN or payload[0] != ((T_HYB0 << 4) | VERSION):
        return None
    _, key, size, fmt, iid = struct.unpack(FLASH_FMT, payload[:FLASH_LEN])
    size = int.from_bytes(size, "big")
    if size <= 0:
        return None
    return {"id": iid, "key": key.hex(), "size": size, "fmt": FORMATS_INV.get(fmt, "bin")}


_LOC_RADIX = (18, 18, 10, 10, 25, 25)


def pack_locator(loc: str) -> int:
    """Locator Maidenhead (4 ou 6 caractères) -> entier (0 = aucun)."""
    loc = (loc or "").strip().upper()
    if len(loc) not in (4, 6):
        return 0
    try:
        d = [ord(loc[0]) - 65, ord(loc[1]) - 65, int(loc[2]), int(loc[3])]
        d += [ord(loc[4]) - 65, ord(loc[5]) - 65] if len(loc) == 6 else [24, 24]
    except ValueError:
        return 0
    v = 0
    for x, r in zip(d, _LOC_RADIX):
        if not 0 <= x < r:
            return 0
        v = v * r + x
    return v + 1


def unpack_locator(v: int) -> str:
    if not v:
        return ""
    v -= 1
    d = []
    for r in reversed(_LOC_RADIX):
        d.append(v % r)
        v //= r
    d.reverse()
    s = chr(65 + d[0]) + chr(65 + d[1]) + str(d[2]) + str(d[3])
    if d[4] < 24 and d[5] < 24:
        s += (chr(65 + d[4]) + chr(65 + d[5])).lower()
    return s


def pack_loc4(loc: str) -> int:
    """Carré de locator (4 caractères) -> 1..32400 (0 = aucun) : tient sur 2 octets."""
    loc = (loc or "").strip().upper()[:4]
    try:
        a, b, c, d = ord(loc[0]) - 65, ord(loc[1]) - 65, int(loc[2]), int(loc[3])
    except (IndexError, ValueError):
        return 0
    if not (0 <= a < 18 and 0 <= b < 18):
        return 0
    return ((a * 18 + b) * 10 + c) * 10 + d + 1


def unpack_loc4(v: int) -> str:
    if not v or v > 32400:
        return ""
    v -= 1
    d, v = v % 10, v // 10
    c, v = v % 10, v // 10
    b, a = v % 18, v // 18
    return f"{chr(65 + a)}{chr(65 + b)}{c}{d}"


def locator_to_latlon(loc: str):
    """Locator Maidenhead -> (lat, lon) du centre du carré ; None si invalide."""
    loc = (loc or "").strip().upper()
    if len(loc) < 4:
        return None
    try:
        lon = (ord(loc[0]) - 65) * 20 - 180 + int(loc[2]) * 2
        lat = (ord(loc[1]) - 65) * 10 - 90 + int(loc[3])
        if len(loc) >= 6 and "A" <= loc[4] <= "X" and "A" <= loc[5] <= "X":
            lon += (ord(loc[4]) - 65) * (2 / 24) + 1 / 24
            lat += (ord(loc[5]) - 65) * (1 / 24) + 1 / 48
        else:
            lon += 1
            lat += 0.5
    except ValueError:
        return None
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        return None
    return lat, lon


def qrv_frame(callsign: str, locator: str = "") -> bytes:
    """Trame de présence (DATAC0, 13 octets) : indicatif + locator."""
    return struct.pack(">B8sI", (T_QRV << 4) | VERSION, _call(callsign), pack_locator(locator))


def parse_control(payload: bytes):
    """-> (« NACK », id, indicatif, symboles demandés) | (« ACK », id, indicatif, report dB ou None)
    | (« QRV », 0, indicatif, locator) | None"""
    typ = payload[0] >> 4
    if typ == T_QRV:
        call, loc = struct.unpack(">8sI", payload[1:13])
        return "QRV", 0, call.decode(errors="replace").strip(), unpack_locator(loc)
    iid = struct.unpack(">H", payload[1:3])[0]
    call = payload[3:11].decode(errors="replace").strip()
    if typ == T_NACK:
        return "NACK", iid, call, struct.unpack(">H", payload[11:13])[0]
    if typ == T_ACK:
        rep = payload[11] if len(payload) > 11 else 0
        loc = unpack_loc4(struct.unpack(">H", payload[12:14])[0]) if len(payload) >= 14 else ""
        return "ACK", iid, call, ((rep - 100) if rep else None, loc)
    return None
