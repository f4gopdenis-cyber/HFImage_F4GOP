#!/usr/bin/env python3
"""Banc d'essai en boucle locale, sans radio :

  image -> AVIF -> trames HDR/DATA (RaptorQ) -> modem codec2 -> WAV
        -> canal simulé (bruit + fading) -> démodulation -> image reçue

Exemples :
  python3 loopback.py photo.jpg --mode DATAC1 --snr 5 --fading moderate
  python3 loopback.py --sample --sweep          # tableau de mesures complet
"""
import argparse
import io
import os
import time
import wave
import zlib

import numpy as np
from PIL import Image

import channel
from modem import MODE_FPB as FPB, Modem
from protocol import Receiver, Sender, parse_control



def load_image(path, sample):
    if sample or not path:
        from skimage import data
        return Image.fromarray(data.astronaut())
    return Image.open(path).convert("RGB")


def compress(img, width, target_bytes, fmt="avif"):
    """Redimensionne puis cherche la meilleure qualité qui tient dans target_bytes."""
    h = round(img.height * width / img.width)
    img = img.resize((width, h), Image.LANCZOS)
    lo, hi, best = 1, 95, None
    while lo <= hi:
        q = (lo + hi) // 2
        buf = io.BytesIO()
        img.save(buf, fmt.upper(), quality=q)
        if buf.tell() <= target_bytes:
            best, lo = (buf.getvalue(), q), q + 1
        else:
            hi = q - 1
    if best is None:
        raise SystemExit("image impossible à faire tenir dans la taille demandée")
    return best[0], best[1], img.size


def write_wav(path, samples, fs):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(fs)
        w.writeframes(samples.astype(np.int16).tobytes())


def run(data, fmt, mode, snr, fading, overhead, seed=1, outdir=None, tag="", verbose=True):
    """Une émission complète, plus un tour de NACK si nécessaire.
    Retourne un dict de mesures."""
    tx = Modem(mode, FPB[mode])
    rx = Modem(mode, FPB[mode])
    image_id = zlib.crc32(data) & 0xFFFF
    snd = Sender(data, fmt, "F4GOP", tx.payload_bytes, image_id)
    rcv = Receiver("F5ABC")

    res = {"mode": mode, "snr": snr, "fading": fading, "K": snd.K, "T": snd.T}
    t_air = 0.0
    for rnd in range(4):                          # émission initiale + 3 compléments max
        frames = (snd.frames(overhead=overhead, multiple=FPB[mode]) if rnd == 0
                  else snd.frames(extra=need, multiple=FPB[mode]))
        audio = tx.modulate(frames)
        noisy = channel.apply(audio, tx.fs, snr, fading, seed=seed + rnd)
        if outdir and rnd == 0:
            write_wav(os.path.join(outdir, f"{tag}tx.wav"), audio, tx.fs)
            write_wav(os.path.join(outdir, f"{tag}rx.wav"), noisy, tx.fs)
        got, snrs, done_at = None, [], None
        step = tx.fs // 10
        for i in range(0, len(noisy), step):     # traitement en flux, par 100 ms
            for payload, s in rx.demodulate(noisy[i:i + step]):
                snrs.append(s)
                r = rcv.feed(payload)
                if r and got is None:
                    got, done_at = r, (i + step) / tx.fs
        if got:
            t_air += done_at
            res.update(ok=True, rounds=rnd + 1, t_s=t_air, crc=True,
                       frames_ok=len(snrs), snr_est=float(np.median(snrs)) if snrs else None)
            if verbose:
                print(f"  {mode} SNR {snr:+} dB {fading:9s} -> image OK en {t_air:6.1f} s "
                      f"({rnd + 1} passage{'s' if rnd else ''})")
            res["data"] = got[1]
            break
        t_air += len(noisy) / tx.fs
        prog = rcv.progress(image_id)
        if prog is None:                          # même pas d'en-tête : on renvoie tout
            need = snd.K
        else:
            need = parse_control(rcv.nack(image_id))[3]
        res["t_s"] = t_air
        if verbose:
            print(f"  {mode} SNR {snr:+} dB {fading:9s} -> incomplet après passage {rnd + 1}"
                  f" ({prog}), NACK de {need} symboles")
    else:
        res.update(ok=False, rounds=4)
    tx.close(); rx.close()
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?")
    ap.add_argument("--sample", action="store_true", help="photo de test intégrée")
    ap.add_argument("--width", type=int, default=320)
    ap.add_argument("--bytes", type=int, default=8000, help="taille cible du fichier compressé")
    ap.add_argument("--format", default="avif", choices=["avif", "webp"])
    ap.add_argument("--mode", default="DATAC1", choices=list(FPB))
    ap.add_argument("--snr", type=float, default=10)
    ap.add_argument("--fading", default="none", choices=list(channel.CCIR))
    ap.add_argument("--overhead", type=float, default=0.1, help="redondance fontaine initiale")
    ap.add_argument("--sweep", action="store_true", help="balayage modes x SNR x canaux")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    img = load_image(a.image, a.sample)
    data, q, size = compress(img, a.width, a.bytes, a.format)
    with open(os.path.join(a.out, f"envoyee.{a.format}"), "wb") as f:
        f.write(data)
    print(f"Image {size[0]}x{size[1]}, {a.format.upper()} qualité {q} : {len(data)} octets")

    if not a.sweep:
        r = run(data, a.format, a.mode, a.snr, a.fading, a.overhead, outdir=a.out)
        if r.get("ok"):
            p = os.path.join(a.out, f"recue.{a.format}")
            open(p, "wb").write(r["data"])
            Image.open(p).save(os.path.join(a.out, "recue.png"))
            print(f"Image reçue identique bit à bit : {r['data'] == data}")
        return

    rows, images = [], {}
    # mode : (taille d'image adaptée au débit, SNR testés)
    plan = {"DATAC1X": (12000, [15, 12, 9, 6]),
            "DATAC1": (8000, [8, 5, 3, 1]),
            "DATAC3": (4000, [3, 0, -2, -4]),
            "DATAC4": (2000, [0, -2, -4, -6])}
    for mode, (nbytes, snrs) in plan.items():
        data, q, size = compress(img, a.width, nbytes, a.format)
        images[mode] = {"octets": len(data), "qualite": q}
        with open(os.path.join(a.out, f"envoyee_{mode}.{a.format}"), "wb") as f:
            f.write(data)
        Image.open(os.path.join(a.out, f"envoyee_{mode}.{a.format}")).save(
            os.path.join(a.out, f"envoyee_{mode}.png"))
        print(f"{mode} : image {len(data)} octets (qualité {q})")
        for fading in ("none", "moderate", "poor"):
            for snr in snrs:
                t0 = time.time()
                r = run(data, a.format, mode, snr, fading, a.overhead,
                        outdir=a.out if snr == snrs[0] and fading == "none" else None,
                        tag=f"{mode}_")
                r["cpu_s"] = time.time() - t0
                r["identique"] = r.pop("data", None) == data
                rows.append(r)
    import json
    with open(os.path.join(a.out, "mesures.json"), "w") as f:
        json.dump({"taille": size, "images": images, "essais": rows}, f, indent=1)


if __name__ == "__main__":
    main()
