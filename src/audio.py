"""Audio carte son : rééchantillonnage 8 kHz <-> 48 kHz (numpy seul) et PTT CAT Kenwood."""
import re
import sys

import numpy as np

FS_MODEM = 8000
FS_CARD = 48000
RATIO = FS_CARD // FS_MODEM


def _lowpass(ntaps=121, cutoff=3600, fs=FS_CARD):
    n = np.arange(ntaps) - (ntaps - 1) / 2
    h = np.sinc(2 * cutoff / fs * n) * np.hamming(ntaps)
    return h / h.sum()


_H = _lowpass()


def upsample(x8k: np.ndarray) -> np.ndarray:
    """int16 8 kHz -> float32 48 kHz (-1..1)."""
    up = np.zeros(len(x8k) * RATIO)
    up[::RATIO] = x8k.astype(np.float64) / 32768.0 * RATIO
    return np.convolve(up, _H, mode="same").astype(np.float32)


class Downsampler:
    """float32 48 kHz -> int16 8 kHz, en flux (garde l'historique du filtre)."""

    def __init__(self):
        self.hist = np.zeros(len(_H) - 1)
        self.phase = 0

    def process(self, x48: np.ndarray) -> np.ndarray:
        x = np.concatenate([self.hist, x48.astype(np.float64)])
        y = np.convolve(x, _H, mode="valid")
        self.hist = x[-(len(_H) - 1):]
        out = y[self.phase::RATIO]
        self.phase = (self.phase - len(y)) % RATIO
        return np.clip(out * 32768.0, -32767, 32767).astype(np.int16)


class LinearResampler:
    """Rééchantillonnage linéaire en flux (ex. 44,1 kHz <-> 48 kHz). Suffisant ici :
    le signal utile est sous 3 kHz, très loin de la fréquence de Nyquist."""

    def __init__(self, fs_in, fs_out):
        self.step = fs_in / fs_out
        self.pos = 1.0          # position du prochain échantillon de sortie (buf[0] = bloc précédent)
        self.last = 0.0         # dernier échantillon du bloc précédent

    def process(self, x: np.ndarray) -> np.ndarray:
        if self.step == 1.0:
            return x.astype(np.float32)
        buf = np.concatenate([[self.last], x.astype(np.float64)])
        n_out = int(np.floor((len(buf) - 1 - self.pos) / self.step)) + 1
        if n_out <= 0:
            self.pos -= len(x)
            self.last = buf[-1]
            return np.zeros(0, np.float32)
        t = self.pos + np.arange(n_out) * self.step
        y = np.interp(t, np.arange(len(buf)), buf)
        self.pos = t[-1] + self.step - len(x)
        self.last = buf[-1]
        return y.astype(np.float32)


def pick_rate(sd, device, output=True):
    """Fréquence acceptée par le périphérique : 48 kHz si possible, sinon sa
    fréquence par défaut, sinon 44,1 kHz. Retourne (fs, canaux)."""
    info = sd.query_devices(device)
    maxch = info["max_output_channels" if output else "max_input_channels"]
    check = sd.check_output_settings if output else sd.check_input_settings
    rates = [48000, int(info["default_samplerate"]), 44100, 96000]
    chans = [1, 2] if maxch >= 2 else [1]
    if output:
        chans = [min(2, maxch)] + [c for c in (1,) if c != min(2, maxch)]
    last_err = None
    for fs in dict.fromkeys(rates):
        for ch in chans:
            try:
                check(device=device, samplerate=fs, channels=ch, dtype="float32")
                return fs, ch
            except Exception as e:      # noqa: PERF203
                last_err = e
    raise RuntimeError(f"aucun format audio accepté par ce périphérique ({last_err})")


def tone(seconds=2.0, freq=1000.0, fs=FS_CARD, amp=0.3):
    t = np.arange(int(seconds * fs)) / fs
    env = np.minimum(1, np.minimum(t, t[::-1]) / 0.02)   # rampes de 20 ms
    return (amp * env * np.sin(2 * np.pi * freq * t)).astype(np.float32)


class PlaybackError(RuntimeError):
    pass


LEAD_IN_S = 0.6


API_PREF = ("MME", "Windows WASAPI", "Windows DirectSound")


# entrées virtuelles de Windows (« périphérique par défaut ») : doublons d'un vrai appareil
_VIRTUAL = ("sound mapper", "mappeur de sons", "primary sound", "pilote de son principal",
            "pilote de capture audio principal", "périphérique audio principal")


def _same_device(full: str, other: str) -> bool:
    """Même appareil vu par deux interfaces : les noms MME sont tronqués à 31 caractères."""
    a, b = full.strip().lower(), other.strip().lower()
    if a == b:
        return True
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    # nom tronqué par MME (31 caractères, parfois avec une espace finale retirée ici)
    return len(short) >= 25 and long_.startswith(short)


def unique_devices(sd, output=True):
    """Un seul choix par appareil réel : [(index, nom complet, interface)].
    Windows présente chaque carte son plusieurs fois (MME, DirectSound, WASAPI, WDM-KS) ;
    on garde l'interface préférée (API_PREF) et le nom le plus complet. Si cette interface
    échoue, la lecture / l'enregistrement essaient déjà les autres (same_device_other_apis)."""
    devs = sd.query_devices()
    apis = sd.query_hostapis()
    key = "max_output_channels" if output else "max_input_channels"
    groups = []                                  # [{"name": nom le plus long, "members": [(rang, i, api)]}]
    for i, d in enumerate(devs):
        if d[key] <= 0:
            continue
        api = apis[d["hostapi"]]["name"]
        if api == "Windows WDM-KS":              # souvent muet ou exclusif
            continue
        name = str(d["name"]).strip()
        if any(v in name.lower() for v in _VIRTUAL):
            continue
        rank = API_PREF.index(api) if api in API_PREF else len(API_PREF)
        for g in groups:
            if _same_device(g["name"], name):
                g["members"].append((rank, i, api))
                if len(name) > len(g["name"]):
                    g["name"] = name
                break
        else:
            groups.append({"name": name, "members": [(rank, i, api)]})
    out = []
    for g in groups:
        rank, i, api = min(g["members"])
        out.append((i, g["name"], api))
    return sorted(out, key=lambda t: t[1].lower())


def device_label(sd, i):
    d = sd.query_devices(i)
    return f"{d['name']} [{sd.query_hostapis(d['hostapi'])['name']}]"


def same_device_other_apis(sd, device, output=True):
    """Le même périphérique vu par les autres interfaces Windows (MME, WASAPI,
    DirectSound), dans l'ordre de préférence. Les noms MME sont tronqués à
    31 caractères : on compare sur ce préfixe."""
    devs = sd.query_devices()
    apis = sd.query_hostapis()
    key = "max_output_channels" if output else "max_input_channels"
    name = devs[device]["name"][:31].lower()
    out = []
    for i, d in enumerate(devs):
        if i == device or d[key] == 0:
            continue
        api = apis[d["hostapi"]]["name"]
        if api not in API_PREF:
            continue
        n = d["name"].lower()
        if n[:31] == name or n.startswith(name) or name.startswith(n[:31]):
            out.append((API_PREF.index(api), i))
    return [i for _, i in sorted(out)]


class Upsampler:
    """int16 8 kHz -> float32 48 kHz, en flux (filtre avec historique)."""

    def __init__(self):
        self.hist = np.zeros(len(_H) - 1)

    def process(self, x8k: np.ndarray) -> np.ndarray:
        up = np.zeros(len(x8k) * RATIO)
        up[::RATIO] = x8k.astype(np.float64) / 32768.0 * RATIO
        x = np.concatenate([self.hist, up])
        self.hist = x[-(len(_H) - 1):]
        return np.convolve(x, _H, mode="valid").astype(np.float32)


def _play_core(sd, device, chunks48, stop_event=None, progress=None, log=None, peak=None):
    """Lecture en flux, mode « callback » (l'écriture bloquante de PortAudio ne joue
    rien en DirectSound). Un fil prépare le son morceau par morceau (quelques
    secondes d'avance), la carte son le consomme : rien n'est fabriqué en entier,
    même pour une émission d'une heure. S'adapte au format accepté (48/44,1 kHz,
    mono/stéréo) et vérifie que le son a vraiment été joué (PlaybackError sinon).
    progress(secondes_jouées) est appelé régulièrement."""
    import collections
    import threading
    import time
    fs, ch = pick_rate(sd, device, output=True)
    rs = LinearResampler(FS_CARD, fs)
    buf = collections.deque()
    st = {"have": 0, "done": False, "pos": 0, "under": 0, "total": 0, "err": None}
    lock = threading.Lock()
    room = threading.Condition(lock)
    ahead = fs * 4                                   # 4 s d'avance au plus

    def producer():
        try:
            # Les cartes son perdent souvent le début d'un flux qui démarre (0,3 à
            # 0,5 s mesurés) : on commence par du silence.
            seq = [np.zeros(int(FS_CARD * LEAD_IN_S), np.float32)]
            for x in _chain(seq, chunks48, [np.zeros(int(FS_CARD * 0.4), np.float32)]):
                y = rs.process(x)
                with room:
                    while st["have"] > ahead and not (stop_event is not None and stop_event.is_set()):
                        room.wait(0.2)
                    if stop_event is not None and stop_event.is_set():
                        break
                    buf.append(y)
                    st["have"] += len(y)
                    st["total"] += len(y)
        except Exception as e:                       # erreur dans la préparation du son
            st["err"] = e
        finally:
            with room:
                st["done"] = True
                room.notify_all()

    def cb(outdata, frames, t, status):
        if status.output_underflow:
            st["under"] += 1
        n = 0
        with lock:
            while n < frames and buf:
                b = buf[0]
                k = min(frames - n, len(b))
                outdata[n:n + k, :] = b[:k, None]
                if k == len(b):
                    buf.popleft()
                else:
                    buf[0] = b[k:]
                n += k
            st["have"] -= n
            st["pos"] += n
            finished = st["done"] and not buf
            room.notify_all()
        if n < frames:
            outdata[n:] = 0
            if finished:
                raise sd.CallbackStop
            st["under"] += 1

    threading.Thread(target=producer, daemon=True).start()
    with lock:                                       # pré-remplissage : 1 s d'avance
        while st["have"] < fs and not st["done"]:
            room.wait(0.1)
    if st["err"]:
        raise st["err"]
    if log:
        lvl = f", crête {20 * np.log10(max(1e-9, peak)):.0f} dBFS" if peak else ""
        log(f"Sortie : {device_label(sd, device)}, {fs} Hz, {ch} voie(s){lvl}")
    done = threading.Event()
    stream = sd.OutputStream(device=device, samplerate=fs, channels=ch, dtype="float32",
                             latency="high", callback=cb, finished_callback=done.set)
    t0 = time.time()
    with stream:
        while not done.wait(0.1):
            if stop_event is not None and stop_event.is_set():
                stream.abort()
                with room:
                    room.notify_all()
                return False
            if progress:
                progress(max(0.0, st["pos"] / fs - LEAD_IN_S))
            if st["done"] and time.time() - t0 > st["total"] / fs + 10:
                stream.abort()
                raise PlaybackError("la carte son ne consomme pas les données (bloquée)")
    if st["err"]:
        raise st["err"]
    elapsed, dur = time.time() - t0, st["total"] / fs
    if elapsed < 0.5 * dur:
        raise PlaybackError(f"lecture terminée en {elapsed:.1f} s au lieu de {dur:.1f} s : "
                            "aucun son n'a réellement été joué")
    if st["under"] > 0 and log:
        log(f"Attention : {st['under']} trou(s) dans le flux audio (ordinateur trop chargé ?)")
    return True


def _chain(*iterables):
    for it in iterables:
        yield from it


def play(sd, device, sig48, stop_event=None, progress=None, log=None):
    """Joue un signal mono 48 kHz déjà prêt (ex. tonalité de test)."""
    peak = float(np.abs(sig48).max()) if len(sig48) else None
    step = FS_CARD // 5
    chunks = (sig48[i:i + step] for i in range(0, len(sig48), step))
    return _play_core(sd, device, chunks, stop_event, progress, log, peak)


def play_8k(sd, device, chunks8k, level=0.5, stop_event=None, progress=None, log=None,
            on_chunk=None):
    """Joue un flux de morceaux int16 8 kHz (sortie du modem), au niveau `level`.
    on_chunk(morceau) est appelé dans l'ordre (ex. pour le waterfall)."""
    up = Upsampler()

    def gen():
        for c in chunks8k:
            if on_chunk:
                on_chunk(c)
            yield up.process(c) * level

    return _play_core(sd, device, gen(), stop_event, progress, log, peak=0.5 * level)


def _registry_ports():
    """Windows : ports série actifs d'après le registre (HARDWARE\\DEVICEMAP\\SERIALCOMM).
    C'est la liste qu'utilisent la plupart des logiciels radio ; elle contient des ports que
    pyserial ne voit pas avec certains pilotes (Prolific, CH340, convertisseurs USB d'anciens
    modèles, ports virtuels…)."""
    if not sys.platform.startswith("win"):
        return []
    out = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DEVICEMAP\SERIALCOMM") as k:
            i = 0
            while True:
                try:
                    name, val, _ = winreg.EnumValue(k, i)
                except OSError:
                    break
                i += 1
                if isinstance(val, str) and val.upper().startswith("COM"):
                    out.append((val.strip(), name.rsplit("\\", 1)[-1]))
    except OSError:
        pass
    return out


def _port_key(p):
    m = re.match(r"COM(\d+)$", p.upper())
    return (0, int(m.group(1)), "") if m else (1, 0, p)


def ports_list():
    """Ports série -> [(port, description)], sans doublons, COM1, COM2… dans l'ordre."""
    found = {}
    try:
        from serial.tools import list_ports
        for p in list_ports.comports():
            found[p.device.upper() if p.device.upper().startswith("COM") else p.device] = p.description
    except Exception:
        pass
    for dev, desc in _registry_ports():
        found.setdefault(dev.upper(), desc)
    return [(d, found[d]) for d in sorted(found, key=_port_key)]


KENWOOD_IDS = {"022": "TS-990S", "024": "TS-890S", "019": "TS-2000", "021": "TS-590S",
               "023": "TS-590SG"}
# codes de mode Kenwood (OM / SF), cf. Hamlib
KENWOOD_MODES = {"1": "LSB", "2": "USB", "3": "CW", "4": "FM", "5": "AM", "6": "FSK",
                 "7": "CW-R", "9": "FSK-R", "A": "PSK", "B": "PSK-R",
                 "C": "LSB-DATA1", "D": "USB-DATA1", "E": "FM-DATA1", "F": "AM-DATA1",
                 "G": "LSB-DATA2", "H": "USB-DATA2", "I": "FM-DATA2", "J": "AM-DATA2",
                 "K": "LSB-DATA3", "L": "USB-DATA3", "M": "FM-DATA3", "N": "AM-DATA3"}


def open_serial(port, baud, dtr=None, rts=None):
    """Ouvre le port série avec un message clair en cas d'échec.
    dtr / rts : état des lignes dès l'ouverture (None : comme d'habitude, hautes)."""
    import serial
    if not port:
        raise RuntimeError("aucun port COM choisi (onglet Réglages)")
    try:
        ser = serial.Serial(None, baud, timeout=0.5, write_timeout=1)
        ser.port = port
        if dtr is not None:
            ser.dtr = bool(dtr)
        if rts is not None:
            ser.rts = bool(rts)
        ser.open()
        return ser
    except serial.SerialException as e:
        msg = str(e)
        if not sys.platform.startswith("win") and ("Permission denied" in msg or "Errno 13" in msg):
            raise RuntimeError(
                f"{port} : accès refusé. Sous Linux, ajoutez votre compte au groupe « dialout » "
                "(sudo usermod -aG dialout $USER), puis fermez la session et reconnectez-vous.") from e
        if ("Access is denied" in msg or "Accès refusé" in msg or "PermissionError" in msg
                or "Errno 13" in msg or "(13," in msg):
            raise RuntimeError(
                f"{port} est déjà utilisé par un autre programme (ARCP, RS-BA1, logger, WSJT-X…). "
                "Fermez-le, ou utilisez l'autre port COM virtuel du poste (les TS-890/990, IC-7610, "
                "IC-7300MK2… en créent deux).") from e
        if "FileNotFoundError" in msg or "cannot find" in msg.lower() or "introuvable" in msg.lower():
            raise RuntimeError(f"{port} n'existe pas (poste éteint, câble USB débranché ?)") from e
        raise RuntimeError(f"impossible d'ouvrir {port} : {msg}") from e


def _query(ser, cmd, timeout=0.6):
    import time
    ser.reset_input_buffer()
    ser.write(cmd.encode())
    t0, buf = time.time(), b""
    want = cmd[:2].encode()
    while time.time() - t0 < timeout:
        buf += ser.read(ser.in_waiting or 1)
        if buf.endswith(b";"):
            # poste en « AI » (informations automatiques) : il envoie aussi des messages qu'on
            # n'a pas demandés (RX0;, FA…;) -> on garde la réponse à notre commande
            parts = buf.split(b";")[:-1]
            for p in parts:
                if p.startswith(want) or p == b"?":
                    return (p + b";").decode(errors="replace")
    msgs = [p for p in buf.split(b";") if p]
    return (msgs[-1] + b";").decode(errors="replace") if msgs and buf.endswith(b";") else buf.decode(errors="replace")


def _mode_of(model, q):
    """Lit le mode du poste (TS-890 : SF0 ; TS-990 et autres : OM0)."""
    if model == "TS-890S":
        r = q("SF0;")
        code = r[14:15] if r.startswith("SF0") and len(r) >= 16 else ""
    else:
        r = q("OM0;")
        code = r[3:4] if r.startswith("OM0") else ""
    return KENWOOD_MODES.get(code), r


class Rig:
    """Liaison CAT unique avec le poste : lecture fréquence / mode et PTT par le même
    port (un seul programme peut ouvrir un port COM)."""

    def __init__(self, port, baud):
        import threading
        self.port, self.baud = port, baud
        self.ser = open_serial(port, baud)
        self.lock = threading.Lock()
        self.model = None
        rid = self.query("ID;")
        if rid.startswith("ID"):
            self.model = KENWOOD_IDS.get(rid[2:5], f"ID {rid[2:-1]}")

    def query(self, cmd, timeout=0.6):
        with self.lock:
            return _query(self.ser, cmd, timeout)

    def write(self, cmd):
        with self.lock:
            self.ser.write(cmd.encode())

    def freq(self):
        """Fréquence du VFO A en Hz, ou None."""
        r = self.query("FA;")
        if r.startswith("FA") and r.endswith(";") and r[2:-1].isdigit():
            return int(r[2:-1])
        return None

    def mode(self):
        return _mode_of(self.model, self.query)[0]

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass


def format_freq(hz, short=False):
    """14233000 -> « 14.233.000 » (ou « 14.233 MHz » si short)."""
    if not hz:
        return ""
    if short:
        return f"{hz / 1e6:.3f} MHz"
    s = f"{hz:,}".replace(",", ".")
    return s


def band_of(hz):
    bands = [(1.8, 2.0, "160 m"), (3.5, 3.8, "80 m"), (5.35, 5.37, "60 m"), (7.0, 7.2, "40 m"),
             (10.1, 10.15, "30 m"), (14.0, 14.35, "20 m"), (18.068, 18.168, "17 m"),
             (21.0, 21.45, "15 m"), (24.89, 24.99, "12 m"), (28.0, 29.7, "10 m"), (50.0, 52.0, "6 m")]
    mhz = (hz or 0) / 1e6
    for lo, hi, name in bands:
        if lo <= mhz <= hi:
            return name
    return ""


def rig_check(port, baud, rig=None):
    """Interroge le poste : modèle et mode. Retourne (texte, mode_data_ok ou None).
    Utilise la liaison déjà ouverte (`rig`) si elle existe."""
    own = rig is None
    if own:
        ser = open_serial(port, baud)
        q = lambda c: _query(ser, c)
    else:
        q = rig.query
    try:
        rid = q("ID;")
        if not rid.startswith("ID"):
            return (f"Pas de réponse du poste sur {port} à {baud} bauds "
                    f"(vérifiez la vitesse, menu 7-01/7-02).", None)
        model = KENWOOD_IDS.get(rid[2:5], f"ID {rid[2:-1]}")
        mode, r = _mode_of(model, q)
        fa = q("FA;")
        f = int(fa[2:-1]) if fa.startswith("FA") and fa[2:-1].isdigit() else None
        where = f" sur {format_freq(f, True)}" if f else ""
        if mode is None:
            return f"{model} détecté sur {port}{where} (mode non lu : {r!r})", None
        ok = "DATA" in mode
        txt = f"{model} détecté sur {port}{where}, mode {mode}"
        if not ok:
            txt += (" — ATTENTION : le poste n'est pas en mode DATA. Avec TX1; l'audio USB "
                    "n'est émis qu'en mode DATA : appuyez sur DATA pour passer en USB-DATA.")
        return txt, ok
    finally:
        if own:
            ser.close()


def rig_set_data(port, baud, rig=None):
    """Passe le poste en USB-DATA (DATA1) par CAT, puis relit le mode pour vérifier.
    -> (texte, ok). TS-990 : mode USB-D1 direct ; TS-890 et autres : USB puis DATA."""
    import time as _t
    own = rig is None
    if own:
        ser = open_serial(port, baud)
        q = lambda c: _query(ser, c)
        w = lambda c: ser.write(c.encode())
    else:
        q, w = rig.query, rig.write
    try:
        rid = q("ID;")
        if not rid.startswith("ID"):
            return f"Pas de réponse du poste sur {port}.", False
        model = KENWOOD_IDS.get(rid[2:5], f"ID {rid[2:-1]}")
        if model == "TS-990S":
            cmds = ["OM0D;"]                         # USB-DATA1 en une commande
        elif model == "TS-890S":
            cmds = ["OM02;", "DA1;"]                 # USB, puis DATA1
        else:
            cmds = ["MD2;", "DA1;"]                  # TS-590 / TS-480… : USB, puis DATA
        for c in cmds:
            w(c)
            _t.sleep(0.15)
        _t.sleep(0.3)
        mode, r = _mode_of(model, q)
        ok = bool(mode) and "DATA" in mode
        if ok:
            return f"{model} passé en {mode} par CAT.", True
        return (f"{model} : le passage en USB-DATA par CAT n'a pas pris (mode lu : {mode or r!r}). "
                f"Appuyez sur DATA sur le poste."), False
    finally:
        if own:
            ser.close()


class PTT:
    """Commande d'émission : CAT Kenwood (« TX1; » = DATA SEND, audio USB/arrière ;
    « RX; » au retour), ou ligne RTS / DTR du port série, ou rien (VOX)."""

    def __init__(self, method, port=None, baud=115200, tx_cmd="TX1;", rig=None):
        self.method = method
        self.tx_cmd = tx_cmd
        self.rig = rig if (rig is not None and rig.port == port) else None
        self.own = self.rig is None and method in ("CAT", "RTS", "DTR")
        if self.rig is not None:
            self.ser = self.rig.ser
        else:
            self.ser = open_serial(port, baud) if self.own else None
        if self.ser is not None and method in ("RTS", "DTR"):
            self.ser.rts = False
            self.ser.dtr = False

    def _w(self, cmd):
        if self.rig is not None:
            self.rig.write(cmd)
        else:
            self.ser.write(cmd.encode())

    def tx(self):
        if self.method == "CAT":
            self._w(self.tx_cmd)
        elif self.method == "RTS":
            self.ser.rts = True
        elif self.method == "DTR":
            self.ser.dtr = True

    def rx(self):
        if self.method == "CAT":
            self._w("RX;")
        elif self.method == "RTS":
            self.ser.rts = False
        elif self.method == "DTR":
            self.ser.dtr = False

    def close(self):
        if self.ser is None:
            return
        try:
            self.rx()
        finally:
            if self.own:
                self.ser.close()
