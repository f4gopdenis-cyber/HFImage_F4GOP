"""Analyseur d'enregistrement : que s'est-il passé pendant une réception ?

On relit un fichier WAV (bouton WAVE, ou tout enregistrement de la sortie audio du poste)
et on mesure, trame par trame et pour chaque mode :
- trames justes / détectées mais fausses, SNR, décalage de fréquence ;
- niveau audio (trop fort = écrêtage, trop faible) ;
- brouillage étroit (porteuses, CW, RTTY) : fréquence et part du temps ;
- ce que le coupe-QRM a sauvé (comparaison avec / sans filtre) ;
- pertes groupées (QSB) ou isolées ;
puis on en tire un diagnostic en clair et le mode conseillé.
"""
import ctypes
import time
import wave

import numpy as np

import engine
import modem as M
import qrmfilter

MODES = ("DATAC1X", "DATAC1", "DATAC3", "DATAC4", "DATAC0", "DATAC13")   # DATAC13 : annonce éclair
THR = {"DATAC1X": 9, "DATAC1": 5, "DATAC3": 0, "DATAC4": -4, "DATAC0": 0, "DATAC13": -7}   # SNR réel (comme le mode Auto)


class _Stats(ctypes.Structure):
    """Début de struct MODEM_STATS de codec2 (le reste est réservé, non lu)."""
    _fields_ = [("Nc", ctypes.c_int), ("snr_est", ctypes.c_float),
                ("rx_symbols", ctypes.c_float * (320 * 51 * 2)),
                ("nr", ctypes.c_int), ("sync", ctypes.c_int), ("foff", ctypes.c_float),
                ("rx_timing", ctypes.c_float), ("clock_offset", ctypes.c_float),
                ("sync_metric", ctypes.c_float), ("pre", ctypes.c_int), ("post", ctypes.c_int),
                ("uw_fails", ctypes.c_int), ("_reserve", ctypes.c_char * 65536)]


M.lib.freedv_get_modem_extended_stats.argtypes = [ctypes.c_void_p, ctypes.c_void_p]


def _frames(x, mode, use_filter, progress=None):
    """Démodule tout le fichier dans un mode. -> liste d'événements (t, ok, snr, foff), nb de préambules."""
    m = M.Modem(mode, M.MODE_FPB[mode])
    flt = qrmfilter.QrmFilter(mode) if use_filter else None
    delay = (flt.CTX if flt else 0)
    out = (ctypes.c_ubyte * m.frame_bytes)()
    st = _Stats()
    ev, pos_out = [], 0
    step = 8000
    try:
        for i in range(0, len(x) + 3 * 8000, step):
            chunk = x[i:i + step] if i < len(x) else np.zeros(step, np.int16)
            y = flt.process(chunk) if flt else chunk
            buf = np.concatenate([m._rxbuf, y.astype(np.int16)])
            pos = 0
            while True:
                nin = M.lib.freedv_nin(m.f)
                if pos + nin > len(buf):
                    break
                c = np.ascontiguousarray(buf[pos:pos + nin])
                n = M.lib.freedv_rawdatarx(m.f, out, c.ctypes.data_as(M._sp))
                pos += nin
                if n:
                    frame = bytes(out)[:n]
                    ok = M.crc16(frame[:-2]) == ((frame[-2] << 8) | frame[-1])
                    M.lib.freedv_get_modem_extended_stats(m.f, ctypes.byref(st))
                    t = (pos_out + pos - len(m._rxbuf) - delay) / 8000
                    ev.append((max(0.0, t), ok, float(M.true_snr(mode, st.snr_est)), float(st.foff)))
            pos_out += len(y)
            m._rxbuf = buf[pos:]
            if progress and i % (step * 10) == 0:
                progress(min(1.0, i / max(1, len(x))))
        M.lib.freedv_get_modem_extended_stats(m.f, ctypes.byref(st))
        return ev, int(st.pre)
    finally:
        m.close()


def _level(path):
    with wave.open(path, "rb") as w:
        fs, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if sw != 2:
        raise ValueError("seuls les WAV 16 bits sont pris en charge")
    a = np.frombuffer(raw, dtype=np.int16)
    if ch > 1:
        a = a.reshape(-1, ch)[:, 0]
    a = a.astype(np.float64)
    peak = float(np.max(np.abs(a))) if len(a) else 0.0
    clip = float(np.mean(np.abs(a) >= 32700)) if len(a) else 0.0
    # niveau RMS des secondes « actives » (signal présent)
    sec = max(1, fs)
    blocks = [a[i:i + sec] for i in range(0, len(a) - sec + 1, sec)] or [a]
    rms = np.array([np.sqrt(np.mean(b ** 2)) for b in blocks])
    act = rms[rms > np.median(rms) * 1.5] if len(rms) > 3 else rms
    rms_act = float(np.median(act)) if len(act) else float(np.median(rms))
    db = lambda v: 20 * np.log10(max(v, 1e-9) / 32768)
    return {"fs": fs, "duration": len(a) / fs, "peak_db": db(peak), "rms_db": db(rms_act),
            "clip": clip}


def _qrm_lines(x, fs=8000):
    """Raies étroites persistantes (porteuses, CW, RTTY) : [(fréquence Hz, part du temps)]."""
    n, hop = 512, 256
    if len(x) < n * 4:
        return [], None
    w = np.hanning(n)
    frames = np.lib.stride_tricks.sliding_window_view(x.astype(np.float64), n)[::hop] * w
    P = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    f = np.fft.rfftfreq(n, 1 / fs)
    band = (f >= 300) & (f <= 2700)
    Pb = qrmfilter._box(P[:, band], 5, 0)
    base = np.median(Pb, axis=1, keepdims=True)
    bad = Pb > base * 10 ** (12 / 10)
    frac = bad.mean(axis=0)
    fb = f[band]
    pm = np.mean(P[:, band], axis=0)
    lines = []
    for i in np.argsort(-frac):
        if frac[i] < 0.15:
            break
        near = np.abs(fb - fb[i]) <= 60
        j = int(np.argmax(np.where(near, pm, -1)))          # raie la plus forte du groupe
        if all(abs(fb[j] - lf) > 90 for lf, _ in lines):
            # fréquence affinée (interpolation parabolique sur 3 raies)
            fj = float(fb[j])
            if 0 < j < len(pm) - 1:
                a_, b_, c_ = np.log(pm[j - 1] + 1e-9), np.log(pm[j] + 1e-9), np.log(pm[j + 1] + 1e-9)
                den = a_ - 2 * b_ + c_
                if den < 0:
                    fj += 0.5 * (a_ - c_) / den * (fb[1] - fb[0])
            lines.append((fj, float(frac[i])))
        if len(lines) >= 4:
            break
    # spectre moyen (pour le graphique)
    spec = 10 * np.log10(np.mean(P, axis=0) + 1e-9)
    return lines, (f, spec)


def analyze(path, progress=lambda f, msg="": None):
    rep = {"path": path, "t": time.time()}
    rep["level"] = _level(path)
    x = engine.read_wav_8k(path)
    rep["duration"] = len(x) / 8000
    progress(0.02, "brouillage")
    rep["qrm"], spec = _qrm_lines(x)
    rep["spectrum"] = spec
    modes = {}
    total = len(MODES)
    for k, mode in enumerate(MODES):
        progress(0.05 + 0.75 * k / total, mode)
        ev, pre = _frames(x, mode, True,
                          lambda f, k=k: progress(0.05 + 0.75 * (k + f) / total, mode))
        modes[mode] = {"events": ev, "pre": pre}
    # sans coupe-QRM, seulement pour les modes où il s'est passé quelque chose
    active = [m for m in MODES if modes[m]["events"] or modes[m]["pre"]]
    for k, mode in enumerate(active):
        progress(0.8 + 0.18 * k / max(1, len(active)), mode + " (sans coupe-QRM)")
        ev, _ = _frames(x, mode, False)
        modes[mode]["raw_ok"] = sum(1 for e in ev if e[1])
    rep["modes"] = modes
    rep["diag"] = diagnose(rep)
    progress(1.0, "")
    return rep


def _summary(ev):
    ok = [e for e in ev if e[1]]
    bad = [e for e in ev if not e[1]]
    snrs = [e[2] for e in ok] or [e[2] for e in ev]
    foffs = [e[3] for e in ok]
    # pertes groupées : au moins 2 trames fausses de suite
    seq = [e[1] for e in sorted(ev)]
    runs, cur = [], 0
    for s in seq:
        if not s:
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    return {"ok": len(ok), "bad": len(bad),
            "snr_med": float(np.median(snrs)) if snrs else None,
            "snr_min": float(np.min(snrs)) if snrs else None,
            "snr_max": float(np.max(snrs)) if snrs else None,
            "foff": float(np.median(foffs)) if foffs else None,
            "grouped": sum(r for r in runs if r >= 2), "isolated": sum(r for r in runs if r == 1)}


def diagnose(rep):
    """-> liste de (gravité, texte) ; gravité : ok / info / warn / bad."""
    out = []
    lv = rep["level"]
    if lv["clip"] > 0.001:
        out.append(("bad", f"Niveau d'entrée trop fort : {lv['clip'] * 100:.2f} % des échantillons sont écrêtés "
                           f"(crête {lv['peak_db']:.1f} dBFS). Baissez le volume d'entrée Windows ou le niveau "
                           f"USB/ACC de sortie du poste : l'écrêtage déforme le signal OFDM."))
    elif lv["peak_db"] > -1.0:
        out.append(("warn", f"Niveau d'entrée à la limite (crête {lv['peak_db']:.1f} dBFS). Gardez 6 dB de marge."))
    if lv["rms_db"] < -45:
        out.append(("warn", f"Niveau d'entrée très faible ({lv['rms_db']:.0f} dBFS en moyenne). Montez le volume "
                            f"d'entrée : le bruit de la carte son peut dominer."))
    elif not out:
        out.append(("ok", f"Niveau d'entrée correct ({lv['rms_db']:.0f} dBFS en moyenne, crête "
                          f"{lv['peak_db']:.1f} dBFS)."))
    for f, frac in rep["qrm"]:
        out.append(("warn", f"Brouillage étroit vers {f:.0f} Hz présent {frac * 100:.0f} % du temps "
                            f"(porteuse, CW ou RTTY)."))
    sums = {m: _summary(d["events"]) for m, d in rep["modes"].items()}
    rep["summary"] = sums
    data = [m for m in MODES if m != "DATAC0" and (sums[m]["ok"] + sums[m]["bad"]) > 0]
    if not data:
        pre = sum(rep["modes"][m]["pre"] for m in MODES)
        if pre:
            out.append(("bad", f"{pre} début(s) de trame détecté(s), mais aucune trame décodée : signal trop faible, "
                               f"trop brouillé, ou décalé en fréquence."))
        else:
            out.append(("bad", "Aucune trame HFImage reconnue dans cet enregistrement (pas de signal HFImage, "
                               "signal hors de la bande audio 300-2700 Hz, ou mauvais mode du poste)."))
        return out
    for m in data:
        s = sums[m]
        n = s["ok"] + s["bad"]
        loss = s["bad"] / n
        txt = (f"{m} : {s['ok']} trame(s) juste(s) sur {n} ({loss * 100:.0f} % perdues), SNR médian "
               f"{s['snr_med']:+.1f} dB (de {s['snr_min']:+.1f} à {s['snr_max']:+.1f}).")
        out.append(("ok" if loss < 0.1 else ("warn" if loss < 0.35 else "bad"), txt))
        if s["bad"] >= 2:
            if s["grouped"] > s["isolated"]:
                out.append(("info", f"{m} : les pertes arrivent par groupes ({s['grouped']} trames) : typique du QSB. "
                                    f"La robustesse « Forte » ou le mode Auto aident."))
            else:
                out.append(("info", f"{m} : pertes isolées ({s['isolated']} trames) : bruit ou brouillage bref."))
        if s["foff"] is not None and abs(s["foff"]) > 25:
            out.append(("warn", f"{m} : décalage de fréquence {s['foff']:+.0f} Hz entre les deux postes "
                                f"(vérifiez RIT/XIT, et que les deux sont en USB)."))
        raw = rep["modes"][m].get("raw_ok")
        if raw is not None and s["ok"] > raw:
            out.append(("info", f"{m} : le coupe-QRM a sauvé {s['ok'] - raw} trame(s) ({raw} sans lui)."))
        elif raw is not None and raw > s["ok"]:
            out.append(("warn", f"{m} : {raw} trames sans coupe-QRM contre {s['ok']} avec : essayez de le "
                                f"désactiver (Réglages → Audio) pour ce type de signal."))
    # conseil de mode : d'après les pertes réelles et la marge de SNR
    order = ["DATAC1X", "DATAC1", "DATAC3", "DATAC4"]
    if "DATAC13" in data:
        out.append(("info", "DATAC13 : annonce hybride éclair (l'image passe par Internet)."))
    data = [m for m in data if m in order]            # conseil de mode : modes d'image seulement
    if not data:
        return out
    best = max(data, key=lambda m: sums[m]["ok"] + sums[m]["bad"])
    s = sums[best]
    snr, loss = s["snr_med"], s["bad"] / max(1, s["ok"] + s["bad"])
    i = order.index(best) if best in order else 1
    if snr is not None:
        if loss > 0.35 and i < len(order) - 1:
            out.append(("info", f"Trop de pertes en {best} : essayez {order[i + 1]} (plus lent mais plus robuste)."))
        elif i > 0 and snr >= THR[order[i - 1]] + 2 and loss < 0.1:
            out.append(("info", f"Le lien a de la marge (SNR {snr:+.1f} dB) : {order[i - 1]} passerait aussi, "
                                f"pour des images plus nettes."))
        else:
            out.append(("ok", f"{best} est bien adapté à ce lien (SNR médian {snr:+.1f} dB, "
                              f"{loss * 100:.0f} % de pertes)."))
    return out


def report_text(rep, tr=lambda s: s):
    lv = rep["level"]
    lines = [tr("Analyse de") + f" {rep['path']}",
             tr(f"Durée {rep['duration']:.0f} s, {lv['fs']} Hz"), ""]
    for sev, t in rep["diag"]:
        mark = {"ok": "✓", "info": "•", "warn": "!", "bad": "✗"}[sev]
        lines.append(f"{mark} {tr(t)}")
    lines.append("")
    lines.append(tr("Trames (temps, mode, résultat, SNR, décalage) :"))
    ev = sorted((e[0], m, e[1], e[2], e[3]) for m, d in rep["modes"].items() for e in d["events"])
    for t, m, ok, snr, foff in ev[:400]:
        lines.append(f"  {int(t // 60):02d}:{t % 60:04.1f}  {m:8s} {'OK  ' if ok else tr('FAUX')}  "
                     f"{snr:+5.1f} dB  {foff:+5.0f} Hz")
    return "\n".join(lines)
