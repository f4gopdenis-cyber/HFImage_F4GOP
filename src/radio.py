"""Commande du poste (CAT) et PTT, façon WSJT-X.

Pilotes :
- « kenwood »   : Kenwood en direct (TS-990S, TS-890S, TS-590S/SG, TS-2000, TS-480…), sans rien installer
- « hamlib »    : tous les postes connus de Hamlib (Icom, Yaesu, Elecraft, Xiegu, Flex…). HFImage lance
                  rigctld (Hamlib) en arrière-plan ; Hamlib est téléchargé une fois depuis GitHub si besoin
- « netrigctl » : un serveur Hamlib rigctld déjà lancé (hôte:port)
- « flrig »     : FLRig (XML-RPC, hôte:port)
- « omnirig »   : OmniRig (Rig 1 / Rig 2), s'il est installé sur le PC
- « none »      : pas de CAT (PTT par VOX, ou RTS / DTR d'une interface)

PTT : VOX, CAT, DTR ou RTS — DTR / RTS sur le port CAT ou sur un autre port (interface à côté).
"""
import hashlib
import os
import socket
import subprocess
import sys
import threading
import time
import zipfile

import audio
from riglist import HAMLIB_VERSION, RIGS

# ------------------------------------------------------------------ liste des postes
# clé enregistrée dans la configuration -> libellé (en français, traduit à l'affichage)
SPECIAL = [("none", "Aucun (pas de CAT)"), ("kenwood", "Kenwood (détection automatique)"),
           ("omnirig1", "OmniRig Rig 1"), ("omnirig2", "OmniRig Rig 2"),
           ("flrig", "FLRig"), ("netrigctl", "Hamlib NET rigctl"),
           ("custom", "Commandes CAT personnalisées (comme EasyPal)"),
           ("tci", "SunSDR / ExpertSDR (TCI)")]
if not sys.platform.startswith("win"):
    SPECIAL = [s for s in SPECIAL if not s[0].startswith("omnirig")]      # OmniRig : Windows seulement
# Kenwood pilotés en direct (commandes ASCII éprouvées) ; les autres passent par Hamlib
KENWOOD_NATIVE = {"TS-990S", "TS-890S", "TS-590S", "TS-590SG", "TS-2000", "TS-480"}
# noms de fabricants écrits de deux façons dans Hamlib -> un seul groupe dans la liste
MFG_FIX = {"Rhode&Schwarz": "Rohde&Schwarz", "N2ADR James Ahlstrom": "N2ADR"}
_BY_ID = {num: (MFG_FIX.get(mfg, mfg), mod) for num, mfg, mod, _ in RIGS}


def _natural(text):
    """Tri naturel : « TS-480 » < « TS-890S » < « TS-990S » < « TS-2000 », « IC-705 » < « IC-7300 »."""
    import re
    return [(0, int(t), "") if t.isdigit() else (1, 0, t.lower()) for t in re.findall(r"\d+|\D+", text)]


def rig_keys():
    """Toutes les clés : entrées spéciales puis les postes Hamlib (« hamlib:2039 »), rangés par
    fabricant (ordre alphabétique) puis par modèle (ordre naturel)."""
    order = sorted(_BY_ID, key=lambda n: (_BY_ID[n][0].lower(), _natural(_BY_ID[n][1]), n))
    return [k for k, _ in SPECIAL] + [f"hamlib:{num}" for num in order]


# postes pilotés par la même entrée Hamlib que leur version de base : noms affichés ensemble
# (« 991A » trouve alors le FT-991 dans la recherche, comme dans WSJT-X où il n'y a que le FT-991)
MODEL_ALSO = {1035: "FT-991 / FT-991A", 1022: "FT-857 / FT-857D", 1023: "FT-897 / FT-897D",
              1020: "FT-817 / FT-817ND", 1037: "FTDX-3000 / FTDX-3000D", 1029: "FT-2000 / FT-2000D",
              1036: "FT-891 / FT-891D"}


def rig_label(key):
    for k, n in SPECIAL:
        if k == key:
            return n
    if key.startswith("hamlib:"):
        try:
            num = int(key[7:])
            mfg, mod = _BY_ID[num]
            return f"{mfg} {MODEL_ALSO.get(num, mod)}"
        except (KeyError, ValueError):
            pass
    return key


def rig_entry(key):
    """Clé -> {kind, model_id, label}."""
    label = rig_label(key)
    if key.startswith("omnirig"):
        return {"kind": "omnirig", "rig_no": 2 if key.endswith("2") else 1, "model_id": None, "label": label}
    if key in ("none", "kenwood", "flrig", "netrigctl", "custom", "tci"):
        return {"kind": key, "model_id": None, "label": label}
    if key.startswith("hamlib:"):
        try:
            num = int(key[7:])
            mfg, mod = _BY_ID[num]
        except (KeyError, ValueError):
            return {"kind": "none", "model_id": None, "label": label}
        kind = "kenwood" if mfg == "Kenwood" and mod in KENWOOD_NATIVE else "hamlib"
        return {"kind": kind, "model_id": num, "label": label, "model": mod}
    return {"kind": "none", "model_id": None, "label": label}


DEFAULTS = {"rig": "none", "port": "", "baud": 115200, "data_bits": "default", "stop_bits": "default",
            "handshake": "default", "dtr": "", "rts": "", "ptt": "VOX", "ptt_port": "",
            "tx_audio": "rear", "set_mode": "none", "host": "", "poll": 1,
            # « Commandes CAT personnalisées » (comme EasyPal) : hexadécimal ou texte
            "cmd_init1": "", "cmd_init2": "", "cmd_ptt_on": "", "cmd_ptt_off": "",
            "cmd_exit1": "", "cmd_exit2": "", "cmd_delay": 200,
            # chaînes de départ / sortie : « tx » à chaque émission (comme EasyPal), « open » au
            # lancement et à la fermeture du programme
            "cmd_when": "tx",
            # Icom : adresse CI-V (hexadécimal, « 94 », « B6 »…), vide = celle du modèle
            "civ": "",
            # 1.65 : partage du poste avec d'autres logiciels (WSJT-X, logger…) par Hamlib NET rigctl
            "share": False, "share_port": 4532}
CUSTOM_KEYS = ("cmd_init1", "cmd_init2", "cmd_ptt_on", "cmd_ptt_off", "cmd_exit1", "cmd_exit2")


def from_conf(conf):
    """Réglages du poste depuis la configuration (avec reprise des réglages des anciennes versions)."""
    r = dict(DEFAULTS)
    r.update(conf.get("radio") or {})
    if "radio" not in conf:                               # versions ≤ 0.20 : Kenwood seulement
        r["port"] = conf.get("cat_port", "") or ""
        r["baud"] = int(conf.get("cat_baud", 115200) or 115200)
        r["ptt"] = conf.get("ptt", "VOX")
        r["tx_audio"] = "front" if str(conf.get("cat_cmd", "TX1;")).startswith("TX0") else "rear"
        if r["port"] and (r["ptt"] == "CAT" or conf.get("cat_freq", True)):
            r["rig"] = "kenwood"
        if r["ptt"] in ("RTS", "DTR") and r["rig"] == "kenwood":
            r["ptt_port"] = r["port"]
    if r["ptt"] not in ("VOX", "CAT", "DTR", "RTS"):
        r["ptt"] = "VOX"
    return r


def cat_signature(cfg):
    """Ce qui oblige à rouvrir la liaison CAT quand ça change."""
    keys = ("rig", "port", "baud", "data_bits", "stop_bits", "handshake", "dtr", "rts", "host", "civ",
            "ptt", "ptt_port", "share", "share_port") + CUSTOM_KEYS
    # (PTT : DTR / RTS du port CAT confié à rigctld, ou ligne gardée basse à l'ouverture du port)
    return tuple(str(cfg.get(k)) for k in keys)


def can_share(cfg):
    """Le poste peut-il être partagé (rigctld de HFImage ouvert aux autres logiciels) ?
    Postes Hamlib, et Kenwood pilotés en direct dont le modèle est connu (ils passent alors par Hamlib)."""
    e = rig_entry(cfg["rig"])
    return e["kind"] == "hamlib" or (e["kind"] == "kenwood" and e.get("model_id") is not None)


def effective(cfg):
    """rig_entry, en tenant compte du partage (Kenwood en direct -> Hamlib quand on partage)."""
    e = dict(rig_entry(cfg["rig"]))
    if cfg.get("share") and e["kind"] == "kenwood" and e.get("model_id") is not None:
        e["kind"] = "hamlib"
    return e


def share_port(cfg):
    try:
        p = int(cfg.get("share_port") or 4532)
    except (TypeError, ValueError):
        p = 4532
    return p if 1024 <= p <= 65535 else 4532


def describe(cfg):
    """Résumé d'une ligne (Réglages)."""
    e = rig_entry(cfg["rig"])
    parts = [e["label"]]
    if e["kind"] in ("kenwood", "hamlib", "custom") and cfg.get("port"):
        parts.append(f"{cfg['port']} {cfg['baud']} bauds")
    if e["kind"] in ("netrigctl", "flrig", "tci"):
        parts.append(cfg.get("host") or {"netrigctl": "127.0.0.1:4532", "flrig": "127.0.0.1:12345",
                                          "tci": "127.0.0.1:40001"}[e["kind"]])
    p = cfg["ptt"]
    if p in ("DTR", "RTS"):
        p += f" {cfg.get('ptt_port') or cfg.get('port') or '?'}"
    elif p == "CAT":
        p += " (" + ("arrière / data" if cfg["tx_audio"] == "rear" else "avant / micro") + ")"
    parts.append("PTT " + p)
    if cfg.get("share") and can_share(cfg):
        parts.append(f"partagé sur 127.0.0.1:{share_port(cfg)}")
    return " — ".join(parts)


# ------------------------------------------------------------------ port série
def open_port(cfg, port=None):
    """Ouvre un port série avec tous les paramètres choisis (comme WSJT-X)."""
    import serial
    port = port or cfg.get("port")
    hs = cfg.get("handshake")
    lines = {}
    for line in ("dtr", "rts"):
        v = cfg.get(line)
        if v in ("high", "low") and not (line == "rts" and hs == "hardware"):
            lines[line] = v == "high"
    # PTT par DTR / RTS sur ce même port : la ligne reste basse dès l'ouverture (sinon le poste
    # passerait en émission au lancement du programme)
    pl = ptt_line_on(cfg, port)
    if pl:
        lines[pl] = False
    ser = audio.open_serial(port, int(cfg.get("baud") or 9600), **lines)
    try:
        db = cfg.get("data_bits")
        if str(db) in ("7", "8"):
            ser.bytesize = serial.SEVENBITS if str(db) == "7" else serial.EIGHTBITS
        sb = cfg.get("stop_bits")
        if str(sb) in ("1", "2"):
            ser.stopbits = serial.STOPBITS_ONE if str(sb) == "1" else serial.STOPBITS_TWO
        hs = cfg.get("handshake")
        if hs == "none":
            ser.xonxoff = ser.rtscts = False
        elif hs == "xonxoff":
            ser.xonxoff, ser.rtscts = True, False
        elif hs == "hardware":
            ser.xonxoff, ser.rtscts = False, True
        for line, on in lines.items():
            setattr(ser, line, on)
    except Exception:
        ser.close()
        raise
    return ser


def ptt_line_on(cfg, port):
    """« dtr » / « rts » si le PTT passe par cette ligne du port `port`, sinon None."""
    if cfg.get("ptt") in ("DTR", "RTS") and port and (cfg.get("ptt_port") or cfg.get("port")) == port:
        return cfg["ptt"].lower()
    return None


def civ_addr(cfg):
    """Adresse CI-V choisie (« 94 », « B6h », « 0xB6 »…) -> entier, ou None (celle du modèle)."""
    t = str(cfg.get("civ") or "").strip().upper().replace("0X", "").rstrip("H").strip()
    try:
        v = int(t, 16) if t else None
    except ValueError:
        return None
    return v if v is not None and 0 < v < 0xE0 else None


# ------------------------------------------------------------------ pilotes
class RigBase:
    kind = "none"
    model = ""
    port = None

    def freq(self):
        return None

    def mode(self):
        return None

    def ptt(self, on, rear=True):
        """rear : audio d'émission par l'arrière / data (sinon avant / micro)."""
        raise RuntimeError("ce pilote ne commande pas le PTT")

    def set_mode(self, which):
        """which : « usb » ou « data ». -> (ok, texte)."""
        return False, "changement de mode non pris en charge"

    @staticmethod
    def is_data(mode):
        m = (mode or "").upper()
        return "DATA" in m or m.startswith("PKT") or "DIG" in m or m.endswith("-D") or "-D1" in m

    @staticmethod
    def is_lsb(mode):
        """Bande latérale inférieure (LSB, LSB-DATA, PKTLSB, DIG-L…) ?"""
        m = (mode or "").upper().replace(" ", "")
        return "LSB" in m or m in ("DIG-L", "DIGL", "PKT-L", "DATA-L", "D-L")

    def before_tx(self):
        """Juste avant de passer en émission (quelle que soit la méthode PTT)."""

    def after_tx(self):
        """Juste après le retour en réception."""

    def set_freq(self, hz):
        """Change la fréquence du poste (Hz)."""
        raise RuntimeError("ce pilote ne change pas la fréquence")

    def set_sideband(self, side):
        """« LSB » ou « USB » (sans DATA)."""
        raise RuntimeError("ce pilote ne change pas la bande latérale")

    def set_voice(self, side):
        """Retour en phonie : « LSB » ou « USB » sans DATA (après une émission en « DATA auto »)."""
        self.set_sideband(side)

    def qsy(self, hz, side=None):
        """Va sur la fréquence `hz`. side (« LSB » / « USB ») : bande latérale voulue sur cette
        fréquence ; si le poste était en DATA, il y reste (LSB-DATA / USB-DATA). -> texte."""
        hz = int(hz)
        was = self.mode() or ""
        self.set_freq(hz)
        time.sleep(0.3)
        msg = ""
        if side and (self.is_lsb(self.mode()) != (side == "LSB")):
            data = self.is_data(was)
            self.set_sideband(side)
            time.sleep(0.3)
            if data:
                self.set_mode("data")
            msg = f", {self.mode() or side}"
        got = self.freq()
        if got and abs(got - hz) > 100:
            raise RuntimeError(f"le poste est resté sur {got / 1e6:.3f} MHz")
        return f"{self.model or 'poste'} : {hz / 1e6:.3f} MHz{msg}"

    def _side(self):
        """Bande latérale actuelle du poste : « LSB » ou « USB » (USB si inconnue)."""
        try:
            return "LSB" if self.is_lsb(self.mode()) else "USB"
        except Exception:
            return "USB"

    def close(self):
        pass


def parse_cmds(text):
    """Commandes écrites à la main -> liste d'octets à envoyer l'une après l'autre ([] si vide).
    - hexadécimal (Icom CI-V…) : « FEFE5EE01C0001FD », espaces permis ; la forme d'EasyPal
      « \\$FEFE5EE014...FD\\ » est acceptée telle quelle (copier-coller), y compris plusieurs
      commandes à la suite « \\$…\\$…\\ » comme dans EasyPal ;
    - sinon texte (Kenwood, Elecraft, Yaesu récents…) : « TX1; », avec \\r et \\n si besoin.
    Plusieurs commandes peuvent aussi être séparées par « | »."""
    import re
    t = (text or "").strip()
    if not t:
        return []
    out = []
    for part in re.split(r"\||\\\$", t):              # « | » ou « \$ » (début de commande EasyPal)
        p = part.strip()
        if p.startswith("\\"):
            p = p[1:]
        if p.endswith("\\"):
            p = p[:-1]
        p = p.lstrip("$").strip()
        if not p:
            continue
        h = re.sub(r"[\s,]", "", p)
        if h.lower().startswith("0x"):
            h = h[2:]
        if re.fullmatch(r"(?:[0-9A-Fa-f]{2})+", h):
            out.append(bytes.fromhex(h))
        else:
            out.append(p.replace("\\r", "\r").replace("\\n", "\n").encode("latin-1", "replace"))
    return out


def parse_cmd(text):
    """Toutes les commandes de la case, mises bout à bout (None si vide)."""
    return b"".join(parse_cmds(text)) or None


class CustomRig(RigBase):
    """Commandes CAT personnalisées, comme EasyPal : chaînes de départ (à l'ouverture), PTT
    marche / arrêt, chaînes de sortie (à la fermeture), délai entre deux commandes.
    Ne lit pas la fréquence du poste."""
    kind = "custom"
    reads_freq = False

    def __init__(self, cfg):
        self.cfg = cfg
        self.model = "CAT personnalisé"
        self.port = cfg.get("port")
        if not self.port:
            raise RuntimeError("commandes CAT personnalisées : choisissez le port série")
        self.cmds = {k: parse_cmds(cfg.get(k)) for k in CUSTOM_KEYS}
        try:
            self.delay = max(0, min(5000, int(cfg.get("cmd_delay") or 0))) / 1000
        except (TypeError, ValueError):
            self.delay = 0.2
        self.per_tx = cfg.get("cmd_when", "tx") != "open"     # comme EasyPal : à chaque émission
        self._in_tx = False
        self.civ = self._find_civ()                    # (adresse du poste, du contrôleur) si Icom
        self.can_qsy = self.civ is not None
        self._hz = None
        self.lock = threading.Lock()
        self.ser = open_port(cfg)
        if not self.per_tx:
            try:
                self._send("cmd_init1", "cmd_init2")
            except Exception:
                self.ser.close()
                raise

    def _find_civ(self):
        """Commandes Icom CI-V (FE FE adresse contrôleur …) ? -> (adresse, contrôleur) ou None.
        Les commandes PTT d'abord : ce sont elles qui visent le poste qui émet."""
        for k in ("cmd_ptt_on", "cmd_ptt_off", "cmd_init1", "cmd_init2", "cmd_exit1", "cmd_exit2"):
            for c in self.cmds.get(k) or ():
                if len(c) >= 6 and c[0] == 0xFE and c[1] == 0xFE and c[-1] == 0xFD and c[2] != 0xFE:
                    return c[2], c[3]
        return None

    def freq(self):
        return self._hz                                # la dernière fréquence envoyée (non lue)

    def set_freq(self, hz):
        if not self.civ:
            raise RuntimeError("Commandes CAT personnalisées : changez la fréquence sur le poste.")
        s = f"{int(hz):010d}"                          # Icom : 5 octets BCD, poids faibles d'abord
        bcd = bytes(int(s[i:i + 2], 16) for i in range(8, -1, -2))
        data = bytes([0xFE, 0xFE, self.civ[0], self.civ[1], 0x05]) + bcd + bytes([0xFD])
        with self.lock:
            self.ser.write(data)
            self.ser.flush()
        self._hz = int(hz)

    def qsy(self, hz, side=None):
        """Fréquence seulement : le mode du poste (LSB / USB, DATA) n'est pas touché."""
        self.set_freq(hz)
        return f"Icom CI-V ({self.civ[0]:02X}) : {int(hz) / 1e6:.3f} MHz"

    def before_tx(self):
        if self.per_tx and not self._in_tx:
            self._in_tx = True
            self._send("cmd_init1", "cmd_init2")

    def after_tx(self):
        if self.per_tx and self._in_tx:
            self._in_tx = False
            self._send("cmd_exit1", "cmd_exit2")

    def _send(self, *keys):
        with self.lock:
            for k in keys:
                for data in self.cmds.get(k) or ():    # une commande, puis le délai, etc.
                    self.ser.write(data)
                    self.ser.flush()
                    if self.delay:
                        time.sleep(self.delay)

    def ptt(self, on, rear=True):
        k = "cmd_ptt_on" if on else "cmd_ptt_off"
        if not self.cmds.get(k):
            raise RuntimeError("PTT par CAT : commande « " + ("PTT marche" if on else "PTT arrêt") +
                               " » vide (Réglages → Poste radio…)")
        self._send(k)

    def set_line(self, line, on):
        setattr(self.ser, line, bool(on))

    def close(self):
        if self.ser is None:
            return
        try:
            if self.per_tx:
                self.after_tx()                          # n'envoie rien si on n'émettait pas
            else:
                self._send("cmd_exit1", "cmd_exit2")
        except Exception:
            pass
        try:
            self.ser.close()
        except Exception:
            pass
        self.ser = None


class TciRig(RigBase):
    """SunSDR / ExpertSDR et autres SDR par TCI (WebSocket, port 40001) : fréquence, mode, PTT."""
    kind = "tci"
    RX = 0                                         # récepteur / émetteur 0, voie A

    def __init__(self, cfg):
        import tci
        self.cfg = cfg
        self.port = cfg.get("host") or tci.DEFAULT_HOST
        self.c = tci.TciClient(self.port)
        self.model = self.c.device or "TCI"

    def _alive(self):
        if not self.c.alive:
            raise RuntimeError("TCI : connexion perdue (ExpertSDR fermé ?)")

    def freq(self):
        self._alive()
        v = self.c.query(f"vfo:{self.RX},0", f"VFO:{self.RX},0;")
        try:
            return int(float(v)) if v else None
        except ValueError:
            return None

    def mode(self):
        self._alive()
        m = self.c.query(f"modulation:{self.RX}", f"MODULATION:{self.RX};")
        return (m or "").upper() or None

    def ptt(self, on, rear=True):
        self._alive()
        self.c.send(f"TRX:{self.RX},{'true' if on else 'false'};")

    def set_freq(self, hz):
        self._alive()
        self.c.send(f"VFO:{self.RX},0,{int(hz)};")
        self.c.wait_for(f"vfo:{self.RX},0", str(int(hz)))

    def set_sideband(self, side):
        self._alive()
        self.c.send(f"MODULATION:{self.RX},{'LSB' if side == 'LSB' else 'USB'};")

    def set_mode(self, which):
        """« data » : DIGL / DIGU (selon la bande latérale) ; « usb » : USB."""
        self._alive()
        want = ("DIGL" if self.is_lsb(self.mode()) else "DIGU") if which == "data" else "USB"
        self.c.send(f"MODULATION:{self.RX},{want};")
        ok = self.c.wait_for(f"modulation:{self.RX}", want)
        return ok, f"{self.model} : mode {want}" + ("" if ok else " (pas de confirmation)")

    def close(self):
        self.c.close()


class KenwoodRig(RigBase):
    """Kenwood en direct (et compatibles ASCII) : ID, FA, SF0 / OM0, TX0 / TX1 / RX."""
    kind = "kenwood"

    def __init__(self, cfg):
        self.cfg = cfg
        self.port, self.baud = cfg["port"], int(cfg["baud"])
        self.ser = open_port(cfg)
        self.lock = threading.Lock()
        self.model = None
        rid = self.query("ID;")
        if rid.startswith("ID"):
            self.model = audio.KENWOOD_IDS.get(rid[2:5], f"ID {rid[2:-1]}")
        elif not rid:
            self.close()
            raise RuntimeError(f"pas de réponse du poste sur {self.port} à {self.baud} bauds "
                               f"(vitesse ? menu « COM port » du poste)")

    def query(self, cmd, timeout=0.6):
        with self.lock:
            return audio._query(self.ser, cmd, timeout)

    def write(self, cmd):
        with self.lock:
            self.ser.write(cmd.encode())

    def freq(self):
        r = self.query("FA;")
        if r.startswith("FA") and r.endswith(";") and r[2:-1].isdigit():
            return int(r[2:-1])
        return None

    def mode(self):
        return audio._mode_of(self.model, self.query)[0]

    def set_freq(self, hz):
        self.write(f"FA{int(hz):011d};")

    def _sf_mode(self, code):
        """TS-890 : le mode se change par la commande SF (fréquence + mode), comme Hamlib :
        on relit « SF0…; » et on le renvoie avec le nouveau code (1 LSB, 2 USB, C LSB-DATA, D USB-DATA)."""
        r = self.query("SF0;")
        if r.startswith("SF0") and len(r) >= 16 and r.endswith(";"):
            self.write(r[:14] + code + r[15:])
        else:
            self.write(f"OM0{code};")

    def set_sideband(self, side):
        lsb = side == "LSB"
        if self.model == "TS-890S":
            self._sf_mode("1" if lsb else "2")
        elif self.model == "TS-990S":
            self.write("OM01;" if lsb else "OM02;")
        else:
            self.write("MD1;" if lsb else "MD2;")

    def set_voice(self, side):
        lsb = side == "LSB"
        if self.model == "TS-890S":
            self._sf_mode("1" if lsb else "2")
            return
        if self.model == "TS-990S":
            cmds = ["OM01;" if lsb else "OM02;"]
        else:
            cmds = ["MD1;" if lsb else "MD2;", "DA0;"]
        for c in cmds:
            self.write(c)
            time.sleep(0.15)

    def ptt(self, on, rear=True):
        if on:
            self.write("TX1;" if rear else "TX0;")
        else:
            self.write("RX;")

    def set_mode(self, which):
        """« data » : DATA en gardant la bande latérale du poste (LSB -> LSB-DATA,
        USB -> USB-DATA) ; « usb » : USB."""
        side = self._side() if which == "data" else "USB"
        lsb = side == "LSB"
        if self.model == "TS-990S":
            cmds = [("OM0C;" if lsb else "OM0D;")] if which == "data" else ["OM02;"]
        elif self.model == "TS-890S":
            self._sf_mode(("C" if lsb else "D") if which == "data" else "2")
            cmds = []
        else:
            cmds = [("MD1;" if lsb else "MD2;"), "DA1;" if which == "data" else "DA0;"]
        for c in cmds:
            self.write(c)
            time.sleep(0.15)
        time.sleep(0.3)
        m = self.mode()
        want = f"{side}-DATA" if which == "data" else "USB"
        ok = bool(m) and (self.is_data(m) and self.is_lsb(m) == lsb if which == "data" else m == "USB")
        return ok, (f"{self.model} passé en {m} par CAT." if ok else
                    f"{self.model} : le passage en {want} par CAT n'a pas pris (mode lu : {m}).")

    def set_line(self, which, on):
        with self.lock:
            setattr(self.ser, which, bool(on))

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass


class RigctlRig(RigBase):
    """Client du protocole texte de Hamlib rigctld (f, m, T, M)."""
    kind = "netrigctl"

    def __init__(self, cfg, host="127.0.0.1", port=4532, label=None):
        self.cfg = cfg
        self.host, self.tport = host, int(port)
        self.port = f"{host}:{port}"
        self.model = label or "Hamlib rigctld"
        self.lock = threading.Lock()
        self.sock = None
        self._connect()

    def _connect(self, tries=1):
        last = None
        for _ in range(tries):
            try:
                self.sock = socket.create_connection((self.host, self.tport), timeout=3)
                self.sock.settimeout(3)
                self.buf = b""
                return
            except OSError as e:
                last = e
                time.sleep(0.5)
        raise RuntimeError(f"serveur Hamlib injoignable ({self.host}:{self.tport}) : {last}")

    def _readline(self):
        while b"\n" not in self.buf:
            b = self.sock.recv(4096)
            if not b:
                raise RuntimeError("liaison avec rigctld coupée")
            self.buf += b
        line, self.buf = self.buf.split(b"\n", 1)
        return line.decode(errors="replace").strip()

    def _drain(self):
        """Jette les lignes en trop d'une réponse précédente : certains rigctld (versions de Hamlib
        des distributions Linux) répondent à « f » par la fréquence ET le VFO ; sans ça, toutes
        les réponses suivantes seraient décalées d'une ligne (fréquence non lue, F4EEI)."""
        self.buf = b""
        try:
            self.sock.setblocking(False)
            while True:
                if not self.sock.recv(4096):
                    break
        except (BlockingIOError, InterruptedError):
            pass
        except OSError:
            pass
        finally:
            try:
                self.sock.settimeout(3)
            except OSError:
                pass

    def cmd(self, c, nlines=1):
        with self.lock:
            if self.sock is None:
                self._connect()
            try:
                self._drain()
                self.sock.sendall((c + "\n").encode())
                out = []
                for _ in range(nlines):
                    line = self._readline()
                    out.append(line)
                    if line.startswith("RPRT"):
                        break
                return out
            except OSError as e:
                # réponse en retard ou liaison coupée : on repart d'une connexion propre
                # (sinon les réponses suivantes seraient décalées)
                try:
                    self.sock.close()
                except OSError:
                    pass
                self.sock = None
                if isinstance(e, TimeoutError) or "timed out" in str(e):
                    raise RuntimeError(f"le poste ne répond pas à la commande Hamlib « {c} »")
                raise RuntimeError(f"liaison avec Hamlib perdue : {e}")

    def _ok(self, c):
        r = self.cmd(c)
        return bool(r) and r[0] == "RPRT 0"

    def freq(self):
        r = self.cmd("f")
        try:
            return int(float(r[0].replace(",", ".")))
        except (ValueError, IndexError):
            return None

    def mode(self):
        r = self.cmd("m", 2)
        return r[0] if r and not r[0].startswith("RPRT") else None

    def set_freq(self, hz):
        if not self._ok(f"F {int(hz)}"):
            raise RuntimeError("Hamlib refuse le changement de fréquence")

    def set_sideband(self, side):
        if not self._ok(f"M {side} -1"):
            raise RuntimeError(f"Hamlib refuse le passage en {side}")

    def ptt(self, on, rear=True):
        if not on:
            if not self._ok("T 0"):
                raise RuntimeError("PTT : rigctld refuse T 0")
            return
        # Hamlib : 3 = émission audio arrière / data, 2 = micro ; repli sur 1 si refusé
        first = "T 3" if rear else "T 2"
        if not self._ok(first) and not self._ok("T 1"):
            raise RuntimeError("PTT : le poste refuse la commande d'émission (Hamlib T)")

    def set_mode(self, which):
        modes = [("PKTLSB" if self._side() == "LSB" else "PKTUSB")] if which == "data" else ["USB"]
        for m in modes:
            if self._ok(f"M {m} -1"):
                time.sleep(0.2)
                got = self.mode()
                return True, f"{self.model} passé en {got or m} par Hamlib."
        return False, f"{self.model} : Hamlib n'a pas pu passer en {modes[0]}."

    def close(self):
        try:
            if self.sock is not None:
                self.sock.close()
        except Exception:
            pass


class HamlibRig(RigctlRig):
    """Tous les postes Hamlib : HFImage lance rigctld (caché) et lui parle en local."""
    kind = "hamlib"
    # poste inconnu d'un Hamlib trop ancien (Linux, WSJT-X…) -> modèle proche + adresse CI-V
    FALLBACK = {3094: (3073, 0xB6)}                      # IC-7300MK2 -> IC-7300 à l'adresse B6h

    def __init__(self, cfg, model_id, label):
        exe = find_rigctld()
        if not exe:
            raise HamlibMissing()
        self.proc = None
        self.logf = None
        port = cfg.get("port") or ""
        if not port:
            raise RuntimeError("aucun port COM choisi pour le poste")
        self.logpath = os.path.join(os.path.dirname(exe) if os.access(os.path.dirname(exe), os.W_OK)
                                    else os.path.expanduser("~"), "rigctld_hfimage.log")
        civ = civ_addr(cfg)
        try:
            tport = self._start(exe, cfg, model_id, civ)
            if model_id in self.FALLBACK and civ is None:
                for _ in range(12):                          # rigctld trop ancien : il s'arrête aussitôt
                    if self.proc.poll() is not None:
                        break
                    time.sleep(0.1)
                if self.proc.poll() is not None:             # il ne connaît pas ce modèle
                    old, civ = self.FALLBACK[model_id]
                    tport = self._start(exe, cfg, old, civ)
            t0 = time.time()
            while True:
                if self.proc.poll() is not None:
                    raise RuntimeError("Hamlib (rigctld) s'est arrêté : " + (self._last_err() or
                                                                          f"code {self.proc.returncode}"))
                try:
                    super().__init__(cfg, "127.0.0.1", tport, label)
                    break
                except RuntimeError:
                    if time.time() - t0 > 15:
                        raise RuntimeError(f"{label} : Hamlib (rigctld) ne démarre pas — "
                                           + (self._last_err() or "le poste ne répond pas"))
                    time.sleep(0.4)
            try:
                f = self.freq()
            except RuntimeError:
                f = None
            if f is None:
                err = self._last_err()
                raise RuntimeError(f"{label} : pas de réponse du poste sur {port} à {cfg.get('baud')} bauds"
                                   + (f" (Hamlib : {err})" if err else "")
                                   + " — vérifiez le port, la vitesse et le réglage CAT du poste"
                                   + (icom_hint(label, civ) if "Icom" in label else ""))
        except Exception:
            self.close()
            raise
        self.port = port

    def _start(self, exe, cfg, model_id, civ):
        """Lance rigctld -> port TCP local."""
        if self.proc is not None:
            try:
                self.proc.kill()
                self.proc.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                pass
        port = cfg["port"]
        if cfg.get("share"):
            # partage : port fixe (4532, celui de Hamlib NET rigctl), sur le PC seulement
            tport = share_port(cfg)
            if not _port_free(tport):
                raise RuntimeError(f"partage du poste : le port {tport} est déjà pris (un autre rigctld, "
                                   "ou HFImage ouvert deux fois ?). Fermez-le ou choisissez un autre port.")
        else:
            tport = _free_port()
        args = [exe, "-m", str(model_id), "-r", _hamlib_port(port), "-s", str(int(cfg.get("baud") or 9600)),
                "-T", "127.0.0.1", "-t", str(tport)]
        if civ is not None:
            args += ["-c", f"0x{civ:02X}"]
        conf = []
        if str(cfg.get("data_bits")) in ("7", "8"):
            conf.append(f"data_bits={cfg['data_bits']}")
        if str(cfg.get("stop_bits")) in ("1", "2"):
            conf.append(f"stop_bits={cfg['stop_bits']}")
        hs = {"none": "None", "xonxoff": "XONXOFF", "hardware": "Hardware"}.get(cfg.get("handshake"))
        if hs:
            conf.append(f"serial_handshake={hs}")
        pl = ptt_line_on(cfg, port)
        for line in ("dtr", "rts"):
            v = {"high": "ON", "low": "OFF"}.get(cfg.get(line))
            # Hamlib refuse de démarrer si on force la ligne du PTT, ou RTS avec le contrôle matériel
            if v and line != pl and not (line == "rts" and hs == "Hardware"):
                conf.append(f"{line}_state={v}")
        if conf:
            args += ["--set-conf=" + ",".join(conf)]
        # PTT par DTR / RTS sur le port CAT : géré par Hamlib (le port lui appartient)
        if pl:
            args += ["-P", cfg["ptt"], "-p", _hamlib_port(port)]
        flags = 0x08000000 if sys.platform.startswith("win") else 0        # CREATE_NO_WINDOW
        lf = getattr(self, "logf", None)
        if lf not in (None, subprocess.DEVNULL):
            try:
                lf.close()
            except OSError:
                pass
        try:
            self.logf = open(self.logpath, "wb")
        except OSError:
            self.logf = subprocess.DEVNULL
        # sortie d'erreur dans un fichier (un tuyau non lu finirait par bloquer rigctld)
        self.proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=self.logf, creationflags=flags)
        _kill_with_us(self.proc)
        return tport

    def _last_err(self):
        try:
            with open(self.logpath, "rb") as f:
                lines = [l.strip() for l in f.read()[-4000:].decode(errors="replace").splitlines() if l.strip()]
            errs = [l for l in lines if "error" in l.lower() or "failed" in l.lower() or "timeout" in l.lower()]
            return (errs or lines or [""])[-1][:160]
        except OSError:
            return ""

    def close(self):
        super().close()
        if getattr(self, "proc", None) is not None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None
        lf = getattr(self, "logf", None)
        if lf not in (None, subprocess.DEVNULL):
            try:
                lf.close()
            except OSError:
                pass
            self.logf = None


_JOB = None


def _kill_with_us(proc):
    """Windows : rigctld est arrêté avec HFImage, même si HFImage plante (« job » Windows)."""
    global _JOB
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.OpenProcess.restype = wintypes.HANDLE
        if _JOB is None:
            job = k32.CreateJobObjectW(None, None)

            class BASIC(ctypes.Structure):
                _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                            ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                            ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                            ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                            ("SchedulingClass", wintypes.DWORD)]

            class IO(ctypes.Structure):
                _fields_ = [(n, ctypes.c_uint64) for n in ("a", "b", "c", "d", "e", "f")]

            class EXT(ctypes.Structure):
                _fields_ = [("Basic", BASIC), ("Io", IO), ("ProcessMemoryLimit", ctypes.c_size_t),
                            ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                            ("PeakJobMemoryUsed", ctypes.c_size_t)]
            info = EXT()
            info.Basic.LimitFlags = 0x2000                       # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            k32.SetInformationJobObject(wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info))
            _JOB = job
        h = k32.OpenProcess(0x0001 | 0x0100, False, proc.pid)    # TERMINATE | SET_QUOTA
        if h:
            k32.AssignProcessToJobObject(wintypes.HANDLE(_JOB), wintypes.HANDLE(h))
            k32.CloseHandle(wintypes.HANDLE(h))
    except Exception:
        pass


class FlrigRig(RigBase):
    """FLRig (XML-RPC)."""
    kind = "flrig"

    def __init__(self, cfg):
        import xmlrpc.client
        host = cfg.get("host") or "127.0.0.1:12345"
        if ":" not in host:
            host += ":12345"
        self.port = host
        self.cfg = cfg
        self.lock = threading.Lock()
        self.srv = xmlrpc.client.ServerProxy(f"http://{host}/RPC2")
        try:
            self.model = f"FLRig ({self.srv.rig.get_xcvr()})"
        except Exception as e:
            raise RuntimeError(f"FLRig injoignable sur {host} : {e}")

    def freq(self):
        with self.lock:
            try:
                return int(float(self.srv.rig.get_vfo()))
            except (ValueError, TypeError):
                return None

    def mode(self):
        with self.lock:
            return str(self.srv.rig.get_mode())

    def set_freq(self, hz):
        with self.lock:
            self.srv.rig.set_vfo(float(int(hz)))

    def set_sideband(self, side):
        with self.lock:
            self.srv.rig.set_mode(side)

    def ptt(self, on, rear=True):
        with self.lock:
            self.srv.rig.set_ptt(1 if on else 0)

    def set_mode(self, which):
        with self.lock:
            modes = [str(m) for m in (self.srv.rig.get_modes() or [])]
        if which != "data":
            wanted = ["USB"]
        elif self._side() == "LSB":
            wanted = ["LSB-D", "LSB-D1", "D-LSB", "PKT-L", "PKTLSB", "DATA-L", "LSB-DATA", "DIGL"]
        else:
            wanted = ["USB-D", "USB-D1", "D-USB", "PKT-U", "PKTUSB", "DATA-U", "USB-DATA", "DIGU", "DIG"]
        for w in wanted:
            for m in modes:
                if m.upper() == w:
                    with self.lock:
                        self.srv.rig.set_mode(m)
                    return True, f"FLRig : mode {m}."
        return False, f"FLRig : aucun mode {'DATA' if which == 'data' else 'USB'} parmi {', '.join(modes)}."


class OmniRigRig(RigBase):
    """OmniRig (serveur COM Windows), Rig 1 ou Rig 2."""
    kind = "omnirig"
    PM_RX, PM_TX = 0x200000, 0x400000
    PM_SSB_U, PM_DIG_U, PM_DIG_L = 0x2000000, 0x8000000, 0x10000000
    MODES = {0x800000: "CW", 0x1000000: "CW-R", 0x2000000: "USB", 0x4000000: "LSB", 0x8000000: "DIG-U",
             0x10000000: "DIG-L", 0x20000000: "AM", 0x40000000: "FM"}

    def __init__(self, cfg, rig_no):
        try:
            import comtypes.client
            comtypes.CoInitialize()
            self.omni = comtypes.client.CreateObject("OmniRig.OmniRigX", dynamic=True)
        except Exception as e:
            raise RuntimeError(f"OmniRig n'est pas installé ou ne démarre pas : {e}")
        self.rig = self.omni.Rig1 if rig_no == 1 else self.omni.Rig2
        self.port = f"OmniRig {rig_no}"
        self.lock = threading.Lock()
        try:
            self.model = f"OmniRig {rig_no} ({self.rig.RigType})"
        except Exception:
            self.model = f"OmniRig {rig_no}"
        self._tid = threading.get_ident()

    def _call(self, fn):
        # OmniRig est un objet COM : chaque fil doit initialiser COM
        if threading.get_ident() != self._tid:
            import comtypes
            try:
                comtypes.CoInitialize()
            except OSError:
                pass
        with self.lock:
            return fn()

    def freq(self):
        f = self._call(lambda: int(self.rig.Freq))
        return f or None

    def mode(self):
        m = self._call(lambda: int(self.rig.Mode))
        return self.MODES.get(m, f"0x{m:x}")

    def set_freq(self, hz):
        def go():
            try:
                self.rig.SetSimplexMode(int(hz))       # VFO A, simplex
            except Exception:
                self.rig.FreqA = int(hz)
        self._call(go)

    def set_sideband(self, side):
        self._call(lambda: setattr(self.rig, "Mode", 0x4000000 if side == "LSB" else self.PM_SSB_U))

    def ptt(self, on, rear=True):
        self._call(lambda: setattr(self.rig, "Tx", self.PM_TX if on else self.PM_RX))

    def set_mode(self, which):
        if which == "data":
            want = self.PM_DIG_L if self._side() == "LSB" else self.PM_DIG_U
        else:
            want = self.PM_SSB_U
        self._call(lambda: setattr(self.rig, "Mode", want))
        time.sleep(0.3)
        return True, f"OmniRig : mode {self.mode()}."


class HamlibMissing(RuntimeError):
    def __init__(self):
        super().__init__("Hamlib n'est pas installé : Réglages du poste → « Installer Hamlib »")


def make_rig(cfg):
    """Ouvre la liaison CAT selon les réglages. -> RigBase ou None (pas de CAT)."""
    e = effective(cfg)
    k = e["kind"]
    if k == "none":
        return None
    if k == "kenwood":
        return KenwoodRig(cfg)
    if k == "hamlib":
        return HamlibRig(cfg, e["model_id"], e["label"])
    if k == "netrigctl":
        host = cfg.get("host") or "127.0.0.1:4532"
        h, _, p = host.partition(":")
        return RigctlRig(cfg, h or "127.0.0.1", int(p or 4532), "Hamlib NET rigctl")
    if k == "flrig":
        return FlrigRig(cfg)
    if k == "omnirig":
        return OmniRigRig(cfg, e["rig_no"])
    if k == "custom":
        return CustomRig(cfg)
    if k == "tci":
        return TciRig(cfg)
    return None


class Ptt:
    """Commande d'émission selon les réglages : VOX, CAT (par le pilote), DTR / RTS
    (sur le port CAT ou sur le port d'une interface à côté)."""

    def __init__(self, cfg, rig):
        self.cfg, self.rig = cfg, rig
        self.method = cfg.get("ptt", "VOX")
        self.ser = None
        self.line = None
        e = effective(cfg)
        if self.method == "CAT":
            if rig is None:
                raise RuntimeError("PTT par CAT : choisissez d'abord le poste (liaison CAT)")
        elif self.method in ("DTR", "RTS"):
            self.line = self.method.lower()
            port = cfg.get("ptt_port") or cfg.get("port")
            if not port:
                raise RuntimeError(f"PTT {self.method} : aucun port COM choisi")
            if rig is not None and rig.port == port and e["kind"] in ("kenwood", "custom"):
                pass                                     # même port que le CAT Kenwood : ses lignes
            elif rig is not None and rig.port == port and e["kind"] == "hamlib":
                self.method = "CAT"                      # Hamlib tient le port et pilote la ligne
            elif rig is not None and rig.port == port:
                raise RuntimeError(f"PTT {self.method} : le port {port} est déjà utilisé par le CAT")
            else:
                try:                                     # lignes basses dès l'ouverture
                    self.ser = audio.open_serial(port, 9600, dtr=False, rts=False)
                except RuntimeError as ex:
                    raise RuntimeError(f"PTT {self.method} : {ex}")
                self.ser.rts = False
                self.ser.dtr = False

    def _set(self, on):
        if self.method == "VOX":
            return
        if self.method == "CAT":
            self.rig.ptt(on, self.cfg.get("tx_audio", "rear") == "rear")
        elif self.ser is not None:
            setattr(self.ser, self.line, bool(on))
        else:
            self.rig.set_line(self.line, on)

    def tx(self):
        if self.rig is not None:
            self.rig.before_tx()                         # chaînes de départ (commandes perso)
        self._set(True)

    def rx(self):
        """Retour en réception : la commande est répétée si elle échoue (sinon le poste
        resterait en émission)."""
        try:
            for i in range(3):
                try:
                    self._set(False)
                    break
                except Exception:
                    if i == 2:
                        raise
                    time.sleep(0.4)
        finally:
            if self.rig is not None:
                self.rig.after_tx()                      # chaînes de sortie (commandes perso)

    def close(self):
        """-> None, ou l'erreur du retour en réception (le poste est peut-être resté en émission)."""
        err = None
        try:
            self.rx()
        except Exception as e:
            err = e
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
        return err


# ------------------------------------------------------------------ Hamlib : installation
HAMLIB_URL = (f"https://github.com/Hamlib/Hamlib/releases/download/{HAMLIB_VERSION}/"
              f"hamlib-w64-{HAMLIB_VERSION}.zip")
HAMLIB_SHA256 = "8553bc6c5c6032e8debf99c017e98f58fed7e07e7c25d04815dc3e8bbe3304c7"
HAMLIB_FILES = ("rigctld.exe", "libhamlib-4.dll", "libgcc_s_seh-1.dll", "libwinpthread-1.dll", "libusb-1.0.dll")


def hamlib_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(base, "HFImage", f"hamlib-{HAMLIB_VERSION}")


LINUX_HAMLIB_HINT = "sudo apt install libhamlib-utils"      # Debian, Ubuntu, Mint, Raspberry Pi OS


def find_rigctld():
    """rigctld.exe : celui téléchargé par HFImage, sinon celui de WSJT-X / JTDX / Hamlib installé.
    Linux : rigctld du système (paquet libhamlib-utils / hamlib)."""
    if not sys.platform.startswith("win"):
        import shutil
        return shutil.which("rigctld")
    cands = [os.path.join(hamlib_dir(), "rigctld.exe")] + _old_own_rigctld()
    pf = [os.environ.get(v) for v in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")]
    for root in [r"C:\WSJT\wsjtx\bin", r"C:\WSJT\wsjtx-improved\bin", r"C:\JTDX64\bin", r"C:\JTDX\bin"]:
        cands += [os.path.join(root, "rigctld-wsjtx.exe"), os.path.join(root, "rigctld.exe")]
    for p in pf:
        if not p or not os.path.isdir(p):
            continue
        try:
            for d in os.listdir(p):
                if d.lower().startswith("hamlib"):
                    cands.append(os.path.join(p, d, "bin", "rigctld.exe"))
        except OSError:
            pass
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def _old_own_rigctld():
    """rigctld des versions de Hamlib téléchargées par d'anciennes versions d'HFImage (la plus récente
    d'abord) : il reste utilisable en attendant la mise à jour."""
    base = os.path.dirname(hamlib_dir())
    try:
        dirs = [d for d in os.listdir(base) if d.startswith("hamlib-") and d != os.path.basename(hamlib_dir())]
    except OSError:
        return []

    def ver(d):
        try:
            return tuple(int(x) for x in d[7:].split("."))
        except ValueError:
            return ()
    return [os.path.join(base, d, "rigctld.exe") for d in sorted(dirs, key=ver, reverse=True)]


def hamlib_outdated(exe=None):
    """Windows : le rigctld utilisé est celui d'une ancienne version d'HFImage -> True."""
    exe = exe or find_rigctld()
    return bool(exe) and exe in _old_own_rigctld()


def install_hamlib(progress=lambda f: None):
    """Télécharge Hamlib pour Windows depuis GitHub (empreinte SHA-256 vérifiée)
    et n'en garde que rigctld et ses bibliothèques. -> dossier."""
    if not sys.platform.startswith("win"):
        raise RuntimeError("Linux : installez Hamlib avec le gestionnaire de paquets : " + LINUX_HAMLIB_HINT)
    import io
    import urllib.request
    req = urllib.request.Request(HAMLIB_URL, headers={"User-Agent": "HFImage-F4GOP"})
    h, buf = hashlib.sha256(), io.BytesIO()
    import netssl
    with netssl.urlopen(req, 30) as r:
        total = int(r.headers.get("Content-Length") or 0)
        while True:
            b = r.read(128 * 1024)
            if not b:
                break
            buf.write(b)
            h.update(b)
            if total:
                progress(min(1.0, buf.tell() / total))
    if h.hexdigest() != HAMLIB_SHA256:
        raise ValueError("Hamlib téléchargé : empreinte SHA-256 inattendue, installation refusée")
    dest = hamlib_dir()
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(buf) as z:
        for n in z.namelist():
            base = n.rsplit("/", 1)[-1]
            if "/bin/" in n and base in HAMLIB_FILES:
                with z.open(n) as src, open(os.path.join(dest, base), "wb") as out:
                    out.write(src.read())
    if not os.path.isfile(os.path.join(dest, "rigctld.exe")):
        raise RuntimeError("rigctld.exe absent de l'archive Hamlib")
    return dest


ICOM_CIV = {"IC-7300": 0x94, "IC-7300MK2": 0xB6, "IC-7610": 0x98, "IC-705": 0xA4, "IC-9700": 0xA2,
            "IC-7100": 0x88, "IC-7851": 0x8E, "IC-7850/7851": 0x8E, "IC-7600": 0x7A, "IC-7700": 0x74,
            "IC-7000": 0x70, "IC-7200": 0x76, "IC-7410": 0x80, "IC-9100": 0x7C, "IC-905": 0xAC}


def icom_hint(label, civ=None):
    """Conseils quand un Icom ne répond pas."""
    mod = label.replace("Icom", "").strip()
    a = civ if civ is not None else ICOM_CIV.get(mod)
    t = ". Icom : "
    if a is not None:
        t += f"l'adresse CI-V du poste doit être {a:02X}h (menu Set → Connectors → CI-V) ; "
    return t + ("« CI-V USB Port » sur « Unlink from [REMOTE] » ; certains Icom (IC-7610, IC-7300MK2…) "
                "créent deux ports COM : essayez l'autre")


def _hamlib_port(port):
    """COM10 et plus : écriture Windows « \\\\.\\COM10 » pour Hamlib."""
    p = port.strip()
    if p.upper().startswith("COM") and p[3:].isdigit() and int(p[3:]) >= 10:
        return "\\\\.\\" + p
    return p


def _port_free(p):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", p))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p
