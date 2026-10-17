"""Moteur émission / réception, indépendant de l'interface (testable seul).

La réception démodule en parallèle DATAC1X, DATAC1, DATAC3 et DATAC4 : pas besoin de
savoir à l'avance dans quel mode la station émet.
"""
import io
import os
import time
import wave
import zlib

import numpy as np
from PIL import Image

import audio
import imgfmt
from modem import MODE_FPB, Modem
import qrmfilter
import protocol
from protocol import (T_ACK, T_HDR, T_NACK, T_QRV, Receiver, Sender, detect_format, hybrid_frame,
                      parse_control, parse_hybrid, unpack_text)

RX_MODES = ("DATAC1X", "DATAC1", "DATAC3", "DATAC4", "DATAC0")   # DATAC0 : BSR / ACK


def png_colors(q):
    """« Qualité » PNG -> nombre de couleurs de la palette (q1 = 2 … q95 = 256)."""
    return max(2, min(256, int(round(2 ** (1 + 7 * (max(1, min(95, q)) - 1) / 94)))))


def quality_label(fmt, q):
    if fmt == "png":
        return f"PNG {png_colors(q)} couleurs"
    return f"{'JPG' if fmt == 'jpeg' else fmt.upper()} q{q}"


def _encode(img, fmt, q, speed):
    buf = io.BytesIO()
    if fmt == "png":
        # palette adaptée (dessins, schémas, captures d'écran, texte) ; une photo
        # passe mieux en avif
        pal = img.convert("RGB").quantize(colors=png_colors(q), method=Image.Quantize.MEDIANCUT,
                                          dither=Image.Dither.NONE)
        pal.save(buf, "PNG", optimize=True, compress_level=9)
    elif fmt == "avif":
        img.save(buf, "AVIF", quality=q, speed=speed)
    elif fmt == "jpeg":
        img.save(buf, "JPEG", quality=max(1, min(95, q)), optimize=True, progressive=True,
                 subsampling=2)
    else:
        img.save(buf, fmt.upper(), quality=q, method=6 if speed <= 6 else 4)
    return buf.getvalue()


def resize_to(img: Image.Image, width) -> Image.Image:
    img = img.convert("RGB")
    if width not in (None, "orig", "originale") and img.width > int(width):
        w = int(width)
        img = img.resize((w, max(1, round(img.height * w / img.width))), Image.LANCZOS)
    return img


def compress(img: Image.Image, width, target_bytes: int, fmt="avif"):
    """Redimensionne puis cherche la meilleure qualité qui tient dans target_bytes.
    Recherche rapide (AVIF vitesse 8), puis encodage final plus soigné (vitesse 6,
    fichier plus petit à qualité égale) en remontant la qualité si la place le permet.
    Retourne (octets, qualité, (l, h))."""
    img = resize_to(img, width)
    lo, hi, q_fast = 1, 95, 0
    while lo <= hi:
        q = (lo + hi) // 2
        if len(_encode(img, fmt, q, 8)) <= target_bytes:
            q_fast, lo = q, q + 1
        else:
            hi = q - 1
    # encodage final plus soigné : recherche fine de la meilleure qualité qui tient
    best = None
    lo, hi = max(1, q_fast), min(95, q_fast + 12)
    while lo <= hi:
        q = (lo + hi) // 2
        d = _encode(img, fmt, q, 6)
        if len(d) <= target_bytes:
            best, lo = (d, q), q + 1
        else:
            hi = q - 1
    if best is None:
        best = (_encode(img, fmt, max(1, q_fast), 6), max(1, q_fast))
    return best[0], best[1], img.size


def bytes_for_quality(img: Image.Image, width, quality=45, fmt="avif") -> int:
    """Taille du fichier pour une qualité « correcte » à cette largeur."""
    return len(_encode(resize_to(img, width), fmt, quality, 6))


def make_preview(img: Image.Image, fmt="avif", target=900):
    """Aperçu rapide : petite image (~1 ko) émise avant l'image complète."""
    return compress(img, 160, target, fmt)


def max_bytes_for(mode: str, seconds: float, overhead: float) -> int:
    """Plus gros fichier qui tient dans `seconds` d'émission (redondance comprise)."""
    m = Modem(mode, MODE_FPB[mode])
    try:
        bursts = 0
        while m.duration_s(bursts + 1) <= seconds:
            bursts += 1
        n_data = bursts * m.fpb - 1                  # une trame d'identification en fin
        k = int(n_data / (1 + overhead))
        return max(0, k * (m.payload_bytes - 14))
    finally:
        m.close()


def compress_auto(img: Image.Image, target_bytes: int, fmt="avif",
                  widths=(1920, 1600, 1280, 1024, 800, 640, 480, 320, 240, 160, 120), min_quality=30):
    """Choisit la plus grande largeur qui garde une qualité correcte dans le budget.
    Retourne (octets, qualité, (l, h)) ; si rien ne tient, la plus petite version
    possible (à l'appelant de vérifier len(octets) <= target_bytes)."""
    fits, smallest = [], None
    widths = [w for w in widths if w <= img.width] or [img.width]
    for w in widths:
        # inutile d'essayer une grande largeur si même la qualité minimale ne tient pas
        if w >= 480 and len(_encode(resize_to(img, w), fmt, min_quality, 8)) > target_bytes * 1.15:
            continue
        r = compress(img, w, target_bytes, fmt)
        if len(r[0]) <= target_bytes:
            if r[1] >= min_quality:
                return r
            fits.append(r)
        if smallest is None or len(r[0]) < len(smallest[0]):
            smallest = r
    if fits:
        return max(fits, key=lambda r: r[1])
    return smallest


class Transmission:
    """Une image prête à émettre dans un mode donné, avec aperçu rapide optionnel
    (petite image émise d'abord : les stations la voient en quelques secondes)."""

    def __init__(self, data: bytes, fmt: str, callsign: str, mode: str, overhead: float,
                 preview: bytes = None):
        self.data, self.fmt, self.mode = data, fmt, mode
        self.modem = Modem(mode, MODE_FPB[mode])
        # l'ID dépend aussi du mode : la même image en deux modes = deux sessions
        self.image_id = zlib.crc32(data + mode.encode()) & 0xFFFF
        self.sender = Sender(data, fmt, callsign, self.modem.payload_bytes, self.image_id)
        self.overhead = overhead
        self.preview = preview
        self.psender = None
        if preview:
            pid = (self.image_id + 1) & 0xFFFF
            self.psender = Sender(preview, fmt, callsign, self.modem.payload_bytes, pid, preview=True)
        self.preview_sent = False

    def frames(self, extra=None):
        fpb = MODE_FPB[self.mode]
        out = []
        if extra is None:
            if self.psender is not None and not self.preview_sent:
                out += self.psender.frames(overhead=0.25, multiple=fpb)
                self.preview_sent = True
            out += self.sender.frames(overhead=self.overhead, multiple=fpb)
        else:
            out += self.sender.frames(extra=extra, multiple=fpb)
        return out

    def audio(self, extra=None) -> np.ndarray:
        """Échantillons 8 kHz int16 de toute l'émission (initiale ou complément)."""
        return self.modem.modulate(self.frames(extra))

    def audio_chunks(self, extra=None):
        """Même chose, rafale par rafale (pour les longues émissions : pas tout en mémoire)."""
        return self.modem.modulate_iter(self.frames(extra))

    def complement_size(self) -> int:
        """Nombre de symboles d'un complément : ~20 % de l'image, au moins une rafale."""
        n = max(self.modem.fpb - 1, int(np.ceil(self.sender.K * 0.2)))
        while (n + 1) % self.modem.fpb:
            n += 1
        return n

    def _bursts(self, K, overhead=None, extra=None):
        m = self.modem
        n = int(np.ceil(K * (1 + overhead))) if extra is None else extra
        while (n + 1) % m.fpb:
            n += 1
        return (n + 1) // m.fpb

    def estimate_s(self, extra=None) -> float:
        """Durée d'une émission (initiale avec aperçu, ou complément de `extra`
        symboles), calculée exactement sans consommer de symboles."""
        if extra is not None:
            return self.modem.duration_s(self._bursts(self.sender.K, extra=extra))
        b = self._bursts(self.sender.K, self.overhead)
        if self.psender is not None and not self.preview_sent:
            b += self._bursts(self.psender.K, 0.25)
        return self.modem.duration_s(b)

    def preview_s(self) -> float:
        """Délai avant que l'aperçu soit reçu (0 sans aperçu)."""
        if self.psender is None:
            return 0.0
        return self.modem.duration_s(self._bursts(self.psender.K, 0.25))


class HybridTransmission:
    """Annonce hybride : la trame HYB est émise 3 fois en rafales indépendantes
    (DATAC3 ; DATAC1 si le lien est trop long) ; une seule copie suffit."""

    def __init__(self, data: bytes, fmt: str, callsign: str, url: str):
        self.data, self.fmt, self.url = data, fmt, url
        self.image_id = zlib.crc32(data + url.encode()) & 0xFFFF
        self.frame = hybrid_frame(self.image_id, callsign, data, fmt, url)
        for mode in ("DATAC3", "DATAC1"):
            m = Modem(mode, MODE_FPB[mode])
            if len(self.frame) <= m.payload_bytes:
                self.mode, self.modem = mode, m
                break
            m.close()
        else:
            raise ValueError("lien trop long pour une trame radio")

    COPIES = 3

    def frames(self):
        return [self.frame] * (self.COPIES if self.modem.fpb == 1 else self.modem.fpb)

    def audio(self) -> np.ndarray:
        return self.modem.modulate(self.frames())

    def estimate_s(self) -> float:
        n = self.COPIES if self.modem.fpb == 1 else 1
        return self.modem.duration_s(n)


class ControlTransmission:
    """Trame courte BSR (NACK) ou ACK en DATAC0, émise 2 fois (~1,7 s)."""

    def __init__(self, payload: bytes, copies=2):
        self.mode = "DATAC0"
        self.modem = Modem("DATAC0", 1)
        self._frames = [payload] * copies

    def frames(self):
        return list(self._frames)

    def estimate_s(self):
        return self.modem.duration_s(len(self._frames))


def cw_audio(text: str, wpm=20, freq=1500.0, fs=8000, amp=12000) -> np.ndarray:
    """Identification en morse (int16 8 kHz), dans la bande du modem."""
    code = {"A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.",
            "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.",
            "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-", "U": "..-",
            "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--", "Z": "--..", "0": "-----",
            "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....", "6": "-....",
            "7": "--...", "8": "---..", "9": "----.", "/": "-..-.", "?": "..--.."}
    dot = 1.2 / wpm
    n = int(dot * fs)
    t = np.arange(n * 3) / fs
    ramp = np.minimum(1, np.minimum(np.arange(n * 3), np.arange(n * 3)[::-1]) / (0.005 * fs))
    tone = (amp * np.sin(2 * np.pi * freq * t) * ramp).astype(np.int16)
    gap = np.zeros(n, np.int16)
    out = [np.zeros(int(0.3 * fs), np.int16)]
    for ch in text.upper():
        if ch == " ":
            out.append(np.zeros(n * 4, np.int16))
            continue
        for sym in code.get(ch, ""):
            out.append(tone[:n] if sym == "." else tone)
            out.append(gap)
        out.append(np.zeros(n * 2, np.int16))
    out.append(np.zeros(int(0.3 * fs), np.int16))
    return np.concatenate(out)


def tune_audio(seconds=10.0, freq=1500.0, fs=8000, amp=16000) -> np.ndarray:
    """Porteuse de réglage (Accord) : sinus pur à la crête du signal modem."""
    t = np.arange(int(seconds * fs)) / fs
    ramp = np.minimum(1, np.minimum(t, t[::-1]) / 0.02)
    return (amp * ramp * np.sin(2 * np.pi * freq * t)).astype(np.int16)


class RxEngine:
    """Reçoit des échantillons 8 kHz, rend les images complètes via callbacks.

    on_image(info, chemin, png, mode) : image complète (indicatif éventuellement
    encore inconnu, "?") ; on_ident(info, chemin, png) : l'indicatif vient d'arriver
    avec la trame d'identification de fin, les fichiers ont été renommés."""

    def __init__(self, callsign, outdir, on_image=None, on_status=None, on_ident=None,
                 on_hybrid=None, on_control=None):
        self.modems = {m: Modem(m, MODE_FPB[m]) for m in RX_MODES}
        # coupe-QRM devant chaque démodulateur (porteuses, CW, RTTY, signaux voisins)
        self.qrm = True
        self.filters = {m: qrmfilter.QrmFilter(m) for m in RX_MODES}
        self.rcv = Receiver(callsign)
        self.outdir = outdir
        self.on_image = on_image or (lambda *a: None)
        self.on_status = on_status or (lambda *a: None)
        self.on_ident = on_ident or (lambda *a: None)
        self.on_hybrid = on_hybrid or (lambda *a: None)
        self.hyb_seen = set()
        self.on_control = on_control or (lambda *a: None)
        # suivi par image : dernière trame, fin d'émission vue (HDR), mode
        self.activity = {}
        self.last = {"snr": None, "mode": None, "frames": 0}
        self.saved = {}      # id -> [chemin, png, base sans indicatif]
        os.makedirs(outdir, exist_ok=True)

    def process(self, samples8k: np.ndarray):
        for mode, modem in self.modems.items():
            x = self.filters[mode].process(samples8k) if self.qrm else samples8k
            for payload, snr in modem.demodulate(x):
                self.last.update(snr=snr, mode=mode, frames=self.last["frames"] + 1)
                iid = int.from_bytes(payload[1:3], "big")
                typ = payload[0] >> 4
                if typ in (T_NACK, T_ACK, T_QRV):
                    ctl = parse_control(payload)
                    if ctl:
                        self.on_control(ctl[0], ctl[1], ctl[2], ctl[3], snr)
                    continue
                hyb = parse_hybrid(payload)
                if hyb is not None:
                    self.on_status(dict(self.last, id=iid, progress=None, call=hyb["call"]))
                    key = (hyb["id"], hyb["crc"])
                    if key not in self.hyb_seen:          # une seule fois par annonce
                        self.hyb_seen.add(key)
                        self.on_hybrid(hyb, mode)
                    continue
                res = self.rcv.feed(payload)
                act = self.activity.setdefault(iid, {"end": 0, "mode": mode, "t": 0.0})
                act["t"] = time.time()
                act["mode"] = mode
                if typ == T_HDR:
                    act["end"] += 1          # fin d'une émission (ou d'un complément FIX)
                s = self.rcv.sessions.get(iid)
                call = s["info"]["call"] if s else "?"
                self.on_status(dict(self.last, id=iid, progress=self.rcv.progress(iid),
                                    call=None if call == "?" else call))
                if res:
                    self._save(res, mode)
                elif iid in self.saved and call != "?" and not self.saved[iid][3]:
                    self._rename(iid, call)

    def save_hybrid(self, hyb, data, mode):
        """Enregistre une image hybride téléchargée et prévient l'interface."""
        info = {"id": hyb["id"], "call": hyb["call"] or "?", "size": len(data), "crc": hyb["crc"],
                "fmt": hyb["fmt"], "hybrid": True, "url": hyb["url"]}
        self._save((info, data), mode + "-HYB")

    def incomplete(self):
        """Images en cours mais incomplètes : [(id, reçus, K, fin_vue, âge_s, mode, indicatif)]."""
        out = []
        now = time.time()
        for iid, s in list(self.rcv.sessions.items()):
            if iid in self.rcv.done or s.get("dec") is None or s["info"].get("preview"):
                continue
            act = self.activity.get(iid, {"end": 0, "t": now, "mode": "?"})
            got, K = self.rcv.progress(iid)
            out.append((iid, got, K, act["end"], now - act["t"], act["mode"], s["info"]["call"]))
        return out

    def _save(self, res, mode):
        info, data = res
        text, img = unpack_text(data)
        if text is not None:
            info["text"] = text            # gardé aussi pour l'identification de fin
            stamp = time.strftime("%Y%m%d_%H%M%S")
            call = info["call"]
            tbase = os.path.join(self.outdir, f"{stamp}_{mode}_texte" + ("" if call == "?" else "_" + call))
            with open(tbase + ".txt", "w", encoding="utf-8") as f:
                f.write(text)
            if not img:                               # message texte seul
                self.saved[info["id"]] = [tbase + ".txt", None, tbase, call != "?"]
                self.on_image(dict(info, fmt="txt"), tbase + ".txt", None, mode)
                return
            data = img
            info["fmt"] = detect_format(img)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        call = info["call"]
        if info.get("fmt") == "file" or data[:4] == protocol.FILE_MAGIC:
            # fichier quelconque : rangé dans « fichiers », sous son nom d'origine
            try:
                name, body = protocol.unpack_file(data)
            except Exception:
                name, body = "fichier.bin", data
            safe = "".join(c if (c.isalnum() or c in "._- ()") else "_" for c in name).strip(" .") or "fichier"
            d = os.path.join(self.outdir, "fichiers")
            os.makedirs(d, exist_ok=True)
            base = os.path.join(d, f"{stamp}_{mode}")
            if call != "?":
                base += "_" + call.replace("/", "-")
            path = base + "__" + safe
            with open(path, "wb") as f:
                f.write(body)
            self.saved[info["id"]] = [path, None, base, call != "?"]
            self.on_image(dict(info, fmt="file", filename=name, size=len(body)), path, None, mode)
            return
        stamp = time.strftime("%Y%m%d_%H%M%S")
        call = info["call"]
        base = os.path.join(self.outdir, f"{stamp}_{mode}" + ("_apercu" if info.get("preview") else ""))
        if call != "?":
            base += "_" + call.replace("/", "-")
        path, png = imgfmt.save_received(base, info["fmt"], data)
        self.saved[info["id"]] = [path, png, base, call != "?"]
        self.on_image(info, path, png, mode)

    def _rename(self, iid, call):
        path, png, base, _ = self.saved[iid]
        nb = base + "_" + call.replace("/", "-")
        try:
            same = png == path
            new_path = nb + path[len(base):]
            os.replace(path, new_path)
            path = new_path
            if same:
                png = path
            elif png:
                os.replace(png, nb + ".png")
                png = nb + ".png"
        except OSError:
            pass
        self.saved[iid] = [path, png, nb, True]
        self.on_ident(self.rcv.done[iid][0], path, png)

    def nack_for(self, iid):
        return self.rcv.nack(iid)


def read_wav_8k(path) -> np.ndarray:
    """WAV mono/stéréo 16 bits, 8 ou 48 kHz -> int16 8 kHz."""
    with wave.open(path, "rb") as w:
        fs, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if sw != 2:
        raise ValueError("seuls les WAV 16 bits sont pris en charge")
    x = np.frombuffer(raw, dtype=np.int16)
    if ch > 1:
        x = x.reshape(-1, ch)[:, 0]
    if fs == 8000:
        return x.copy()
    if fs == 48000:
        return audio.Downsampler().process(x.astype(np.float32) / 32768.0)
    # autre fréquence : interpolation linéaire vers 48 kHz puis décimation
    t48 = np.arange(int(len(x) * 48000 / fs)) * fs / 48000
    x48 = np.interp(t48, np.arange(len(x)), x.astype(np.float64)) / 32768.0
    return audio.Downsampler().process(x48.astype(np.float32))


def write_wav(path, samples, fs):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(fs)
        w.writeframes(np.asarray(samples, dtype=np.int16).tobytes())
