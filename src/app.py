#!/usr/bin/env python3
"""HFImage F4GOP — émission / réception d'images numériques en HF.

Onglets : Émission, Réception, Simulation, Réglages.
"""
import io
import json
import os
import platform
import re
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
import traceback
import zlib
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

import numpy as np
from PIL import Image, ImageTk

import audio
import easypal_hybrid
import engine
import hamdrm
import hybrid
import i18n
import imgfmt
import presence
import docking
import gallery
import sites
import websync
import trafic
import msgwin
import clocktz
import radio
import radiodlg
import contextlib
import stationmap
import theme
import updater
from i18n import tr
import protocol
import qsl
import rxclean
import dropfiles
import bubbles
import setupwiz
import translate
import shutil
import webbrowser
import wavtext
from panel import LED_AMBER, LED_GREEN, LED_OFF, LED_RED, ImageView, StatusPanel
import waterfall
from waterfall import RowMaker, Waterfall
from modem import MODE_BPS, MODE_BW
import random
import wave

APP = "HFImage F4GOP"
VERSION = "1.60"


def _take_profile(argv):
    """« --profil 20m » (ou --profile) : plusieurs HFImage ouverts en même temps, chacun avec ses
    propres réglages (entrée audio, poste, dossier). Retiré de argv ; -> nom nettoyé ou ""."""
    for i, a in enumerate(argv[1:], 1):
        low = a.lower()
        name = None
        if low in ("--profil", "--profile") and i + 1 < len(argv):
            name = argv[i + 1]
            del argv[i:i + 2]
        elif low.startswith(("--profil=", "--profile=")):
            name = a.split("=", 1)[1]
            del argv[i]
        if name is not None:
            return re.sub(r"[^A-Za-z0-9_-]", "", name)[:16]
    return ""


PROFILE = _take_profile(sys.argv)
CONF_MAIN = os.path.join(os.path.expanduser("~"), ".hfimage.json")
CONF_PATH = os.path.join(os.path.expanduser("~"), f".hfimage_{PROFILE}.json") if PROFILE else CONF_MAIN
DEFAULT_OUT = os.path.join(os.path.expanduser("~"), "Documents", "HFImage")
if PROFILE:
    DEFAULT_OUT = os.path.join(DEFAULT_OUT, PROFILE)
DEFAULTS = {
    "callsign": "", "opname": "", "mode": "Auto", "width": "auto", "seconds": 120, "fmt": "avif",
    "overhead": "auto", "out_dev": "", "in_dev": "", "level": 50,
    "ptt": "VOX", "cat_port": "", "cat_baud": 115200, "cat_cmd": "TX1;",
    "folder": DEFAULT_OUT,
    "hyb_on": False, "hyb_host": "", "hyb_port": 21, "hyb_user": "", "hyb_pass": "",
    "hyb_dir": "hfimage", "hyb_tls": False, "hyb_url": "", "hyb_auto": True,
    "hyb_width": "originale", "hyb_kb": 3000, "hyb_fmt": "original", "gif_kb": 2000, "hyb_rx_max_mb": 200, "hyb_keep": 3,
    "net_on": True, "net_host": presence.DEFAULT_HOST, "net_port": presence.DEFAULT_PORT,
    "update_check": True,
    "look_style": "classique", "modern_theme": "Vert EasyPal",
    "theme": "Vert EasyPal", "theme_color": "#3a8ee6", "font_family": "(par défaut)", "font_size": "9",
    "locator": "", "bsr_auto": True, "fix_auto": True, "ack_auto": True, "listen_after": True, "follow_mode": True,
    "cwid": False, "cat_freq": True, "lang": "", "msg_translate": True, "wait_free": True, "hyb_flash": True,
    "freq_presets": [[3733000, "LSB"], [7058000, "LSB"], [14233000, "USB"], [21340000, "USB"], [28680000, "USB"]],
    "drm_mode": "B", "drm_qam": "QAM16", "drm_bw": "2,4 kHz", "drm_prot": "Haute (HI)", "drm_rs": "RS2",
    "wav_volume": 5, "wft_font": "Arial", "wft_neg": False, "wft_text": "",
}
TX_MODES = ["Auto", "DATAC1X", "DATAC1", "DATAC3", "DATAC4"] + (["EasyPal"] if hamdrm.AVAILABLE else [])
# mode EasyPal (HamDRM) : réglages proposés, comme dans EasyPal
DRM_MODES = ["A", "B", "E"]
DRM_QAMS = ["QAM4", "QAM16", "QAM64"]
DRM_BWS = ["2,2 kHz", "2,4 kHz"]          # comme EasyPal (QSSTV : 2,3 / 2,5, même signal)
DRM_PROTS = ["Haute (HI)", "Normale (LO)"]
DRM_RSS = ["Aucun", "RS1", "RS2", "RS3", "RS4"]
# formats lisibles par EasyPal / QSSTV : JPEG 2000 et JPEG (pas d'AVIF ni de WebP)
DRM_FORMATS = {"avif": "jp2", "webp": "jp2", "jpeg": "jpeg"}
# mode « Auto » : choisi d'après le report le plus faible des stations (dB, SNR sur 3 kHz).
# Mesuré au simulateur avec QSB moyen : DATAC1X perd peu de trames dès ~10 dB,
# DATAC1 dès ~5 dB, DATAC3 tient jusque vers 0 dB.
# Les seuils sont exprimés en SNR *estimé par codec2* (celui des reports et du panneau) :
# cette estimation est comprimée (SNR réel 12 dB -> ~8,5 dB affichés avec QSB). Mesuré au
# simulateur, QSB moyen : DATAC1X perd < 12 % des trames dès ~6,5 dB affichés (9 dB réels),
# DATAC1 < 25 % dès ~3,5 dB affichés (5 dB réels).
AUTO_STEPS = [(9, "DATAC1X"), (5, "DATAC1"), (None, "DATAC3")]
AUTO_DEFAULT = "DATAC1X"         # aucun report récent : image nette (comme avant la 0.22)
# seuil de chaque mode (dB) : la robustesse « Auto » dépend de la marge au-dessus
MODE_THR = {"DATAC1X": 9, "DATAC1": 5, "DATAC3": 0, "DATAC4": -4}
AUTO_MAX_AGE = 45 * 60           # reports pris en compte (s)
# robustesse = redondance du code fontaine (trames en plus, pour les trames perdues dans le QSB)
ROBUST = [("Auto (selon les reports)", None), ("Faible (15 %)", 15), ("Normale (40 %)", 40), ("Forte (70 %)", 70), ("Très forte (100 %)", 100)]
DATA_ACTIONS = {"ask": "Demander", "switch": "Passer en DATA automatiquement (USB-DATA / LSB-DATA)",
                "send": "Émettre sans rien dire"}
HEARD_KEEP_S = 2 * 3600     # stations entendues gardées 2 h dans la liste
RING_S = 15 * 60          # Relire RX : 15 dernières minutes gardées en mémoire
PTT_METHODS = ["VOX", "CAT", "RTS", "DTR"]
# taille d'image proposée quand on change de mode
# durée d'émission proposée quand on change de mode (s)
MODE_SEC = {"DATAC1X": 120, "DATAC1": 120, "DATAC3": 120, "DATAC4": 180, "EasyPal": 90}
# « original » : le fichier ouvert part tel quel (JPG, PNG, GIF, AVIF, WEBP, SVG compressé)
FORMATS_TX = ["avif", "webp", "jpg", "original"]
ORIGINAL_KINDS = ("jpeg", "png", "gif", "avif", "webp", "svg")
WIDTHS = ["auto", 160, 240, 320, 480, 640, 800, 1024, 1280, 1600, 1920, "originale"]
HYB_WIDTHS = [480, 640, 800, 1024, 1280, 1600, 1920, 2560, "originale"]
# hybride : images déposées sur NOTRE serveur FTP qu'on garde (les plus anciennes sont effacées)
# images envoyées gardées dans « envoyees » (galerie « Dernières envoyées ») ; 0 = toutes
SENT_KEEP = {"Toutes": 0, "Les 20 dernières": 20, "La dernière seulement": 1}
HYB_KEEP = {"Toutes": 0, "Les 3 dernières": 3, "La dernière seulement": 1}
HYB_RX_MAX = ["8 Mo", "50 Mo", "200 Mo", "1 Go", "Sans limite"]
HYB_MAX_BYTES = 1 << 31        # image hybride : partie telle quelle (plus de recompression au-delà de 7,5 Mo)
# aperçu rapide : taille cible selon le mode (octets) ; proposé si l'émission dépasse 2 min
PREVIEW_BYTES = {"DATAC1X": 1200, "DATAC1": 1000, "DATAC3": 450, "DATAC4": 220}
PREVIEW_MIN_S = 120
PREVIEW = 300
GREEN = "#33d633"          # vert « EasyPal »
GREEN_DARK = "#1c8f1c"
FG_DARK = "#0d3b0d"
BTN_ON = "#ffe066"


def _tr_box(f):
    def g(title, message="", **k):
        return f(title, tr(message), **k)
    return g


for _n in ("showinfo", "showerror", "showwarning", "askyesno"):
    setattr(messagebox, _n, _tr_box(getattr(messagebox, _n)))


class TrVar(tk.StringVar):
    """StringVar dont le texte affiché est traduit (et retraduit au changement de langue)."""

    def set(self, value):
        self._fr = value
        super().set(tr(value))

    def retranslate(self):
        super().set(tr(getattr(self, "_fr", "")))



def tip(widget, text):
    """Petite bulle d'aide quand la souris s'arrête sur `widget` (texte traduit)."""
    state = {"w": None, "job": None}

    def show():
        state["job"] = None
        if state["w"] is not None:
            return
        t = tk.Toplevel(widget)
        t.wm_overrideredirect(True)
        t.wm_geometry(f"+{widget.winfo_pointerx() + 12}+{widget.winfo_pointery() + 16}")
        tk.Label(t, text=tr(text), bg="#ffffe0", fg="#000", relief="solid", borderwidth=1,
                 font=("TkDefaultFont", 8), padx=4, pady=1).pack()
        state["w"] = t

    def enter(_e):
        if state["job"] is None and state["w"] is None:
            state["job"] = widget.after(500, show)

    def leave(_e):
        if state["job"] is not None:
            widget.after_cancel(state["job"])
            state["job"] = None
        if state["w"] is not None:
            state["w"].destroy()
            state["w"] = None

    widget.bind("<Enter>", enter, add="+")
    widget.bind("<Leave>", leave, add="+")
    widget.bind("<Button-1>", leave, add="+")


def private_file(path):
    """Linux : fichier de réglages lisible par son seul propriétaire (il contient le mot de passe
    FTP ; sous Windows, celui-ci est déjà chiffré pour le compte Windows)."""
    if sys.platform.startswith("win"):
        return
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def linux_menu_entry(cmd, name, slug, desktop=False):
    """Linux : fichier .desktop (menu des applications, et Bureau si desktop=True) + icône."""
    import shlex
    import shutil
    here = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    data = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    icon_dir = os.path.join(data, "icons")
    os.makedirs(icon_dir, exist_ok=True)
    icon = os.path.join(icon_dir, "hfimage-f4gop.png")
    src = os.path.join(here, "icon256.png")
    if os.path.exists(src) and not os.path.exists(icon):
        shutil.copyfile(src, icon)
    text = ("[Desktop Entry]\nType=Application\n"
            f"Name={name}\nComment=Images numériques en HF / HF digital pictures\n"
            f"Exec={' '.join(shlex.quote(c) for c in cmd)}\nIcon={icon}\nTerminal=false\n"
            "Categories=HamRadio;Network;\n")
    targets = [os.path.join(data, "applications", slug + ".desktop")]
    if desktop:
        d = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.isdir(d):
            d = os.path.join(os.path.expanduser("~"), "Bureau")
        if os.path.isdir(d):
            targets.append(os.path.join(d, slug + ".desktop"))
    for t in targets:
        os.makedirs(os.path.dirname(t), exist_ok=True)
        try:
            with open(t, encoding="utf-8") as f:
                if f.read() == text:
                    continue
        except OSError:
            pass
        with open(t, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(t, 0o755)

def split_call(text):
    """« F4LTX CHRIS » -> ("F4LTX", "Chris") : l'indicatif est le premier mot, le reste est le
    prénom (beaucoup d'utilisateurs l'écrivaient dans la case indicatif ; par radio, l'indicatif
    est coupé à 8 caractères : « F4LTX CH », et la même station apparaissait deux fois)."""
    parts = str(text or "").strip().split()
    if not parts:
        return "", ""
    return parts[0].upper(), " ".join(parts[1:]).title()[:16]


def is_swl(call):
    """Indicatif d'écouteur (SWL) : PA0041SWL, F-12345, 14VD274 (identifiants 14…), ONL1234.
    Ces stations reçoivent et envoient leurs reports par Internet, mais n'émettent jamais."""
    c = str(call or "").strip().upper()
    return bool(c) and (c.endswith("SWL") or "-" in c or c[:2].isdigit()
                        or (c.startswith("ONL") and c[3:].isdigit()))


def load_conf():
    c = dict(DEFAULTS)
    try:
        path = CONF_PATH
        new_profile = PROFILE and not os.path.exists(CONF_PATH) and os.path.exists(CONF_MAIN)
        if new_profile:
            path = CONF_MAIN              # nouveau profil : part des réglages habituels (indicatif, poste…)
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
        if new_profile:
            saved["folder"] = DEFAULT_OUT       # mais ses images dans son propre dossier
        c.update(saved)
        if "ptt" not in saved:                       # réglages de la v0.3
            c["ptt"] = "CAT" if saved.get("cat_on") else "VOX"
        if saved.get("conf_v", 0) < 10:
            # v0.10 : nouveau mode rapide DATAC1X et 2 min par défaut (images nettes)
            if saved.get("mode", "DATAC1") == "DATAC1" and int(saved.get("seconds", 60)) == 60:
                c["mode"], c["seconds"] = "DATAC1X", 120
            if c.get("fmt") == "jpeg":
                c["fmt"] = "jpg"
        if saved.get("conf_v", 0) < 22:
            # v0.22 : redondance 10 % trop juste dans le QSB -> « Normale (40 %) »
            if str(saved.get("overhead", 10)).isdigit() and int(saved.get("overhead", 10)) <= 10:
                c["overhead"] = 40
            if c.get("mode") == "DATAC1X":
                c["mode"] = "Auto"                   # DATAC1X choisi seul quand les reports le permettent
        if saved.get("conf_v", 0) < 24 and str(c.get("overhead")) in ("10", "40"):
            # v0.24 : robustesse « Auto » (15 % si le lien est bon, 40 % s'il est juste)
            c["overhead"] = "auto"
        if saved.get("conf_v", 0) < 62 and c.get("drm_rs") == "Aucun":
            # v0.62 : Reed-Solomon RS2 par défaut en EasyPal (image complète malgré le QSB)
            c["drm_rs"] = "RS2"
        if saved.get("conf_v", 0) < 63:
            # v0.98 : hybride éclair (DATAC13, passe jusqu'à -7 dB) par défaut, une fois ; sans serveur
            # des stations en ligne au moment d'émettre, l'annonce normale (DATAC3) part à la place
            c["hyb_flash"] = True
            c["conf_v"] = 63
        if saved.get("conf_v", 0) < 64:
            # v1.04 : en hybride, l'image passe par Internet : plus de réduction à 640 px / 60 ko
            # (image floue) ; le fichier original part tel quel, en pleine qualité
            try:
                small = float(saved.get("hyb_kb", 60)) <= 100
            except (TypeError, ValueError):
                small = True
            if small:
                c["hyb_kb"], c["hyb_width"], c["hyb_fmt"] = 3000, "originale", "original"
            c["conf_v"] = 64
        # prénom écrit dans la case indicatif : rangé dans sa propre case
        call, name = split_call(c.get("callsign"))
        if name:
            c["callsign"] = call
            c["opname"] = c.get("opname") or name
        if c.get("fmt") not in FORMATS_TX:
            c["fmt"] = {"jpeg": "jpg"}.get(c.get("fmt"), "avif")
    except Exception:
        pass
    return c


def _fmt_size(n):
    n = int(n or 0)
    return f"{n} o" if n < 1000 else (f"{n / 1000:.1f} ko" if n < 1_000_000 else f"{n / 1e6:.2f} Mo")


def _fmt_s(sec):
    sec = int(round(sec))
    if sec < 60:
        return f"{sec} s"
    if sec < 3600:
        return f"{sec // 60} min {sec % 60:02d} s"
    return f"{sec // 3600} h {sec % 3600 // 60:02d} min"


def easypal_hybrid_params(cfg_call):
    """Annonce hybride EasyPal : toujours en mode E, QAM4, protection haute, entrelacement long
    (réglages imposés par EasyPal / QSSTV pour ce petit fichier)."""
    return hamdrm.make_params(cfg_call or "NOCALL", mode=2, bandwidth=1, qam=0, protection=0, interleaver=0, rs=0)


class _NeedCompute(Exception):
    """Préparation en tâche de fond : ce calcul n'est pas encore fait."""

    def __init__(self, key, obj, fn, args, kw):
        super().__init__(key[0])
        self.key, self.obj, self.fn, self.args, self.kw = key, obj, fn, args, kw


class HybridJob:
    """Image prête pour le mode hybride ; `announce` existe après le dépôt FTP."""

    def __init__(self, data, fmt, call):
        self.data, self.fmt, self.call = data, fmt, call
        self.filename = ""          # fichier (pas une image) : nom d'origine, déposé tel quel
        self.mode = "DATAC3"
        self.announce = None
        self.pre = None             # dépôt fait d'avance (« Déposer maintenant ») : (signature, résultat)


def sd():
    import sounddevice
    return sounddevice


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP} {VERSION}" + (f" — {PROFILE}" if PROFILE else ""))
        self._set_icon()
        self._linux_menu()
        self.first_run = not os.path.exists(CONF_PATH)    # aucun réglage enregistré : premier démarrage
        private_file(CONF_PATH)
        self.conf = load_conf()
        clocktz.MODE = self.conf.get("clock", "local")
        self.v_fbold = tk.BooleanVar(value=bool(self.conf.get("font_bold")))       # menu Police / Réglages
        self.conf["font_size"] = theme.size_name(self.conf.get("font_size", "9"))   # 8 … 14 points
        self.v_msize = tk.StringVar(value=self.conf["font_size"])
        self.geometry(self.conf.get("win_geom") or "1320x880")
        self.minsize(900, 600)
        if self.conf.get("win_zoomed"):
            self.after(50, lambda: self._zoom_main())
        i18n.set_lang(self.conf.get("lang") or i18n.detect_lang())
        self._orig = {}             # textes français d'origine des widgets (changement de langue)
        self.uiq = queue.Queue()
        self.src_img = None
        self.src_raw = None             # octets du fichier ouvert (mode « original »)
        self.src_kind = None            # jpeg, png, svg…
        self.src_anim = None            # GIF animé : (images, durées ms)
        self._gif_cache = {}
        self.tx = None            # engine.Transmission prête
        self.tx_busy = False
        self.stop_tx = threading.Event()
        self.rx_stream = None
        self.rx_engine = None
        self.audio_q = queue.Queue()
        self._photos = {}
        self.pips = []              # images des correspondants incrustées dans l'image TX
        self.bubbles = []           # bulles de texte (BD) dessinées sur l'image TX

        self.sent_images = {}       # id -> Transmission émise (pour répondre aux BSR)
        self.my_ids = set()         # id de nos images (normales et annonces hybrides)
        self.heard = {}             # indicatif -> {t, freq, snr, what, loc} : stations entendues
        # Rx Ok, comme EasyPal : stations qui ont reçu l'image EN COURS (la nôtre, ou celle
        # qu'on vient de recevoir), visible par tous ; id image -> {indicatif: (report, heure)}
        self.rxok_by_id = {}
        self.rxok_ctx = None        # id de l'image affichée dans Rx Ok
        self.rxok = {}              # = rxok_by_id[rxok_ctx]
        self.known_loc = self._load_locs()   # indicatif -> locator (gardé d'une session à l'autre)
        self.map_win = None
        self.online = {}            # stations en ligne (Internet) : clé -> présence (call, loc, freq…)
        self.opnames = {}           # indicatif -> prénom (présence Internet, ou écrit après l'indicatif)
        self.net = None             # client de présence Internet
        self.net_ok = False
        self.rxok_sent = set()      # images dont on a déjà confirmé la réception par Internet
        self.pending_fix = {}       # id -> BSR reçus en attente de FIX
        self.drm_last_tx = None     # mode EasyPal : dernière image émise (pour répondre aux BSR)
        self.drm_pending_bsr = None # mode EasyPal : BSR reçu en attente de FIX
        self._drm_hint = None       # mode EasyPal : image incomplète déjà signalée
        self._drm_hyb_seen = set()  # annonces hybrides EasyPal déjà traitées
        self.bsr_state = {}         # id -> BSR envoyés (réception)
        self.ack_pending = {}       # id -> ACK à envoyer quand l'émetteur aura fini
        self.last_tx_id = None      # id de notre dernière image émise (carte : stations qui l'ont reçue)
        self.sent_msgs = {}         # id -> message envoyé : texte, heure, mode, accusés {indicatif: (report, t, via)}
        self.bsr_target = None
        self.ctl_seen = {}
        self.rig = None
        self.rig_freq = self.rig_mode = None
        self.radio_cfg = radio.from_conf(self.conf)     # poste, CAT, PTT (fenêtre « Poste radio »)
        self.rig_lock = threading.RLock()
        self._rig_err = None                       # (heure, erreur) du dernier échec d'ouverture CAT
        self._rig_hold = 0                               # > 0 : liaison CAT prêtée (tests)
        self._rig_kick = threading.Event()
        self._closing = False
        self.snr_by_call = {}       # dernier SNR mesuré par station (report QSL)
        self.snr_by_id = {}
        self.rx_dbfs = -120.0
        self.ring, self.ring_len = [], 0
        self.rec_wav = None
        self.look = theme.Appearance(self)
        self._build()
        self._apply_look(save=False)
        self.gal_store = None
        self._gallery_open()
        self.after(1500, self._thumb_from_gallery)     # vignette : dernière image reçue
        self.web = websync.WebSync(os.path.join(os.path.expanduser("~"), ".hfimage_web.json"),
                                   log=lambda m: self.ui(self.log, m))
        self.after(100, self._poll)
        self.after(500, self._tick)
        self.after(1000, self._clock)
        threading.Thread(target=self._rig_loop, daemon=True).start()
        self._btn_on("hyb", self.v_hyb.get())
        # comme EasyPal : on écoute dès le démarrage si l'entrée audio est réglée
        self.after(1500, lambda: self.toggle_listen(quiet=True)
                   if self.v_in.get() and self.rx_stream is None else None)
        self.after(1200, self.net_start)
        for ms in (100, 20000):                       # ancien exe laissé par une mise à jour (l'ancien
            self.after(ms, self._update_cleanup)      # programme met parfois quelques s à se fermer)
        if self.conf.get("update_check", True):
            self.after(5000, lambda: self.update_check(quiet=True))
        self.after(300, self._startup_dialogs)     # licence, puis assistant au premier démarrage
        self.after(400, self._restore_layout)
        self.after(1500, self._restore_layout)     # une 2e fois, une fois tout affiché
        self.after(1700, lambda: self.dock.restore(self.conf.get("detached")))   # fenêtres séparées
        self.after(20000, self._auto_clean)        # anciennes images (puis toutes les 6 h)
        self.protocol("WM_DELETE_WINDOW", self._quit)
        self.journal_devices()
        self.log(f"{APP} {VERSION} prêt. Images reçues : {self.conf['folder']}")

    # ------------------------------------------------------------------ UI
    def _build(self):
        self.configure(bg=GREEN)
        self.v_call = tk.StringVar(value=self.conf["callsign"])
        self.v_opname = tk.StringVar(value=self.conf.get("opname", ""))
        self.v_loc = tk.StringVar(value=self.conf.get("locator", ""))
        protocol.MY_LOCATOR = self.v_loc.get().strip()
        self.v_loc.trace_add("write", lambda *a: setattr(protocol, "MY_LOCATOR", self.v_loc.get().strip()))
        self.v_state = TrVar(value="")
        self.v_state.set("Réception arrêtée")
        self.v_call.trace_add("write", lambda *a: self._set_title())
        self._set_title()

        # bandeau de mise à jour (caché tant qu'aucune nouvelle version n'est annoncée)
        self.upd_bar = tk.Frame(self, bg="#ff9f1a", cursor="hand2")
        self.upd_bar._no_theme = True
        self.upd_lbl = tk.Label(self.upd_bar, text="", bg="#ff9f1a", fg="#1a1a1a", cursor="hand2",
                                font=("TkDefaultFont", 10, "bold"), anchor="w")
        self.upd_lbl.pack(side="left", fill="x", expand=True, padx=8, pady=3)
        self.upd_close = tk.Label(self.upd_bar, text="✕", bg="#ff9f1a", fg="#1a1a1a", cursor="hand2",
                                  font=("TkDefaultFont", 10, "bold"))
        self.upd_close.pack(side="right", padx=8)
        for w in (self.upd_bar, self.upd_lbl):
            w.bind("<Button-1>", lambda e: self._update_click())
        self.upd_close.bind("<Button-1>", lambda e: self.upd_bar.pack_forget())
        self.upd_info = None
        self.upd_busy = False
        self._build_topbar()
        # séparateurs réglables à la souris (positions gardées d'une session à l'autre)
        pw = dict(bg=GREEN_DARK, sashwidth=6, sashrelief="raised", bd=0, opaqueresize=True)
        self.panes = {}
        main = tk.PanedWindow(self, orient="horizontal", **pw)
        main.pack(fill="both", expand=True, padx=2, pady=2)
        self._main_pane = main
        self.panes["main"] = main
        # ---------------- colonne de gauche : état, boutons, spectre + waterfall, stations
        left = tk.Frame(main, bg=GREEN, width=268)
        main.add(left, minsize=230, stretch="never", width=268)
        ctl = tk.Frame(left, bg=GREEN)               # panneau d'état + grille de boutons
        ctl.pack(fill="x")
        self.panel = StatusPanel(ctl)
        self.panel.on_thumb = lambda: self.show_tab("rx")
        self.panel.pack(fill="x")
        self._button_grid(ctl)
        lpw = tk.PanedWindow(left, orient="vertical", **pw)
        lpw.pack(fill="both", expand=True, pady=(4, 0))
        self.panes["left"] = lpw
        wfbox = self._wfbox = tk.Frame(lpw, bg="#000")
        self.wf = Waterfall(wfbox, height=200)
        self.wf.pack(fill="both", expand=True)
        lpw.add(wfbox, minsize=90, stretch="always")
        sbox = self._sbox = tk.Frame(lpw, bg=GREEN)
        lpw.add(sbox, minsize=80, stretch="never", height=170)
        self._stations_box(sbox)

        # ---------------- à droite : grande image, onglets, journal
        right = tk.Frame(main, bg=GREEN)
        main.add(right, minsize=500, stretch="always")
        rpw = tk.PanedWindow(right, orient="vertical", **pw)
        rpw.pack(fill="both", expand=True)
        self.panes["right"] = rpw
        self.nb = nb = ttk.Notebook(rpw)
        rpw.add(nb, minsize=300, stretch="always")
        self._tab_rx(nb)
        self._tab_tx(nb)
        self._tab_stations(nb)
        self._tab_sim(nb)
        self.gal = gallery.GalleryView(nb, self, tr)
        nb.add(self.gal, text="  Galerie  ")
        logbox = tk.Frame(rpw, bg=GREEN)
        self.logbox = tk.Text(logbox, height=4, state="disabled", wrap="word", bg="#f4fff4")
        self.logbox.pack(fill="both", expand=True)
        rpw.add(logbox, minsize=40, stretch="never", height=70)
        bar = tk.Frame(right, bg=GREEN_DARK)
        bar.pack(fill="x", pady=(2, 0))
        tk.Label(bar, textvariable=self.v_state, bg=GREEN_DARK, fg="white",
                 font=("TkDefaultFont", 9, "bold")).pack(side="left", padx=6)
        self.lb_clock = tk.Label(bar, text="", bg=GREEN_DARK, fg="white", cursor="hand2",
                                 font=("TkDefaultFont", 9, "bold"))
        self.lb_clock.pack(side="right", padx=6)
        self.lb_clock.bind("<Button-1>", lambda e: self._clock_cycle())
        # hommage à Erik Sundstrup VK4AES (SK), créateur d'EasyPal : petit drapeau australien
        try:
            import flag
            self._flag_ph = ImageTk.PhotoImage(flag.australia(24, 12))
        except Exception:
            self._flag_ph = None
        self.lb_tribute = tk.Label(bar, text=" En hommage à VK4AES", image=self._flag_ph, compound="left",
                                   bg=GREEN_DARK, fg="white", cursor="hand2", font=("TkDefaultFont", 8, "bold"))
        self.lb_tribute.pack(side="right", padx=8)
        self.lb_tribute.bind("<Button-1>", lambda e: self.show_tribute())
        tip(self.lb_tribute, "Erik Sundstrup VK4AES (SK), créateur d'EasyPal")
        self.lb_freq = tk.Label(bar, text="", bg=GREEN_DARK, fg="#ffe066", font=("TkDefaultFont", 9, "bold"))
        # clic sur la fréquence (barre d'état ou panneau) : menu des fréquences image (CAT)
        for w in (self.lb_freq, self.panel.freq):
            w.configure(cursor="hand2")
            w.bind("<Button-1>", self._freq_menu)
            tip(w, "Cliquez pour changer de fréquence")
        self.lb_freq.pack(side="right", padx=12)

        self._tab_conf()            # fenêtres Réglages et Texte (cachées)
        self._build_text_window()
        self._build_wav_window()
        self._build_wft_window()
        # ---------------- fenêtres séparées (menu Fenêtres)
        d = self.dock = docking.Dock(self, APP, on_change=self._dock_changed, tr=tr)
        d.add_pack("commandes", "Panneau et boutons", ctl, [ctl, lpw], fill="x")
        d.add_pane("waterfall", "Waterfall", wfbox, lpw, [wfbox, sbox], minsize=90, stretch="always")
        d.add_pane("liste", "Stations entendues", sbox, lpw, [wfbox, sbox], minsize=80, stretch="never")
        # onglets RX, TX, Simulation et le journal restent dans la fenêtre principale
        self.tab_frames = {"rx": self.tab_rx, "tx": self.tab_tx, "stations": self.tab_stations,
                           "sim": self.tab_sim, "gal": self.gal}
        tabs = list(self.tab_frames.values())
        for name, title, text in (("stations", "Stations", "  Stations  "), ("gal", "Galerie", "  Galerie  ")):
            d.add_tab(name, title, self.tab_frames[name], nb, text, tabs)
        self._menus()
        self._translate_ui()
        hybrid.set_max_download(self.conf.get("hyb_rx_max_mb", 200))
        try:
            # glisser-déposer depuis l'Explorateur Windows, n'importe où sur la fenêtre
            if not dropfiles.hook(self, dropfiles.all_widgets(self), self._dropped):
                self.log("Glisser-déposer indisponible (tkinterdnd2 absent).")
        except Exception as e:
            self.log(f"Glisser-déposer indisponible : {e}")

    # ------------------------------------------------------------------ fenêtres séparées
    def _dock_changed(self):
        for n, v in getattr(self, "v_dock", {}).items():
            v.set(self.dock.detached(n))
        self.conf["detached"] = self.dock.saved()

    def show_tab(self, name, focus=True):
        """Montre un onglet : dans la fenêtre principale, ou sa fenêtre séparée (au premier plan
        si focus)."""
        if self.dock.detached(name):
            if focus:
                self.dock.show(name)
            return
        self.nb.select(self.tab_frames[name])

    def _tab_shown(self, name):
        """L'onglet est-il celui affiché dans la fenêtre principale ?"""
        if self.dock.detached(name):
            return False
        try:
            return self.nb.select() == str(self.tab_frames[name])
        except tk.TclError:
            return False

    # ------------------------------------------------------------------ apparence
    def _font_menu(self):
        """Menu Réglages → Police et taille du texte : gras et taille, appliqués tout de suite."""
        self.conf["font_bold"] = bool(self.v_fbold.get())
        size = self.v_msize.get()
        if hasattr(self, "v_fsize"):
            self.v_fsize.set(tr(size))
        else:
            self.conf["font_size"] = size
        self._apply_look()
        self._save_conf_file()

    def _apply_look(self, save=True):
        """Thème de couleurs et police choisis dans les Réglages (appliqués tout de suite)."""
        th = self._theme_names.get(self.v_theme.get(), self.v_theme.get()) if hasattr(self, "v_theme") \
            else self.conf.get("theme", "Vert EasyPal")
        fam = self.v_font.get() if hasattr(self, "v_font") else self.conf.get("font_family")
        size = self._size_names.get(self.v_fsize.get(), "9") if hasattr(self, "v_fsize") \
            else theme.size_name(self.conf.get("font_size", "9"))
        modern = None
        if hasattr(self, "v_lookstyle"):
            self.conf["look_style"] = "moderne" if self.v_lookstyle.get() == tr("Moderne") else "classique"
            amb = self._modern_names.get(self.v_modern.get(), self.v_modern.get())
            if amb in theme.MODERN:
                self.conf["modern_theme"] = amb
        if self.conf.get("look_style") == "moderne":
            modern = self.conf.get("modern_theme") if self.conf.get("modern_theme") in theme.MODERN else "Vert EasyPal"
        self.look.set(theme=th if th in theme.THEMES or th == "Personnalisée" else "Vert EasyPal",
                      custom=self.conf.get("theme_color"), family=fam,
                      scale=theme.FONT_SIZES.get(size, 1.0), text=self.conf.get("text_color") or "",
                      bold=bool(self.conf.get("font_bold")), modern=modern)
        # boutons de la grille : couleur selon leur état, dans le style choisi
        for b in getattr(self, "gbtn", {}).values():
            st = getattr(b, "_hf_state", "off")
            if not modern:                             # Classique : boutons texte, comme avant
                b.configure(image="", compound="none", padx=1, pady=1)
            if modern or st != "off":                  # Classique : boutons au repos laissés au thème
                self._btn_color(b, st)
        self._data_auto_paint()
        self._topbar_show()
        self._cards(self.look.palette())
        self.conf.update(theme=th, font_family=fam, font_size=size)
        if hasattr(self, "v_msize") and self.v_msize.get() != size:
            self.v_msize.set(size)
        try:
            self.wf.configure(bg="#000")
        except Exception:
            pass
        # police plus grande : on élargit la colonne de gauche pour que les boutons restent lisibles
        try:
            want = int(268 * theme.FONT_SIZES.get(size, 1.0) * (1.08 if fam not in ("", "(par défaut)") else 1.0))
            p = self.panes["main"]
            if p.sash_coord(0)[0] < want:
                self.after(100, lambda: p.sash_place(0, want, 0))
        except (tk.TclError, KeyError, AttributeError):
            pass
        if hasattr(self, "lst_heard"):
            self._heard_refresh()
        if save:
            try:
                with open(CONF_PATH, "w", encoding="utf-8") as f:
                    json.dump(self.conf, f, indent=1)
            except Exception:
                pass

    def _pick_color(self):
        from tkinter import colorchooser
        c = colorchooser.askcolor(color=self.conf.get("theme_color", "#3a8ee6"), parent=self.win_conf,
                                  title=tr("Couleur des fenêtres"))
        if c and c[1]:
            self.conf["theme_color"] = c[1]
            self.v_theme.set(tr("Personnalisée"))
            self._apply_look()

    def _pick_text_color(self):
        from tkinter import colorchooser
        c = colorchooser.askcolor(color=self.conf.get("text_color") or "#000000", parent=self.win_conf,
                                  title=tr("Couleur du texte"))
        if c and c[1]:
            self.conf["text_color"] = c[1]
            self._text_swatch()
            self._apply_look()

    def _reset_text_color(self):
        self.conf["text_color"] = ""
        self._text_swatch()
        self._apply_look()

    def _text_swatch(self):
        if hasattr(self, "sw_text"):
            c = self.conf.get("text_color") or ""
            self.sw_text.configure(bg=c or "#d9d9d9", text="" if c else tr("thème"))

    # ------------------------------------------------------------------ barre du haut (style Moderne, 1.54)
    def _build_topbar(self):
        """Barre du haut du style Moderne : indicatif, fréquence en grand, état, stations en ligne,
        heure. Cachée en style Classique."""
        bar = self.topbar = tk.Frame(self, height=52)
        bar._no_theme = True
        self.tb = {}

        def lab(key, side="left", padx=(0, 0), font=None, cursor=None):
            w = tk.Label(bar, text="", font=font or ("TkDefaultFont", 10), cursor=cursor or "")
            w._no_theme = True
            w.pack(side=side, padx=padx, pady=8)
            self.tb[key] = w
            return w
        lab("logo", padx=(14, 6), font=("TkDefaultFont", 10, "bold")).configure(text=" HF ")
        lab("app", padx=(0, 18), font=("TkDefaultFont", 13, "bold")).configure(text="HFImage")
        lab("call", padx=(0, 6), font=("TkDefaultFont", 13, "bold"))
        lab("who", padx=(0, 22))
        f = lab("freq", padx=(0, 4), font=("TkDefaultFont", 18, "bold"), cursor="hand2")
        f.bind("<Button-1>", lambda e: self._freq_menu(e))
        m = lab("mode", padx=(0, 22), cursor="hand2")
        m.bind("<Button-1>", lambda e: self._freq_menu(e))
        lab("state", padx=(0, 12), font=("TkDefaultFont", 10, "bold"))
        o = lab("online", padx=(0, 12), cursor="hand2")
        o.bind("<Button-1>", lambda e: self.show_map())
        lab("clock", side="right", padx=(0, 16), font=("TkDefaultFont", 11, "bold"))

    def _cards(self, P):
        """Style Moderne : colonne de gauche en « cartes » (bordure fine, marges) ; Classique : comme avant."""
        if not hasattr(self, "_st_box"):
            return
        try:
            self.panel.set_modern(P)
            m = 4 if P else 0
            self.panel.pack_configure(padx=m, pady=(m, 0))
            self._grid_frame.pack_configure(padx=m, pady=(6, 0))
            lpw = self.panes["left"]
            for w in (self._wfbox, self._sbox):
                lpw.paneconfigure(w, padx=m, pady=(3 if P else 0))
            for w in (self.panel, self._st_box):
                if P:
                    w.configure(highlightthickness=1, highlightbackground=P["border"], highlightcolor=P["border"])
            if P:
                self._grid_frame.configure(bg=P["bg"])
        except (tk.TclError, AttributeError):
            pass

    def _topbar_show(self):
        if not hasattr(self, "topbar"):
            return
        P = self.look.palette()
        if not P:
            self.topbar.pack_forget()
            return
        fam = self.look._family() or "TkDefaultFont"
        k = self.look.scale
        top = P["top"]
        self.topbar.configure(bg=top, highlightthickness=1, highlightbackground=P["border"])
        fonts = {"logo": (fam, int(10 * k), "bold"), "app": (fam, int(13 * k), "bold"),
                 "call": (fam, int(13 * k), "bold"), "who": (fam, int(10 * k)),
                 "freq": (fam, int(18 * k), "bold"), "mode": (fam, int(10 * k)),
                 "state": (fam, int(10 * k), "bold"), "online": (fam, int(10 * k)),
                 "clock": (fam, int(11 * k), "bold")}
        for key, w in self.tb.items():
            w.configure(bg=top, fg=P.get("top_fg", P["fg"]), font=fonts[key])
        self.tb["logo"].configure(bg=P["accent"], fg=P["accent_fg"])
        for key in ("who", "mode", "online"):
            self.tb[key].configure(fg=P.get("top_muted", P["muted"]))
        if not self.topbar.winfo_manager():
            self.topbar.pack(fill="x", before=self._main_pane)
        self._topbar_update()

    def _topbar_update(self):
        """Contenu de la barre du haut (appelé chaque seconde par l'horloge)."""
        if not hasattr(self, "topbar") or not self.topbar.winfo_manager():
            return
        P = self.look.palette() or theme.MODERN["Vert EasyPal"]
        tb = self.tb
        tb["call"].configure(text=self.mycall() or "—")
        who = " · ".join(x for x in (self.myname(), self.v_loc.get().strip().upper()) if x)
        tb["who"].configure(text=who)
        fr = self.rig_freq
        tb["freq"].configure(text=f"{fr / 1e6:.3f}" if fr else "—.———")
        tb["mode"].configure(text=("MHz · " + str(self.rig_mode)) if fr and self.rig_mode else ("MHz" if fr else tr("Fréquence ▾")))
        if self.tx_busy:
            st, bg, fg = "●  " + tr("ÉMISSION"), P["bad"], "#ffffff"
        elif getattr(self, "_wait_job", None):
            st, bg, fg = "●  " + tr("ATTENTE…"), "#ffb84d", "#1a1a1a"
        elif self.rx_stream is not None:
            st, bg, fg = "●  " + tr("RÉCEPTION"), P["accent"], P["accent_fg"]
        else:
            st, bg, fg = "●  " + tr("Réception arrêtée"), P["button"], P["muted"]
        tb["state"].configure(text=f" {st} ", bg=bg, fg=fg)
        n = len({str(d.get("call")).upper() for d in self.online.values()}) if getattr(self, "online", None) else 0
        tb["online"].configure(text=f"🌐 {n} " + tr("en ligne") if self.net is not None else "")
        tb["clock"].configure(text=time.strftime("%H:%M", time.gmtime()) + " UTC")

    def _c(self, color):
        """Couleur de texte d'origine adaptée au thème (éléments de listes)."""
        return self.look.map(color, "foreground") if hasattr(self, "look") else color

    def _set_text(self, w, fr):
        """Texte d'un widget, donné en français : gardé pour les changements de langue."""
        self._orig[str(w)] = fr
        w.configure(text=tr(fr))

    def _translate_ui(self, root=None):
        """(Re)traduit tous les textes fixes de l'interface à partir du français d'origine."""
        if root is not None and hasattr(self, "look"):
            self.after_idle(lambda r=root: self.look.apply(r) if r.winfo_exists() else None)
        stack = [root or self]
        while stack:
            w = stack.pop()
            stack.extend(w.winfo_children())
            key = str(w)
            if isinstance(w, tk.Menu):
                try:
                    last = w.index("end")
                except tk.TclError:
                    last = None
                for i in range(0, (last if last is not None else -1) + 1):
                    if w.type(i) in ("command", "cascade", "checkbutton", "radiobutton"):
                        k = (key, i)
                        orig = self._orig.setdefault(k, w.entrycget(i, "label"))
                        w.entryconfigure(i, label=tr(orig))
                continue
            if isinstance(w, ttk.Notebook):
                for i, tab in enumerate(w.tabs()):
                    orig = self._orig.setdefault((key, "tab", i), w.tab(tab, "text"))
                    w.tab(tab, text=tr(orig))
            if isinstance(w, ttk.Treeview):
                for c in w["columns"]:
                    orig = self._orig.setdefault((key, "col", c), w.heading(c, "text"))
                    w.heading(c, text=tr(orig))
            if isinstance(w, ImageView):
                orig = self._orig.setdefault((key, "ph"), w.placeholder)
                w.placeholder = tr(orig)
                w._redraw()
            if isinstance(w, tk.Toplevel):
                orig = self._orig.setdefault((key, "title"), w.title())
                w.title(tr(orig))
            try:
                t = w.cget("text")
            except (tk.TclError, AttributeError):
                continue
            if isinstance(t, str) and t:
                orig = self._orig.setdefault(key, t)
                w.configure(text=tr(orig))

    def set_language(self, code):
        i18n.set_lang(code)
        if hasattr(self, "v_lang"):
            self.v_lang.set(i18n.LANGS.get(code, "Français"))
        self.conf["lang"] = code
        self._translate_ui()
        for v in (self.v_state, self.v_txinfo, getattr(self, "v_sim", None)):
            if isinstance(v, TrVar):
                v.retranslate()
        self.save_conf(quiet=True)
        self.log("Langue changée.")

    def mycall(self):
        """Notre indicatif (premier mot de la case : un prénom tapé derrière n'en fait pas partie)."""
        return split_call(self.v_call.get())[0]

    def myname(self):
        """Prénom affiché dans les listes des autres stations (case Prénom, sinon ce qui suit
        l'indicatif dans la case indicatif)."""
        try:
            n = self.v_opname.get().strip()
        except AttributeError:
            n = ""
        return (n.title()[:16] if n else split_call(self.v_call.get())[1])

    def _set_title(self):
        self.title(f"{APP} {VERSION} — {self.mycall() or 'NOCALL'}"
                   + (f" — {PROFILE}" if PROFILE else ""))

    # ---------------------------------------------------------------- menus
    def _menus(self):
        m = tk.Menu(self)
        r = tk.Menu(m, tearoff=0)
        r.add_command(label="Réglages…", command=self.show_settings)
        r.add_command(label="Assistant de démarrage…", command=self.setup_wizard)
        r.add_command(label="Ouvrir une autre instance (profil)…", command=self.new_instance)
        r.add_separator()
        r.add_command(label="Tester la sortie audio (1 kHz)", command=self.test_audio)
        r.add_command(label="Poste radio…", command=self.radio_dialog)
        r.add_command(label="Vérifier le poste (CAT)", command=self.check_rig)
        r.add_command(label="Tester le PTT (1 s)", command=self.test_ptt)
        r.add_separator()
        pm = tk.Menu(r, tearoff=0)
        pm.add_checkbutton(label="Texte en gras", variable=self.v_fbold, command=self._font_menu)
        pm.add_separator()
        for n in theme.FONT_SIZES:
            pm.add_radiobutton(label=f"{n} points" + (" (normale)" if n == "9" else ""), value=n,
                               variable=self.v_msize, command=self._font_menu)
        pm.add_separator()
        pm.add_command(label="Police, couleurs…", command=self.show_settings)
        r.add_cascade(label="Police et taille du texte", menu=pm)
        r.add_separator()
        r.add_command(label="Enregistrer les réglages", command=self.save_conf)
        r.add_command(label="Ouvrir le journal", command=self.open_journal)
        r.add_separator()
        r.add_command(label="Disposition d'origine des fenêtres", command=self.reset_layout)
        m.add_cascade(label="Réglages", menu=r)
        fw = tk.Menu(m, tearoff=0)
        fw.add_checkbutton(label="Afficher l'historique (onglet RX)", variable=self.v_show_hist,
                           command=lambda: self._rx_side_apply(save=True))
        fw.add_checkbutton(label="Afficher les messages reçus (onglet RX)", variable=self.v_show_msgs,
                           command=lambda: self._rx_side_apply(save=True))
        fw.add_separator()
        self.v_dock = {}
        for n in self.dock.order:
            v = self.v_dock[n] = tk.BooleanVar(value=self.dock.detached(n))
            fw.add_checkbutton(label=self.dock.zones[n]["title"], variable=v,
                               command=lambda n=n: self.dock.toggle(n))
        fw.add_separator()
        fw.add_command(label="Tout remettre dans la fenêtre principale", command=self.dock.attach_all)
        m.add_cascade(label="Fenêtres", menu=fw)
        h = tk.Menu(m, tearoff=0)
        h.add_checkbutton(label="Mode hybride", variable=self.v_hyb, command=self._toggle_hyb_ui)
        h.add_command(label="Tester le serveur", command=self.test_hybrid)
        h.add_checkbutton(label="Télécharger automatiquement", variable=self.v_hauto)
        h.add_command(label="Réglages du serveur…", command=self.show_settings)
        m.add_cascade(label="Hybride", menu=h)
        a = tk.Menu(m, tearoff=0)
        a.add_command(label="Émettre", command=lambda: self._tx_when_free(self.transmit, tr("image")))
        a.add_command(label="FIX / Compléter", command=self.send_fix)
        a.add_command(label="Arrêter l'émission", command=lambda: self.stop_tx.set())
        a.add_separator()
        a.add_command(label="BSR (demander la suite)", command=self.send_bsr_manual)
        a.add_command(label="Écoute marche / arrêt", command=self.toggle_listen)
        a.add_separator()
        a.add_command(label="Accord (10 s)", command=self.send_tune)
        a.add_command(label="ID morse", command=self.send_cwid)
        a.add_command(label="Envoi texte…", command=self.show_text)
        a.add_command(label="Messages reçus…", command=self.show_messages)
        a.add_command(label="Texte waterfall…", command=self.show_wft)
        a.add_separator()
        a.add_command(label="Signaler ma présence (QRV)", command=self.send_qrv)
        a.add_command(label="Carte des stations…", command=self.show_map)
        a.add_command(label="Sites des stations…", command=self.show_sites)
        self.qsy_menu = tk.Menu(a, tearoff=0, postcommand=lambda: self._fill_qsy_menu(self.qsy_menu))
        a.add_cascade(label="Aller sur une fréquence", menu=self.qsy_menu)
        m.add_cascade(label="Action", menu=a)
        i = tk.Menu(m, tearoff=0)
        i.add_command(label="Ouvrir une image…", command=self.open_image)
        i.add_command(label="Envoyer un fichier…", command=self.send_file)
        i.add_command(label="Mes conditions de trafic…", command=self.trafic_dialog)
        i.add_command(label="Image du correspondant…", command=self.pip_dialog)
        i.add_command(label="Bulles de texte…", command=self.bubble_dialog)
        i.add_command(label="Carte QSL…", command=self.qsl_dialog)
        i.add_separator()
        i.add_command(label="Image reçue en plein format", command=self._open_full)
        i.add_command(label="Dossier des images reçues", command=self.open_folder)
        i.add_command(label="Galerie des dernières images", command=lambda: self.show_tab("gal"))
        i.add_command(label="Site web / Digi-Sites…", command=self.web_dialog)
        i.add_command(label="Sites des stations…", command=self.show_sites)
        m.add_cascade(label="Images", menu=i)
        f = tk.Menu(m, tearoff=0)
        f.add_command(label="Enregistrer l'émission en WAV…", command=self.save_wav)
        f.add_command(label="Décoder et analyser un fichier WAV…", command=self.decode_wav)
        f.add_command(label="Relire RX (15 dernières min)", command=self.replay_rx)
        f.add_command(label="Fichiers WAV (begin / end)…", command=self.show_wav)
        f.add_command(label="Enregistrement WAVE marche / arrêt", command=self.toggle_record)
        f.add_separator()
        f.add_command(label="Journal des stations (CSV)",
                      command=lambda: self._open_path(os.path.join(DEFAULT_OUT, "stations.csv")))
        f.add_separator()
        # 0.97 : l'onglet Simulation (outil d'essai) n'est plus affiché d'office
        self.v_simtab = tk.BooleanVar(value=bool(self.conf.get("show_sim", False)))
        f.add_checkbutton(label="Onglet Simulation (canal HF simulé)", variable=self.v_simtab,
                          command=self._sim_tab_toggle)
        e = tk.Menu(f, tearoff=0)
        e.add_command(label="Historique des images", command=self._clear_hist)
        e.add_command(label="Messages reçus", command=lambda: self._clear_text(self.msgbox))
        e.add_command(label="Journal des stations", command=lambda: self.tree.delete(*self.tree.get_children()))
        e.add_command(label="Waterfall", command=lambda: self.wf.clear())
        e.add_command(label="Journal à l'écran", command=lambda: self._clear_text(self.logbox))
        f.add_cascade(label="Effacer", menu=e)          # 0.97 : sous-menu de Fichiers
        m.add_cascade(label="Fichiers", menu=f)
        self._sim_tab_toggle(save=False)
        n = tk.Menu(m, tearoff=0)
        n.add_command(label="Mode d'emploi (PDF)", command=self.open_manual)
        n.add_command(label="Mode d'emploi en anglais (PDF)",
                      command=lambda: self.open_manual("HFImage_user_manual_EN.pdf"))
        n.add_command(label="Rechercher une mise à jour", command=lambda: self.update_check(quiet=False))
        n.add_command(label="Page du programme sur GitHub",
                      command=lambda: __import__("webbrowser").open(f"https://github.com/{updater.REPO}"))
        n.add_separator()
        n.add_command(label="À propos…", command=self._about)
        n.add_command(label="Licence (GNU GPL v3)", command=self._license)
        m.add_cascade(label="Infos", menu=n)
        self.config(menu=m)

    def _sim_tab_toggle(self, save=True):
        """Onglet Simulation affiché ou caché (menu Fichiers)."""
        on = bool(self.v_simtab.get())
        try:
            if on:
                self.nb.add(self.tab_sim)                 # réaffiche l'onglet caché, à sa place
                if save:
                    self.nb.select(self.tab_sim)
            else:
                if self.nb.select() == str(self.tab_sim):
                    self.nb.select(self.tab_rx)
                self.nb.hide(self.tab_sim)
        except tk.TclError:
            pass
        if save:
            self.conf["show_sim"] = on
            self._save_conf_file()

    def _about(self):
        messagebox.showinfo(APP, f"{APP} {VERSION}" + (" (Windows 7 / 8)" if updater.LEGACY else "") + ("" if updater.WIN else " (Linux)")
                            + "\n\nImages numériques en HF : modem OFDM codec2 "
                                 "(DATAC1X / DATAC1 / DATAC3 / DATAC4, BSR/ACK en DATAC0), code fontaine, "
                                 "mode hybride par Internet.\n\nAutotests :\n"
                                 "  HFImage_F4GOP.exe --selftest rapport.txt\n"
                                 "  HFImage_F4GOP.exe --audiotest test.txt \"USB Audio CODEC\""
                            + "\n\n© 2026 Denis F4GOP — logiciel libre et gratuit, licence GNU GPL v3 : "
                                 "vous pouvez l'utiliser, le copier, le partager et le modifier ; une version modifiée "
                                 "doit rester sous la même licence, avec ses sources, sans reprendre le nom "
                                 "HFImage F4GOP (fichier LICENCE.txt).\n"
                                 "Sources et licence : github.com/f4gopdenis-cyber/HFImage_F4GOP\n"
                                 "Modem EasyPal d'après QSSTV (ON4QZ), modems DATAC : codec2 (VK5DGR)."
                            + "\n\nConçu, choisi et testé sur l'air par Denis F4GOP ; code écrit en grande partie "
                              "avec l'aide de l'intelligence artificielle Claude (Anthropic).\n"
                              "Programme dédié à Erik VK4AES (SK), créateur d'EasyPal.")

    TRIBUTE_LOGO = "hommage_vk4aes.jpg"

    def show_tribute(self):
        """Clic sur le drapeau australien de la barre du bas : la dédicace, avec le logo
        d'hommage dessiné par Denis F4GOP."""
        text = tr("HFImage est dédié à la mémoire d'Erik Sundstrup VK4AES (SK), "
                  "radioamateur australien et créateur d'EasyPal, en hommage à son travail "
                  "pour l'image numérique en HF.") + "\n\n— Denis F4GOP"
        w = getattr(self, "_tribute_win", None)
        if w is not None and w.winfo_exists():
            w.lift()
            return w
        here = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        try:
            logo = Image.open(os.path.join(here, self.TRIBUTE_LOGO)).convert("RGB")
        except Exception:
            messagebox.showinfo(APP, text)
            return None
        w = self._tribute_win = tk.Toplevel(self)
        w.title(tr("En hommage à VK4AES"))
        w.transient(self)
        w.resizable(False, False)
        w.configure(bg="black")
        ph = ImageTk.PhotoImage(logo)
        lbl = tk.Label(w, image=ph, bg="black", bd=0)
        lbl.image = ph
        lbl._no_theme = True
        lbl.pack(padx=12, pady=(12, 6))
        t = tk.Label(w, text=text, bg="black", fg="#f2d16b", wraplength=logo.width,
                     justify="center", font=("TkDefaultFont", 10))
        t._no_theme = True
        t.pack(padx=12, pady=(0, 8))
        ttk.Button(w, text="OK", command=w.destroy).pack(pady=(0, 12))
        w.bind("<Escape>", lambda e: w.destroy())
        return w

    LICENCE_VERSION = "1.0"

    @staticmethod
    def _launch_cmd(profile):
        """Commande qui lance HFImage avec ce profil (exe, ou python app.py depuis les sources)."""
        if getattr(sys, "frozen", False):
            return [sys.executable, "--profil", profile]
        return [sys.executable, os.path.abspath(__file__), "--profil", profile]

    def new_instance(self):
        """Réglages → Ouvrir une autre instance : un autre HFImage avec ses propres réglages
        (par ex. un récepteur sur 20 m pendant que celui-ci écoute le 40 m)."""
        from tkinter import simpledialog
        name = simpledialog.askstring(
            APP, tr("Nom du profil (ex. 20m, 28MHz) : chaque profil garde ses propres réglages "
                    "(entrée audio, poste, dossier des images)."), parent=self)
        if name is None:
            return
        prof = re.sub(r"[^A-Za-z0-9_-]", "", name)[:16]
        if not prof:
            messagebox.showerror(APP, tr("Nom de profil vide : lettres, chiffres, - ou _."))
            return
        if prof == PROFILE:
            messagebox.showinfo(APP, tr("Ce profil est déjà celui de cette fenêtre."))
            return
        cmd = self._launch_cmd(prof)
        try:
            subprocess.Popen(cmd, close_fds=True)
        except OSError as e:
            messagebox.showerror(APP, tr("Lancement impossible :") + f" {e}")
            return
        self.log(tr("Instance lancée :") + f" {prof}")
        if messagebox.askyesno(
                APP, tr("Créer un raccourci sur le Bureau pour ouvrir directement ce profil ?")):
            try:
                self._desktop_shortcut(prof, cmd)
            except Exception as e:
                self.log_exc("Raccourci du profil", e)
                messagebox.showerror(APP, tr("Raccourci impossible :") + f" {e}")

    @staticmethod
    def _desktop_shortcut(prof, cmd):
        if not sys.platform.startswith("win"):
            linux_menu_entry(cmd, f"HFImage {prof}", f"hfimage-f4gop-{prof}", desktop=True)
            return
        import comtypes.client
        shell = comtypes.client.CreateObject("WScript.Shell", dynamic=True)
        desk = shell.SpecialFolders("Desktop")
        lnk = shell.CreateShortcut(os.path.join(desk, f"HFImage {prof}.lnk"))
        lnk.TargetPath = cmd[0]
        lnk.Arguments = subprocess.list2cmdline(cmd[1:])
        lnk.WorkingDirectory = os.path.dirname(cmd[0])
        lnk.Description = f"HFImage F4GOP — {prof}"
        lnk.Save()

    def _startup_dialogs(self):
        self._licence_first_run()
        try:
            if self.winfo_exists() and (self.first_run or not self.v_call.get().strip()):
                self.setup_wizard()               # premier démarrage : indicatif, carte son, poste
        except tk.TclError:
            pass

    def setup_wizard(self):
        """Réglages → Assistant de démarrage… (3 étapes)."""
        w = getattr(self, "_wiz", None)
        if w is not None and w.winfo_exists():
            w.lift()
            return
        self._wiz = setupwiz.SetupWizard(self)
        self._translate_ui(self._wiz)

    def _licence_first_run(self):
        """Premier démarrage (ou nouvelle version de la licence) : la licence s'affiche,
        « J'accepte » pour continuer, « Je refuse » ferme le programme."""
        if self.conf.get("licence_ok") == self.LICENCE_VERSION:
            return
        here = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        try:
            with open(os.path.join(here, "LICENCE.txt"), encoding="utf-8") as f:
                text = f.read()
        except OSError:
            text = ("HFImage F4GOP — © 2026 Denis F4GOP — logiciel libre et gratuit, licence GNU GPL v3.\n"
                    "https://github.com/f4gopdenis-cyber/HFImage_F4GOP/blob/main/LICENCE.txt")
        w = tk.Toplevel(self)
        w.title(tr("Licence d'utilisation"))
        w.transient(self)
        w.geometry("760x560")
        w.minsize(520, 360)
        f = ttk.Frame(w, padding=12)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text="Licence d'utilisation (logiciel libre et gratuit)",
                  font=("TkDefaultFont", 12, "bold")).pack(anchor="w")
        ttk.Label(f, text="Le programme est gratuit. Avant la première utilisation, lisez la licence ci-dessous "
                          "et cliquez « J'accepte » pour continuer.", wraplength=720,
                  justify="left").pack(anchor="w", pady=(2, 8))
        b = ttk.Frame(f)
        b.pack(side="bottom", fill="x", pady=(10, 0))
        box = ttk.Frame(f)
        box.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(box, orient="vertical")
        t = tk.Text(box, wrap="word", yscrollcommand=sb.set, padx=8, pady=6, font=("TkDefaultFont", 9))
        sb.configure(command=t.yview)
        sb.pack(side="right", fill="y")
        t.pack(side="left", fill="both", expand=True)
        t.insert("1.0", text)
        t.configure(state="disabled")
        res = {"ok": False}

        def done(ok):
            res["ok"] = ok
            w.destroy()

        ttk.Button(b, text="J'accepte", command=lambda: done(True)).pack(side="right")
        ttk.Button(b, text="Je refuse", command=lambda: done(False)).pack(side="right", padx=8)
        w.protocol("WM_DELETE_WINDOW", lambda: done(False))
        self._translate_ui(w)
        w.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - w.winfo_width()) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - w.winfo_height()) // 3)
        w.geometry(f"+{x}+{y}")
        w.grab_set()
        self.wait_window(w)
        if res["ok"]:
            self.conf["licence_ok"] = self.LICENCE_VERSION
            self._save_conf_file()
            self.log("Licence acceptée (LICENCE.txt, menu Infos → Licence).")
        else:
            self._quit()

    def _license(self):
        """Licence (en français, conditions de F4GOP) + texte officiel de la GPL v3, copiés dans
        Documents\\HFImage pour rester ouvrables."""
        here = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        try:
            os.makedirs(DEFAULT_OUT, exist_ok=True)
            shutil.copyfile(os.path.join(here, "LICENSE.txt"), os.path.join(DEFAULT_OUT, "LICENSE_GPL-3.0.txt"))
            dst = os.path.join(DEFAULT_OUT, "LICENCE.txt")
            shutil.copyfile(os.path.join(here, "LICENCE.txt"), dst)
            self._open_path(dst)
        except OSError:
            webbrowser.open("https://github.com/f4gopdenis-cyber/HFImage_F4GOP/blob/main/LICENCE.txt")

    def _open_path(self, p):
        if not os.path.exists(p):
            messagebox.showinfo(APP, f"Pas encore de fichier :\n{p}")
            return
        if sys.platform.startswith("win"):
            os.startfile(p)
        else:
            subprocess.Popen(["xdg-open", p])

    def _clear_text(self, w):
        w.configure(state="normal")
        w.delete("1.0", "end")
        w.configure(state="disabled")

    def _clear_hist(self):
        self.hist.clear()
        self.lst.delete(0, "end")

    # ---------------------------------------------------------------- boutons
    def _button_grid(self, parent):
        g = self._grid_frame = tk.Frame(parent, bg=GREEN)
        g.pack(fill="x", pady=(6, 0))
        self.gbtn = {}
        spec = [
            ("tx", "ÉMISSION", self._btn_emission), ("relire", "Relire RX", self.replay_rx),
            ("fix", "FIX", self.send_fix), ("bsr", "BSR", self.send_bsr_manual),
            ("accord", "Accord", self.send_tune), ("id", "ID", self.send_cwid),
            ("texte", "Envoi Texte", self.show_text), ("wave", "WAVE", self.show_wav),
            ("ecoute", "Écoute", self.toggle_listen), ("txtinc", "Txt inclus", self._toggle_txtinc),
            ("log", "Log Station", lambda: self.show_tab("stations")), ("qsl", "IMG/QSL", self.qsl_dialog),
            ("image", "Image…", self.open_image), ("hyb", "Hybride", self._toggle_hyb_btn),
            ("reglages", "Réglages", self.show_settings), ("dossier", "Dossier", self.open_folder),
        ]
        for k, (key, text, cmd) in enumerate(spec):
            b = tk.Button(g, text=text, command=cmd, bg="white", activebackground="#e6ffe6",
                          relief="raised", bd=1, font=("TkDefaultFont", 8), padx=1, pady=1)
            b.grid(row=k // 4, column=k % 4, sticky="nsew", padx=1, pady=1)
            b._hf_key = key
            self.gbtn[key] = b
        for c in range(4):
            g.columnconfigure(c, weight=1, uniform="b")
        self.gbtn["tx"].bind("<Button-3>", self._btn_emission_force)
        self.v_waitfree = tk.BooleanVar(value=self.conf.get("wait_free", True))
        row = tk.Frame(parent, bg=GREEN)
        row.pack(fill="x")
        # bouton bien visible pour changer de fréquence (le clic sur la fréquence affichée
        # n'était pas trouvé par beaucoup d'utilisateurs)
        bq = tk.Button(row, text="Fréquence ▾", font=("TkDefaultFont", 8), bg="white", cursor="hand2",
                       padx=6, pady=0, command=lambda: self._freq_menu_at(bq))
        bq.pack(side="right", padx=(4, 2), pady=1)
        tip(bq, "Cliquez pour changer de fréquence")
        tk.Checkbutton(row, text="Attendre fréquence libre", variable=self.v_waitfree, bg=GREEN,
                       activebackground=GREEN, font=("TkDefaultFont", 8), anchor="w",
                       command=lambda: (self.conf.__setitem__("wait_free", bool(self.v_waitfree.get())),
                                        self._save_conf_file())
                       ).pack(side="left", fill="x", expand=True)
        # compatibilité avec le reste du code
        self.btn_listen = self.gbtn["ecoute"]
        self.btn_bsr = self.gbtn["bsr"]


    def _btn_on(self, key, on):
        self._btn_color(self.gbtn[key], "on" if on else "off")

    BTN_CLASSIC = {"off": ("white", "#e6ffe6", None, "raised"), "on": (BTN_ON, None, None, "sunken"),
                   "wait": ("#ffb84d", "#ffc870", None, None), "tx": ("#ff6b6b", "#ff8f8f", None, None)}

    def _tile_icon(self, key, color, size=18):
        """Icône d'une tuile (style Moderne), gardée en mémoire par couleur."""
        import icons
        cache = self.__dict__.setdefault("_tile_icons", {})
        k = (key, color, size)
        if k not in cache:
            cache[k] = ImageTk.PhotoImage(icons.icon(key, size, color))
        return cache[k]

    def _btn_color(self, b, state):
        """Couleur d'un bouton de la grille selon son état (repos, actif, attente, émission),
        dans le style en cours (Classique : couleurs d'origine ; Moderne : palette plate)."""
        P = self.look.palette() if hasattr(self, "look") else None
        b._hf_state = state
        if P:
            bg, fg = {"off": (P["button"], P["button_fg"]), "on": (P["accent"], P["accent_fg"]),
                      "wait": ("#ffb84d", "#1a1a1a"), "tx": (P["bad"], "#ffffff")}[state]
            key = getattr(b, "_hf_key", None)
            if key == "tx" and state == "off":
                bg, fg = P["accent"], P["accent_fg"]          # l'émission : la tuile principale
            b.configure(bg=bg, fg=fg, activebackground=P["accent"] if state == "off" else bg,
                        activeforeground=P["accent_fg"] if state == "off" else fg, relief="flat")
            if key:                                           # 1.58 : boutons plats compacts, sans icône
                b.configure(image="", compound="none", padx=1, pady=3)
            return
        b._hf_state = state
        bg, abg, _, relief = self.BTN_CLASSIC[state]
        kw = {"bg": bg}
        if abg:
            kw["activebackground"] = abg
        if relief:
            kw["relief"] = relief
        b.configure(**kw)

    def _btn_emission(self):
        if getattr(self, "_wait_job", None):
            self._wait_cancel()                    # second clic pendant l'attente : annulée
        elif self.tx_busy:
            self.stop_tx.set()
        else:
            self._tx_when_free(self.transmit, tr("image"))

    # ---------------------------------------------------------------- attendre la fréquence libre
    WAIT_MAX_S = 300           # au-delà, on demande s'il faut émettre quand même
    WAIT_HOLD_S = 3.0          # fin d'un signal : la fréquence est « occupée » encore ce temps
    WAIT_SYNC_S = 0.7          # accroche du démodulateur prise en compte au-delà de ce temps (sur le
                               # bruit seul, une fausse accroche dure un bloc de 0,5 s, jamais plus)

    def _freq_busy(self):
        """Fréquence occupée par une autre station ? -> texte (qui / quoi) ou None.
        Par radio (signal DATAC ou EasyPal en cours de décodage, si l'écoute est active) et par
        Internet (station en ligne en émission sur notre fréquence, à 3 kHz près)."""
        now = time.time()
        r = self.rx_engine
        if r is not None and self.rx_stream is not None:
            for mode, m in r.modems.items():
                held = m.sync and now - getattr(m, "sync_since", 0.0) >= self.WAIT_SYNC_S
                if held or now - m.last_ok < self.WAIT_HOLD_S:
                    return f"signal {mode}"
            if r.drm is not None and now - r.drm_t < self.WAIT_HOLD_S:
                return "signal EasyPal"
        if self.rig_freq:
            mine = self.mycall()
            for d in self.online.values():
                if d.get("state") != "TX" or now - float(d.get("seen") or d.get("t") or 0) > 120:
                    continue
                call = str(d.get("call") or "").upper()
                try:
                    near = abs(int(d.get("freq")) - int(self.rig_freq)) <= 3000
                except (TypeError, ValueError):
                    near = False
                if call and call != mine and near:
                    return call
        return None

    def _tx_when_free(self, fn, what=""):
        """Émission lancée à la main : tout de suite si la fréquence est libre (ou si la case
        « Attendre fréquence libre » est décochée), sinon dès qu'elle se libère."""
        if getattr(self, "_wait_job", None):
            return None                            # une émission attend déjà
        if not self.v_waitfree.get() or self.tx_busy:
            return fn()
        who = self._freq_busy()
        if who is None:
            return fn()
        import random
        self._wait_job = {"fn": fn, "what": what, "t0": time.time(), "free": None,
                          "delay": random.uniform(2.0, 6.0), "who": who}
        self._set_text(self.gbtn["tx"], "ATTENTE…")
        self._btn_color(self.gbtn["tx"], "wait")
        self.log(tr("Fréquence occupée") + f" ({who}) : " + tr("émission en attente") + f" ({what}). "
                 + tr("Clic sur ÉMISSION : annuler ; clic droit : émettre tout de suite."))
        self._wait_tick()

    def _wait_tick(self):
        j = getattr(self, "_wait_job", None)
        if not j:
            return
        now = time.time()
        who = self._freq_busy()
        if who:
            j["free"], j["who"] = None, who
            self.v_state.set(tr("En attente : fréquence occupée") + f" ({who})")
        else:
            j["free"] = j["free"] or now
            left = j["delay"] - (now - j["free"])
            self.v_state.set(tr("Fréquence libre : émission dans") + f" {max(0, left):.0f} s")
            if left <= 0:
                self._wait_go()
                return
        if now - j["t0"] > self.WAIT_MAX_S:
            self._wait_clear()
            if messagebox.askyesno(APP, tr("La fréquence est occupée depuis 5 minutes") + f" ({who}).\n\n"
                                   + tr("Émettre quand même ?")):
                j["fn"]()
            else:
                self.log(tr("Émission en attente annulée."))
            return
        self.after(500, self._wait_tick)

    def _wait_clear(self):
        self._wait_job = None
        if not self.tx_busy:
            self._set_text(self.gbtn["tx"], "ÉMISSION")
            self._btn_color(self.gbtn["tx"], "off")
            self.v_state.set("RÉCEPTION" if self.rx_stream is not None else "")

    def _wait_go(self):
        j = self._wait_job
        self._wait_clear()
        if j:
            self.log(tr("Fréquence libre : départ de l'émission en attente."))
            j["fn"]()

    def _wait_cancel(self):
        self._wait_clear()
        self.log(tr("Émission en attente annulée."))

    def _btn_emission_force(self, event=None):
        """Clic droit sur ÉMISSION : émettre tout de suite, sans attendre."""
        if getattr(self, "_wait_job", None):
            self._wait_go()
        elif not self.tx_busy:
            self.transmit()

    def _toggle_txtinc(self):
        self.v_txtinc.set(not self.v_txtinc.get())
        if self.v_txtinc.get() and not self.txt_msg.get("1.0", "end").strip():
            self.show_text()
        self._btn_on("txtinc", self.v_txtinc.get())
        self.prepare()

    def _toggle_hyb_btn(self):
        self.v_hyb.set(not self.v_hyb.get())
        self._toggle_hyb_ui()

    def _drm_hyb_mode(self):
        """Hybride EasyPal : réglages EasyPal mis sur E / QAM4 (ceux de l'annonce, comme EasyPal) ;
        ils reviennent à leurs valeurs précédentes quand on décoche « Mode hybride »."""
        v = getattr(self, "v_drm", None)
        if not v:
            return
        hyb = bool(self.v_hyb.get()) and self.v_mode.get() == engine.DRM_MODE
        saved = getattr(self, "_drm_before_hyb", None)
        if hyb and saved is None:
            self._drm_before_hyb = {k: v[k].get() for k in ("drm_mode", "drm_qam")}
            v["drm_mode"].set("E")
            v["drm_qam"].set("QAM4")
            self.log("Hybride EasyPal : mode E / QAM4 (annonce robuste, comme EasyPal).")
        elif not hyb and saved is not None:
            for k, val in saved.items():
                v[k].set(val)
            self._drm_before_hyb = None

    def _show_pre_btn(self):
        """« Déposer maintenant » : visible en mode hybride seulement."""
        b = getattr(self, "btn_pre", None)
        if b is None:
            return
        if self.v_hyb.get():
            b.pack(side="left", padx=(4, 0))
        else:
            b.pack_forget()

    def _toggle_hyb_ui(self):
        self._show_pre_btn()
        self._drm_hyb_mode()
        self._btn_on("hyb", self.v_hyb.get())
        side = "hyb" if self.v_hyb.get() else "radio"
        if side != self._fmt_side:
            self._fmt_mem[self._fmt_side] = self.v_fmt.get()
            self._fmt_side = side
            new = self._fmt_mem.get(side) or "avif"
            if self.v_fmt.get() != new:
                self.v_fmt.set(new)
                self.log(f"Format {new} ({'hybride' if side == 'hyb' else 'radio'}).")
        if not self.tx_busy:              # pendant une émission : recalcul à la fin (_tx_done)
            self.tx = None                # l'émission prête de l'autre mode ne doit pas partir
            self.prepare()
            self._update_comp()

    def _set_fix_text(self, text):
        self._set_text(self.btn_fix, text)
        self._set_text(self.gbtn["fix"], text.replace(" symboles", ""))

    # ---------------------------------------------------------------- images
    def _show(self, label, key, pil_img):
        if isinstance(label, ImageView):
            label.set_image(pil_img)
            return
        im = pil_img.copy()
        im.thumbnail((PREVIEW, PREVIEW))
        ph = ImageTk.PhotoImage(im)
        self._photos[key] = ph
        label.configure(image=ph, text="", width=PREVIEW, height=PREVIEW)

    def _green_bar(self, parent):
        bar = tk.Frame(parent, bg=GREEN)
        bar.pack(fill="x", side="bottom")
        return bar

    def _tab_rx(self, nb):
        t = self.tab_rx = tk.Frame(nb, bg="black")
        nb.add(t, text="  RX  ")
        bar = self._green_bar(t)
        self.lb_rx_info = tk.Label(bar, text="En attente d'image…", bg=GREEN, anchor="w",
                                   font=("TkDefaultFont", 9))
        self.lb_rx_info.pack(side="left", padx=6)
        self.pb_rx = ttk.Progressbar(bar, mode="determinate", length=260)
        self.pb_rx.pack(side="right", padx=6, pady=3)
        tk.Label(bar, text="Double-clic : plein format", bg=GREEN, fg="#114411",
                 font=("TkDefaultFont", 8)).pack(side="right", padx=8)
        pw = dict(bg=GREEN_DARK, sashwidth=6, sashrelief="raised", bd=0, opaqueresize=True)
        rxp = tk.PanedWindow(t, orient="horizontal", **pw)
        rxp.pack(fill="both", expand=True)
        self.panes["rx"] = rxp
        self.lb_rx = ImageView(rxp, placeholder="En attente d'image…")
        rxp.add(self.lb_rx, minsize=250, stretch="always")
        side = tk.PanedWindow(rxp, orient="vertical", **pw)
        rxp.add(side, minsize=150, stretch="never", width=250)
        self.panes["rxside"] = side
        h1 = self._rx_hist = tk.Frame(side, bg=GREEN)
        side.add(h1, minsize=60, stretch="always")
        tk.Label(h1, text="Historique", bg=GREEN, font=("TkDefaultFont", 9, "bold")).pack(anchor="w", padx=4)
        self.lst = tk.Listbox(h1, height=12)
        self.lst.pack(fill="both", expand=True, padx=4)
        h2 = self._rx_msgs = tk.Frame(side, bg=GREEN)
        side.add(h2, minsize=60, stretch="always")
        tk.Label(h2, text="Messages reçus", bg=GREEN, font=("TkDefaultFont", 9, "bold")).pack(anchor="w", padx=4,
                                                                                              pady=(6, 0))
        self.msgbox = tk.Text(h2, height=8, wrap="word", state="disabled")
        self.msgbox.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.msgbox.bind("<Double-Button-1>", lambda e: self.show_messages())
        self.lst.bind("<<ListboxSelect>>", self._hist_select)
        self.lst.bind("<Double-Button-1>", lambda e: self._open_full())
        self.lb_rx.bind("<Double-Button-1>", lambda e: self._open_full())
        self.lb_rx.menu_cb = self._rx_menu
        self.v_rxstat = tk.StringVar(value="")
        self.v_level = tk.DoubleVar(value=0)
        self.hist = []
        self.v_show_hist = tk.BooleanVar(value=self.conf.get("rx_hist", True))
        self.v_show_msgs = tk.BooleanVar(value=self.conf.get("rx_msgs", True))
        self.after_idle(self._rx_side_apply)

    def _rx_side_apply(self, save=False):
        """Onglet RX : affiche ou masque « Historique » et « Messages reçus ». Sans aucun des
        deux, l'image reçue prend toute la largeur."""
        rxp, side = self.panes["rx"], self.panes["rxside"]
        show = [(self._rx_hist, bool(self.v_show_hist.get())), (self._rx_msgs, bool(self.v_show_msgs.get()))]
        for f, on in show:
            there = str(f) in [str(p) for p in side.panes()]
            if on and not there:
                if f is self._rx_hist and str(self._rx_msgs) in [str(p) for p in side.panes()]:
                    side.add(f, before=self._rx_msgs, minsize=60, stretch="always")
                else:
                    side.add(f, minsize=60, stretch="always")
            elif not on and there:
                side.forget(f)
        in_rxp = str(side) in [str(p) for p in rxp.panes()]
        if any(on for _, on in show) and not in_rxp:
            rxp.add(side, minsize=150, stretch="never", width=250)
        elif not any(on for _, on in show) and in_rxp:
            rxp.forget(side)
        if save:
            self.conf.update(rx_hist=bool(self.v_show_hist.get()), rx_msgs=bool(self.v_show_msgs.get()))
            self._save_conf_file()

    def _tab_tx(self, nb):
        t = self.tab_tx = tk.Frame(nb, bg="black")
        nb.add(t, text="  TX  ")
        tb = ttk.Frame(t, padding=(6, 4))
        tb.pack(fill="x", side="top")
        self.v_mode = tk.StringVar(value=self.conf["mode"] if self.conf["mode"] in TX_MODES else "Auto")
        self.v_width = tk.StringVar(value=str(self.conf.get("width", "auto")))
        self.v_sec = tk.IntVar(value=int(self.conf.get("seconds", 60)))
        # format mémorisé séparément pour la radio et pour l'hybride (« original » en hybride
        # ne doit pas rester en radio : une grosse photo y demanderait des heures)
        self._fmt_mem = {"radio": self.conf.get("fmt", "avif"),
                         "hyb": self.conf.get("hyb_fmt", self.conf.get("fmt", "avif"))}
        self._fmt_side = "hyb" if self.conf.get("hyb_on") else "radio"
        self.v_fmt = tk.StringVar(value=self._fmt_mem[self._fmt_side])
        ov = str(self.conf.get("overhead", "auto"))
        if ov.isdigit():
            near = min(ROBUST[1:], key=lambda r: abs(r[1] - int(ov)))
        else:
            near = ROBUST[0]
        self.v_over = tk.StringVar(value=tr(near[0]))
        r1 = ttk.Frame(tb)
        r1.pack(fill="x")
        ttk.Button(r1, text="Ouvrir une image…", command=self.open_image).pack(side="left", padx=(0, 4))
        ttk.Button(r1, text="Envoyer un fichier…", command=self.send_file).pack(side="left", padx=(0, 10))
        widgets = [
            ("Mode", ttk.Combobox(r1, textvariable=self.v_mode, values=TX_MODES, width=8, state="readonly")),
            ("Durée max (s)", ttk.Spinbox(r1, textvariable=self.v_sec, from_=15, to=3600, increment=30, width=6)),
            ("Largeur", ttk.Combobox(r1, textvariable=self.v_width, values=WIDTHS, width=8)),
            ("Format", ttk.Combobox(r1, textvariable=self.v_fmt, values=FORMATS_TX, width=8, state="readonly")),
            ("Robustesse", ttk.Combobox(r1, textvariable=self.v_over, values=[tr(r[0]) for r in ROBUST], width=17,
                                        state="readonly")),
        ]
        for lab, w in widgets:
            ttk.Label(r1, text=lab).pack(side="left", padx=(6, 2))
            w.pack(side="left")
        ttk.Button(r1, text="Recalculer", command=self.prepare).pack(side="left", padx=(10, 0))
        # en hybride, la liste Mode reste active : « EasyPal » = hybride façon EasyPal
        self._radio_widgets = [w for lab, w in widgets if lab not in ("Format", "Mode")]
        for lab, w in widgets:
            w._ro = lab in ("Mode", "Robustesse")
        widgets[0][1].bind("<<ComboboxSelected>>", self._mode_changed)
        for _, w in widgets[1:]:
            w.bind("<<ComboboxSelected>>", lambda e: self.prepare())
            w.bind("<Return>", lambda e: self.prepare())
            w.bind("<FocusOut>", lambda e: self.prepare())
        r2 = ttk.Frame(tb)
        r2.pack(fill="x", pady=(4, 0))
        self.v_prev = tk.BooleanVar(value=bool(self.conf.get("preview", True)))
        self.v_hyb = tk.BooleanVar(value=bool(self.conf.get("hyb_on")))
        self.v_cwid = tk.BooleanVar(value=bool(self.conf.get("cwid")))
        self.v_txtinc = tk.BooleanVar(value=False)
        ttk.Checkbutton(r2, text="Aperçu rapide d'abord (> 2 min)", variable=self.v_prev,
                        command=self.prepare).pack(side="left")
        ttk.Checkbutton(r2, text="Mode hybride", variable=self.v_hyb,
                        command=self._toggle_hyb_ui).pack(side="left", padx=(12, 0))
        self.v_flash = tk.BooleanVar(value=bool(self.conf.get("hyb_flash")))

        def _flash_toggle():
            self.conf["hyb_flash"] = bool(self.v_flash.get())
            self._save_conf_file()
            if self.v_flash.get() and not self.v_hyb.get():
                self.v_hyb.set(True)
                self._toggle_hyb_ui()
            else:
                self.prepare()
        ttk.Checkbutton(r2, text="Éclair (9 s)", variable=self.v_flash,
                        command=_flash_toggle).pack(side="left", padx=(6, 12))
        ttk.Checkbutton(r2, text="Texte inclus", variable=self.v_txtinc,
                        command=lambda: (self._btn_on("txtinc", self.v_txtinc.get()), self.prepare())).pack(side="left")
        ttk.Checkbutton(r2, text="ID morse en fin d'émission", variable=self.v_cwid).pack(side="left", padx=12)
        self.v_tcon = tk.BooleanVar(value=bool(self.conf.get("tc_on")))

        def _tc_toggle():
            self.conf["tc_on"] = bool(self.v_tcon.get())
            self._save_conf_file()
            self.prepare()
        ttk.Checkbutton(r2, text="Mes conditions de trafic", variable=self.v_tcon,
                        command=_tc_toggle).pack(side="left")
        ttk.Button(r2, text="…", width=3, command=self.trafic_dialog).pack(side="left", padx=(2, 0))
        self.v_pipon = tk.BooleanVar(value=bool(self.conf.get("pip_on")))

        def _pip_toggle():
            self.conf["pip_on"] = bool(self.v_pipon.get())
            self._save_conf_file()
            if self.conf["pip_on"] and not self.pips:
                self.pip_dialog()
            else:
                self.prepare()
        ttk.Checkbutton(r2, text="Image du correspondant", variable=self.v_pipon,
                        command=_pip_toggle).pack(side="left", padx=(12, 0))
        ttk.Button(r2, text="…", width=3, command=self.pip_dialog).pack(side="left", padx=(2, 0))
        ttk.Button(r2, text="💬 Bulles…", command=self.bubble_dialog).pack(side="left", padx=(12, 0))

        # réglages du mode EasyPal (HamDRM) : visibles seulement dans ce mode
        self.drm_row = ttk.Frame(tb)
        self.v_drm = {}
        drm_widgets = [("drm_mode", "Mode EasyPal", DRM_MODES, 4), ("drm_qam", "QAM", DRM_QAMS, 7),
                       ("drm_bw", "Largeur", DRM_BWS, 8), ("drm_prot", "Erreur", DRM_PROTS, 12),
                       ("drm_rs", "Reed-Solomon", DRM_RSS, 7)]
        old_bw = {"2,3 kHz": "2,2 kHz", "2,5 kHz": "2,4 kHz"}      # réglages d'avant la 0.59
        if self.conf.get("drm_bw") in old_bw:
            self.conf["drm_bw"] = old_bw[self.conf["drm_bw"]]
        for key, lab, vals, w in drm_widgets:
            v = tk.StringVar(value=self.conf.get(key) if self.conf.get(key) in vals else DEFAULTS[key])
            self.v_drm[key] = v
            ttk.Label(self.drm_row, text=lab).pack(side="left", padx=(0 if key == "drm_mode" else 8, 2))
            cb = ttk.Combobox(self.drm_row, textvariable=v, values=vals, width=w, state="readonly")
            cb.pack(side="left")
            cb.bind("<<ComboboxSelected>>", lambda e: self._drm_changed())
        ttk.Label(self.drm_row, text="(compatible EasyPal / QSSTV, JPEG 2000)", foreground="#555").pack(side="left", padx=(10, 0))
        self._robust_widget = widgets[4][1]
        self.after_idle(self._drm_ui_update)

        bar = self._green_bar(t)
        self.v_txinfo = TrVar(value="")
        tk.Label(bar, textvariable=self.v_txinfo, bg=GREEN, justify="left", anchor="w",
                 font=("TkDefaultFont", 9)).pack(side="left", padx=6, pady=2)
        bb = tk.Frame(bar, bg=GREEN)
        bb.pack(side="right", padx=6, pady=3)
        self.pb_tx = ttk.Progressbar(bb, mode="determinate", length=260)
        self.pb_tx.pack(side="top", fill="x", pady=(0, 3))
        bt = tk.Frame(bb, bg=GREEN)
        bt.pack(side="top", fill="x")
        ttk.Button(bt, text="▶ Émettre", style="Accent.TButton",
                   command=lambda: self._tx_when_free(self.transmit, tr("image"))).pack(side="left")
        self.btn_comp = ttk.Button(bt, text="+ Compléter", command=lambda: self.transmit(complement=True))
        self.btn_comp.pack(side="left", padx=4)
        ttk.Button(bt, text="■ Arrêter", command=lambda: self.stop_tx.set()).pack(side="left")
        ttk.Button(bt, text="WAV…", command=self.save_wav).pack(side="left", padx=(4, 0))
        # « DATA auto » : LSB -> LSB-DATA pour l'image, retour en LSB à la fin (commenter au micro)
        self.bt_dauto = tk.Button(bt, text="DATA auto", command=self._data_auto_toggle, cursor="hand2",
                                  padx=4, pady=0)
        self.bt_dauto.pack(side="left", padx=(4, 0))
        self._data_auto_paint()
        tip(self.bt_dauto, "Allumé : le poste passe en LSB-DATA (ou USB-DATA) au moment d'émettre, puis "
                           "revient tout seul en LSB (ou USB) à la fin de l'image.")
        # mode hybride : déposer l'image d'avance (l'annonce part tout de suite à l'émission)
        self.btn_pre = ttk.Button(bt, text="⇪ Déposer", command=self.hyb_preupload)
        tip(self.btn_pre, "Mode hybride : met l'image sur le serveur tout de suite ; à votre tour, "
                          "« Émettre » envoie directement l'annonce.")
        self._show_pre_btn()
        info = tk.Frame(t, bg=GREEN)
        info.pack(fill="x", side="bottom")
        self.lb_src_info = tk.Label(info, text="", bg=GREEN, anchor="w", font=("TkDefaultFont", 8))
        self.lb_src_info.pack(side="left", padx=6)
        self.lb_cmp_info = tk.Label(info, text="", bg=GREEN, anchor="w", font=("TkDefaultFont", 9, "bold"))
        self.lb_cmp_info.pack(side="left", padx=12)
        # tourner l'image à émettre (photos de téléphone mal orientées)
        for txt, deg, hint in (("⟳", -90, "Tourner à droite"), ("⟲", 90, "Tourner à gauche")):
            b = tk.Button(info, text=txt, font=("TkDefaultFont", 10, "bold"), bg="white", cursor="hand2",
                          padx=4, pady=0, command=lambda d=deg: self._rotate_tx(d))
            b.pack(side="right", padx=(0, 4), pady=1)
            tip(b, hint)
        self.lb_cmp = ImageView(t, placeholder="Cliquez ici pour ouvrir une image, ou glissez-la ici")
        self.lb_cmp.pack(fill="both", expand=True)
        # un clic (sans glisser) sur l'image TX ouvre le choix de l'image
        self.lb_cmp.bind("<ButtonPress-1>", lambda e: setattr(self, "_cmp_press", (e.x, e.y)), add="+")
        self.lb_cmp.bind("<ButtonRelease-1>", self._cmp_click, add="+")
        import txedit
        self.tx_editor = txedit.TxEditor(self, self.lb_cmp)     # 1.52 : textes et logos à la souris
        self.lb_src = ImageView(t)          # original : pas affiché, gardé pour la carte QSL

    def _build_text_window(self):
        w = self.win_txt = tk.Toplevel(self)
        w.title(f"{APP} — Envoi texte")
        w.withdraw()
        w.transient(self)
        w.protocol("WM_DELETE_WINDOW", w.withdraw)
        f = ttk.Frame(w, padding=10)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text="Texte à envoyer :").pack(anchor="w")
        self.txt_msg = tk.Text(f, height=8, width=72, wrap="word")
        self.txt_msg.pack(fill="both", expand=True, pady=(2, 6))
        b = ttk.Frame(f)
        b.pack(fill="x")
        ttk.Checkbutton(b, text="Inclure ce texte avec l'image", variable=self.v_txtinc,
                        command=lambda: (self._btn_on("txtinc", self.v_txtinc.get()), self.prepare())).pack(side="left")
        ttk.Button(b, text="Fermer", command=lambda: (w.withdraw(), self.prepare())).pack(side="right")
        ttk.Button(b, text="Envoyer le texte seul", command=lambda: self._tx_when_free(self.send_text, tr("texte"))).pack(side="right", padx=6)
        sf = ttk.LabelFrame(f, text="Messages envoyés — reçus par", padding=4)
        sf.pack(fill="both", expand=True, pady=(8, 0))
        self.tv_sent = ttk.Treeview(sf, columns=("h", "txt", "st"), show="headings", height=5)
        for c, title, wd in (("h", "Heure", 50), ("txt", "Message", 260), ("st", "Reçu par", 320)):
            self.tv_sent.heading(c, text=tr(title))
            self.tv_sent.column(c, width=wd, anchor="w", stretch=c != "h")
        self.tv_sent.pack(fill="both", expand=True)

    # ------------------------------------------------------------ fenêtre « Lire fichier Wave »
    def _build_wav_window(self):
        w = self.win_wav = tk.Toplevel(self)
        w.title(f"{APP} — WAVE")
        w.withdraw()
        w.transient(self)
        w.protocol("WM_DELETE_WINDOW", w.withdraw)
        f = ttk.LabelFrame(w, text="Lire fichier Wave", padding=8)
        f.pack(fill="both", expand=True, padx=8, pady=8)
        self.lst_wav = tk.Listbox(f, height=14, width=46, bg="#c8c8c8")
        self.lst_wav.pack(fill="both", expand=True)
        self.lst_wav.bind("<Double-Button-1>", lambda e: self.wav_play())
        g = ttk.Frame(f)
        g.pack(fill="x", pady=(8, 0))
        rows = [
            [("Mettre comme « begin.wav »", lambda: self.wav_set("begin.wav")),
             ("Retirer « begin.wav »", lambda: self.wav_unset("begin.wav"))],
            [("Mettre comme « end.wav »", lambda: self.wav_set("end.wav")),
             ("Retirer « end.wav »", lambda: self.wav_unset("end.wav"))],
            [("ÉMISSION", self.wav_play), ("SORTIE", w.withdraw), ("Effacer", self.wav_delete),
             ("Renommer", self.wav_rename)],
            [("Importer…", self.wav_import), ("Texte waterfall…", self.show_wft),
             ("Dossier", lambda: self._open_path(wavtext.wav_dir(DEFAULT_OUT)))],
        ]
        for r, row in enumerate(rows):
            span = 4 // len(row)
            for c, (txt, cmd) in enumerate(row):
                ttk.Button(g, text=txt, command=cmd).grid(row=r, column=c * span, columnspan=span,
                                                          sticky="ew", padx=2, pady=2)
        for c in range(4):
            g.columnconfigure(c, weight=1, uniform="w")
        self.btn_rec = ttk.Button(g, text="● Enregistrer RX", command=self.toggle_record)
        self.btn_rec.grid(row=4, column=0, columnspan=4, sticky="ew", padx=2, pady=(6, 2))
        ttk.Label(f, text="begin.wav part avant chaque émission, end.wav après (comme EasyPal).",
                  foreground="#555").pack(anchor="w", pady=(6, 0))

    def show_wav(self):
        self._wav_refresh()
        self.win_wav.deiconify()
        self.win_wav.lift()

    def _wav_files(self):
        d = wavtext.wav_dir(DEFAULT_OUT)
        return d, sorted((f for f in os.listdir(d) if f.lower().endswith(".wav")), key=str.lower)

    def _wav_refresh(self):
        d, files = self._wav_files()
        self.lst_wav.delete(0, "end")
        for name in files:
            mark = {"begin.wav": tr("   ← avant chaque émission"),
                    "end.wav": tr("   ← après chaque émission")}.get(name.lower(), "")
            self.lst_wav.insert("end", name + mark)
        self._wav_names = files

    def _wav_selected(self):
        sel = self.lst_wav.curselection()
        if not sel:
            messagebox.showinfo(APP, "Choisissez d'abord un fichier dans la liste.")
            return None
        return os.path.join(wavtext.wav_dir(DEFAULT_OUT), self._wav_names[sel[0]])

    def wav_set(self, target):
        p = self._wav_selected()
        if not p:
            return
        dst = os.path.join(os.path.dirname(p), target)
        if os.path.abspath(p) != os.path.abspath(dst):
            shutil.copyfile(p, dst)
        self.log(f"{os.path.basename(p)} → {target}")
        self._wav_refresh()

    def wav_unset(self, target):
        p = os.path.join(wavtext.wav_dir(DEFAULT_OUT), target)
        if os.path.exists(p):
            os.remove(p)
            self.log(f"{target} retiré.")
        self._wav_refresh()

    def wav_delete(self):
        p = self._wav_selected()
        if p and messagebox.askyesno(APP, f"Effacer {os.path.basename(p)} ?"):
            os.remove(p)
            self._wav_refresh()

    def wav_rename(self):
        from tkinter import simpledialog
        p = self._wav_selected()
        if not p:
            return
        new = simpledialog.askstring(APP, tr("Nouveau nom :"), initialvalue=os.path.basename(p),
                                     parent=self.win_wav)
        if not new:
            return
        if not new.lower().endswith(".wav"):
            new += ".wav"
        os.replace(p, os.path.join(os.path.dirname(p), os.path.basename(new)))
        self._wav_refresh()

    def wav_import(self):
        ps = filedialog.askopenfilenames(parent=self.win_wav, filetypes=[("WAV", "*.wav")])
        for p in ps:
            shutil.copy(p, wavtext.wav_dir(DEFAULT_OUT))
        self._wav_refresh()

    def wav_play(self):
        p = self._wav_selected()
        if not p:
            return
        try:
            engine.read_wav_8k(p)
        except Exception as e:
            messagebox.showerror(APP, f"Fichier illisible :\n{e}")
            return
        self._start_job({"kind": "wav", "path": p})

    # ------------------------------------------------------------ fenêtre « Texte Waterfall »
    def _build_wft_window(self):
        w = self.win_wft = tk.Toplevel(self)
        w.title(f"{APP} — Texte / image waterfall")
        w.withdraw()
        w.transient(self)
        w.protocol("WM_DELETE_WINDOW", w.withdraw)
        f = ttk.LabelFrame(w, text="Texte ou image dans le waterfall", padding=8)
        f.pack(fill="both", expand=True, padx=8, pady=8)
        self.txt_wft = tk.Text(f, height=4, width=34, wrap="none", bg="black", fg="#ffe066",
                               insertbackground="white", font=("TkDefaultFont", 12, "bold"))
        self.txt_wft.pack(fill="x")
        self.txt_wft.insert("1.0", self.conf.get("wft_text") or self.conf.get("callsign", ""))
        self.cv_wft = tk.Canvas(f, width=264, height=110, bg="black", highlightthickness=0)
        self.cv_wft.pack(pady=(6, 0))
        o = ttk.Frame(f)
        o.pack(fill="x", pady=(6, 0))
        self.v_wavvol = tk.IntVar(value=int(self.conf.get("wav_volume", 5)))
        self.lb_wavvol = ttk.Label(o, text="")
        ttk.Scale(o, from_=1, to=10, variable=self.v_wavvol, length=150,
                  command=lambda v: self._wft_vol()).pack(side="left")
        self.lb_wavvol.pack(side="left", padx=6)
        o2 = ttk.Frame(f)
        o2.pack(fill="x", pady=(4, 0))
        ttk.Label(o2, text="Fonte").pack(side="left")
        self.v_wftfont = tk.StringVar(value=self.conf.get("wft_font", "Arial"))
        cb = ttk.Combobox(o2, textvariable=self.v_wftfont, values=list(wavtext.FONTS), width=16,
                          state="readonly")
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._wft_preview())
        self.v_wftneg = tk.BooleanVar(value=bool(self.conf.get("wft_neg")))
        ttk.Checkbutton(o2, text="Négatif", variable=self.v_wftneg,
                        command=self._wft_preview).pack(side="left", padx=6)
        oi = ttk.Frame(f)
        oi.pack(fill="x", pady=(4, 0))
        ttk.Button(oi, text="Image…", command=self.wft_image).pack(side="left")
        ttk.Button(oi, text="Texte", command=self.wft_text_mode).pack(side="left", padx=4)
        self.lb_wftsrc = ttk.Label(oi, text="", foreground="#555")
        self.lb_wftsrc.pack(side="left", padx=4)
        self._wft_img = None
        b = ttk.Frame(f)
        b.pack(fill="x", pady=(8, 0))
        for i, (txt, cmd) in enumerate((("Émission", self.wft_send), ("Sauve", self.wft_save),
                                        ("Effacer texte", lambda: (self.txt_wft.delete("1.0", "end"),
                                                                   self.wft_text_mode())),
                                        ("SORTIE", w.withdraw))):
            ttk.Button(b, text=txt, command=cmd).grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
        b.columnconfigure(0, weight=1)
        b.columnconfigure(1, weight=1)
        self.lb_wftinfo = ttk.Label(f, text="", foreground="#555")
        self.lb_wftinfo.pack(anchor="w", pady=(4, 0))
        self.txt_wft.bind("<KeyRelease>", lambda e: self._wft_preview())
        self._wft_vol()

    def _wft_vol(self):
        self.lb_wavvol.configure(text=tr(f"Wav Volume {int(self.v_wavvol.get())}"))

    def wft_image(self):
        """Comme EasyPal : une image (photo, logo, QSL) dessinée dans le waterfall."""
        p = filedialog.askopenfilename(parent=self.win_wft, filetypes=[
            ("Images", "*.jpg *.jpeg *.png *.gif *.bmp *.webp *.avif *.svg"), ("Tous", "*.*")])
        if not p:
            return
        try:
            self._wft_img = imgfmt.load_source(p)[0]
        except Exception as e:
            messagebox.showerror(APP, f"Image illisible : {e}", parent=self.win_wft)
            return
        self.lb_wftsrc.configure(text=os.path.basename(p))
        self._wft_preview()

    def wft_text_mode(self):
        self._wft_img = None
        self.lb_wftsrc.configure(text="")
        self._wft_preview()

    def _wft_bitmap(self):
        if getattr(self, "_wft_img", None) is not None:
            return wavtext.render_image(self._wft_img, negative=bool(self.v_wftneg.get()))
        txt = self.txt_wft.get("1.0", "end").strip()
        if not txt:
            return None
        return wavtext.render(txt, self.v_wftfont.get(), bool(self.v_wftneg.get()))

    def _wft_preview(self):
        self.cv_wft.delete("all")
        bm = self._wft_bitmap()
        if bm is None:
            self.lb_wftinfo.configure(text="")
            return
        im = wavtext.preview(bm, 1)
        im = im.resize((264, max(8, min(110, int(264 * bm.shape[0] / bm.shape[1])))), Image.NEAREST)
        self._photos["wft"] = ImageTk.PhotoImage(im)
        self.cv_wft.create_image(132, 55, image=self._photos["wft"])
        self.lb_wftinfo.configure(text=tr(f"Durée : {bm.shape[0] * wavtext.ROW_S + 0.6:.1f} s, "
                                          f"{wavtext.F_LO:.0f}–{wavtext.F_HI:.0f} Hz"))

    def show_wft(self):
        self.win_wft.deiconify()
        self.win_wft.lift()
        self._wft_preview()

    def wft_send(self):
        bm = self._wft_bitmap()
        if bm is None:
            messagebox.showinfo(APP, "Écrivez d'abord le texte à envoyer.")
            return
        self._start_job({"kind": "wftext", "bitmap": bm})

    def wft_save(self):
        from tkinter import simpledialog
        bm = self._wft_bitmap()
        if bm is None:
            messagebox.showinfo(APP, "Écrivez d'abord le texte à envoyer.")
            return
        name = simpledialog.askstring(APP, tr("Nom du fichier :"),
                                      initialvalue="image_waterfall.wav" if self._wft_img is not None
                                      else "texte_waterfall.wav",
                                      parent=self.win_wft)
        if not name:
            return
        if not name.lower().endswith(".wav"):
            name += ".wav"
        p = os.path.join(wavtext.wav_dir(DEFAULT_OUT), os.path.basename(name))
        engine.write_wav(p, wavtext.synth(bm, int(self.v_wavvol.get())), 8000)
        self.log(f"Texte waterfall enregistré : {p}")
        self._wav_refresh()
        if messagebox.askyesno(APP, "L'utiliser comme « begin.wav » (avant chaque émission) ?"):
            shutil.copyfile(p, os.path.join(os.path.dirname(p), "begin.wav"))
            self._wav_refresh()

    def show_text(self):
        self.win_txt.deiconify()
        self.win_txt.lift()
        self.txt_msg.focus_set()

    def show_settings(self):
        w = self.win_conf
        if not getattr(self, "_conf_sized", False):
            # taille d'ouverture : tout le contenu si l'écran le permet, sinon la hauteur de
            # l'écran (moins la barre des tâches) avec défilement
            w.update_idletasks()
            t = self._conf_inner
            need_w = t.winfo_reqwidth() + 24
            need_h = t.winfo_reqheight() + 60
            sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
            ww, wh = min(need_w, sw - 40), min(need_h, sh - 110)
            x = max(0, min(self.winfo_rootx() + 40, sw - ww - 10))
            w.geometry(f"{ww}x{wh}+{x}+20")
            self._conf_sized = True
        w.deiconify()
        w.lift()

    def _tab_stations(self, nb):
        w = self.tab_stations = tk.Frame(nb)      # cadre tk : peut devenir une fenêtre séparée
        t = ttk.Frame(w, padding=10)
        t.pack(fill="both", expand=True)
        nb.add(w, text="  Stations  ")
        opt = ttk.LabelFrame(t, text="BSR / FIX (demandes de compléments)", padding=6)
        opt.pack(fill="x")
        self.v_bsr_auto = tk.BooleanVar(value=self.conf.get("bsr_auto", True))
        self.v_fix_auto = tk.BooleanVar(value=self.conf.get("fix_auto", True))
        self.v_ack_auto = tk.BooleanVar(value=self.conf.get("ack_auto", True))
        self.v_listen_after = tk.BooleanVar(value=self.conf.get("listen_after", True))
        self.v_follow = tk.BooleanVar(value=self.conf.get("follow_mode", True))
        for i, (txt, v) in enumerate((
                ("En réception : envoyer un BSR automatiquement si l'image est incomplète", self.v_bsr_auto),
                ("En réception : envoyer un accusé (ACK) quand l'image est complète", self.v_ack_auto),
                ("En émission : répondre automatiquement aux BSR par un FIX", self.v_fix_auto),
                ("Écouter après chaque émission (pour recevoir BSR et ACK)", self.v_listen_after),
                ("Passer en émission sur le mode reçu (EasyPal ou HFImage)", self.v_follow))):
            ttk.Checkbutton(opt, text=txt, variable=v).grid(row=i, column=0, sticky="w")
        ttk.Label(opt, text="BSR et ACK partent en DATAC0 (~2 s) quand l'émetteur a fini ; "
                            "un FIX n'envoie que des symboles nouveaux, utiles à toutes les stations.",
                  foreground="#555").grid(row=5, column=0, sticky="w", pady=(4, 0))
        cols = ("heure", "call", "evt", "mode", "snr", "detail")
        self.tree = ttk.Treeview(t, columns=cols, show="headings", height=14)
        for c, title, w in zip(cols, (clocktz.label(tr("Heure")), "Indicatif", "Événement", "Mode", "SNR", "Détail"),
                               (80, 90, 170, 90, 60, 360)):
            self.tree.heading(c, text=title)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, pady=8)
        bf = ttk.Frame(t)
        bf.pack(fill="x")
        self.btn_fix = ttk.Button(bf, text="FIX", command=self.send_fix)
        self.btn_fix.pack(side="left")
        ttk.Button(bf, text="Effacer la liste", command=lambda: self.tree.delete(*self.tree.get_children())).pack(
            side="left", padx=6)
        ttk.Label(bf, text="Journal complet : Documents\\HFImage\\stations.csv", foreground="#555").pack(side="right")

    # ------------------------------------------------- stations entendues / Rx Ok (EasyPal)
    def _stations_box(self, parent):
        box = self._st_box = tk.Frame(parent, bg=GREEN, bd=2, relief="groove")
        box.pack(fill="both", expand=True)
        head = tk.Frame(box, bg=GREEN)
        head.pack(fill="x")
        self.lb_heard = tk.Label(head, text="", bg=GREEN, fg=FG_DARK, anchor="w",
                                 font=("TkDefaultFont", 9, "bold"))
        self.lb_heard.pack(side="left", padx=(4, 0))
        self.lb_rxok = tk.Label(head, text="", bg=GREEN, fg=FG_DARK, anchor="e",
                                font=("TkDefaultFont", 9, "bold"))
        self.lb_rxok.pack(side="right", padx=(0, 4))
        tk.Label(box, text="* = en émission    HYB = mode hybride", bg=GREEN, fg=FG_DARK, anchor="w",
                 font=("TkDefaultFont", 8)).pack(side="bottom", fill="x", padx=4)   # légende toujours visible
        # séparateur réglable entre la liste des stations et Rx Ok (position gardée)
        split = tk.PanedWindow(box, orient="horizontal", bg=GREEN, sashwidth=6, sashrelief="raised", bd=0,
                               opaqueresize=True)
        split.pack(fill="both", expand=True, padx=2, pady=(0, 2))
        self.panes["stlists"] = split
        body = tk.Frame(split, bg=GREEN)
        rbody = tk.Frame(split, bg=GREEN)
        split.add(body, minsize=70, stretch="always")
        split.add(rbody, minsize=50, stretch="never")
        mono = ("Consolas", 9) if sys.platform.startswith("win") else ("TkFixedFont", 9)
        self.lst_heard = tk.Listbox(body, height=7, width=18, font=mono, activestyle="none",
                                    bg="white", fg="#062e06", selectbackground="#2f9e2f")
        sb = ttk.Scrollbar(body, orient="vertical", command=self.lst_heard.yview)
        sb.pack(side="right", fill="y")                 # placée d'abord : jamais écrasée par la liste
        self.lst_heard.pack(side="left", fill="both", expand=True)
        self.lst_heard.configure(yscrollcommand=sb.set)
        self.lst_rxok = tk.Listbox(rbody, height=7, width=14, font=mono, activestyle="none",
                                   bg="white", fg="#062e06", selectbackground="#2f9e2f")
        self.lst_rxok.pack(side="left", fill="both", expand=True)
        for lb in (self.lst_heard, self.lst_rxok):
            lb.bind("<ButtonRelease-1>", lambda e: e.widget.xview_moveto(0), add="+")
            # jamais de défilement horizontal (molette, pavé tactile, glisser…) : sinon le début
            # des indicatifs est coupé (« 4VD274 » pour « 14VD274 »)
            lb.configure(xscrollcommand=App._no_xscroll(lb))
            lb.bind("<B1-Leave>", lambda e: "break")       # pas de défilement horizontal en glissant
        self.lst_heard.bind("<Double-Button-1>", lambda e: self._heard_detail())
        self.lst_rxok.bind("<Double-Button-1>", lambda e: self._heard_detail(self.lst_rxok))
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Carte des stations…", command=self.show_map)
        menu.add_command(label="Sites des stations…", command=self.show_sites)
        menu.add_command(label="Signaler ma présence (QRV)", command=self.send_qrv)
        menu.add_command(label="Aller sur la fréquence de cette station", command=self._qsy_station)
        menu.add_command(label="Vider la liste des stations", command=self._heard_clear)
        for w in (self.lst_heard, self.lst_rxok, self.lb_heard):
            w.bind("<Button-3>", lambda e, m=menu: m.tk_popup(e.x_root, e.y_root))
        self._heard_names, self._rxok_names = [], []
        self._heard_refresh()

    # ------------------------------------------------- présence par Internet (comme EasyPal)
    def net_start(self):
        self.net_stop()
        call = self.mycall()
        if not self.v_net.get() or not call:
            self._net_status()
            return
        try:
            host, port = self.v_nethost.get().strip() or presence.DEFAULT_HOST, int(self.v_netport.get())
        except (tk.TclError, ValueError):
            host, port = presence.DEFAULT_HOST, presence.DEFAULT_PORT
        self.net = presence.Presence(
            host, port,
            on_station=lambda k, d: self.ui(self._net_station, k, d),
            on_rxok=lambda d: self.ui(self._net_rxok, d),
            on_state=lambda ok, why: self.ui(self._net_state, ok, why),
            log=lambda m: self.ui(self.log, m))
        self._net_st = None
        self.net.tag = PROFILE                   # plusieurs instances : une présence chacune
        try:
            self.net.start(call, {"loc": self.v_loc.get().strip(), "freq": self.rig_freq,
                                  "mode": self.rig_mode, "state": "RX", "ver": VERSION, "app": "HFImage",
                                  "hyb": bool(self.v_hyb.get()), "name": self.myname(),
                                  "site": self._my_site()})
        except Exception as e:
            self.log_exc("Présence Internet", e)
            self.net = None
        self._net_status()

    def net_stop(self):
        if self.net is not None:
            self.net.stop()
            self.net = None
        self.net_ok = False
        self.online.clear()

    def _net_state(self, ok, why):
        if ok and not self.net_ok:
            self.log(f"Internet : connecté au serveur de présence ({self.net.host if self.net else '?'}).")
        elif not ok and self.net_ok:
            self.log("Internet : serveur de présence injoignable, nouvel essai automatique…")
        self.net_ok = ok
        if not ok:
            self.online.clear()
        self._net_status()
        self._heard_refresh()

    def _net_status(self):
        if not hasattr(self, "lb_netstat"):
            return
        if self.net is None:
            txt = "Désactivé" if not self.v_net.get() else "Indicatif manquant"
        elif self.net_ok:
            txt = tr(f"Connecté — {len(self.online)} station(s) en ligne")
        else:
            txt = "Connexion en cours…"
        self._set_text(self.lb_netstat, txt)

    def _station_call(self, text):
        """Indicatif d'une station tel qu'il arrive (« F4LTX CHRIS », « F4LTX CH » par radio) ->
        indicatif seul (une seule ligne par station) ; le prénom éventuel est retenu."""
        call, name = split_call(text)
        # (8 caractères tout juste : peut-être coupé par la radio, « F1JI PAU » pour « F1JI PAUL »)
        if name and call and call != "?" and len(name) >= 3 and call not in self.opnames \
                and len(str(text).strip()) != 8:
            self.opnames[call] = name               # « CH » (coupé par la radio) : pas un prénom
        return call

    def _label(self, call):
        """Indicatif + prénom pour l'affichage des listes."""
        n = self.opnames.get(call)
        try:
            if call == self.mycall():
                n = self.myname() or n               # notre propre ligne (Rx Ok) : notre prénom
        except AttributeError:
            pass
        return f"{call} {n}" if n else call

    def _name_tail(self, call, tag=None):
        """Prénom en bout de ligne (après le report / la fréquence) : un prénom long ne cache
        plus rien ; coupé à 10 caractères."""
        n = self._label(call)[len(call) + 1:]
        if not n:
            return ""
        if len(n) > 10:
            n = n[:9] + "."
        return (" " * 6 if tag == "" else "  ") + n

    def _net_station(self, key, d):
        if d is None:
            if self.online.pop(key, None) is not None:
                self._heard_refresh()
            return
        d = dict(d)
        d["call"] = self._station_call(d.get("call"))
        name = str(d.get("name") or "").strip()
        if name:
            self.opnames[d["call"]] = name.title()[:16]
        # même station sous une autre clé (ancienne présence « F4LTX-CHRIS », 2e profil) :
        # une seule ligne dans la liste, et pas de nouveau « En ligne » dans le journal
        new = not any(x.get("call") == d["call"] for x in self.online.values())
        self.online[key] = dict(d, seen=time.time())
        if d.get("loc"):
            self._remember_loc(str(d["call"]).upper(), d["loc"])
        if new:
            fr = f" — {audio.format_freq(d['freq'], True)}" if d.get("freq") else ""
            self.log(f"En ligne : {d['call']}" + (f" ({d['loc']})" if d.get("loc") else "") + fr)
        self._net_status()
        self._heard_refresh()

    def _net_rxok(self, d):
        call = self._station_call(d.get("from", ""))
        iid = d.get("id")
        if d.get("loc"):
            self._remember_loc(call, d["loc"])
        rep = d.get("report")
        rep = int(rep) if isinstance(rep, (int, float)) else None
        mine = iid in self.my_ids or iid in self.sent_images
        first = call not in self.rxok_by_id.get(iid, {})
        # gardé pour toutes les images : si on reçoit (ou a reçu) la même, on verra ces reports
        self._rxok_add(call, rep, iid)
        if iid in self.sent_msgs:
            self._msg_ack(iid, call, rep, "Internet")
        elif mine:
            if first:
                self.log(f"{call} confirme la réception de l'image par Internet"
                         + ("." if rep is None else f" (report {rep:+d} dB)."))
                self.station_event(call, "Rx Ok (Internet)", "", None,
                                   "" if rep is None else f"report {rep:+d} dB")

    def _net_confirm(self, iid, call, show=True):
        """Image (ou message) bien reçu : l'image s'affiche dans Rx Ok avec notre report, et on prévient
        l'émetteur (et les autres stations) par Internet."""
        snr = self.snr_by_id.get(iid)
        if show and iid not in self.my_ids:
            self._rxok_show(iid)
            self._rxok_add(self.mycall(), None if snr is None else int(round(snr)), iid)
        if self.net is None or iid in self.rxok_sent:
            return
        if self.net.send_rxok(call, iid, None if snr is None else int(round(snr)), self.v_loc.get().strip()):
            if call and call != "?":
                self.rxok_sent.add(iid)     # indicatif inconnu : on renverra quand il arrivera

    def _load_locs(self):
        try:
            with open(os.path.join(DEFAULT_OUT, "locators.json"), encoding="utf-8") as f:
                return dict(json.load(f))
        except Exception:
            return {}

    def _remember_loc(self, call, loc):
        loc = (loc or "").strip()
        if not call or len(loc) < 4 or protocol.locator_to_latlon(loc) is None:
            return
        old = self.known_loc.get(call, "")
        # un locator à 6 caractères n'est pas remplacé par le même carré à 4 caractères
        if len(loc) == 4 and old[:4].upper() == loc.upper():
            return
        if old != loc:
            self.known_loc[call] = loc
            try:
                os.makedirs(DEFAULT_OUT, exist_ok=True)
                with open(os.path.join(DEFAULT_OUT, "locators.json"), "w", encoding="utf-8") as f:
                    json.dump(self.known_loc, f, indent=0, sort_keys=True)
            except Exception:
                pass

    def _map_data(self):
        """Pour la carte : (notre station, [stations entendues / Rx Ok avec position])."""
        mycall = self.mycall() or "NOCALL"
        myloc = self.v_loc.get().strip()
        me = {"call": mycall, "loc": myloc, "pos": protocol.locator_to_latlon(myloc), "info": tr("votre station")}
        out = []
        on = {str(d["call"]).upper(): d for d in self.online.values()}
        # stations qui ont reçu NOTRE dernière image (même si Rx Ok affiche depuis une image reçue)
        if self.last_tx_id is not None:
            mine = self.rxok_by_id.get(self.last_tx_id, {})
        else:
            mine = self.rxok if self.rxok_ctx in self.my_ids else {}
        for c in sorted(set(self.heard) | set(mine) | set(on)):
            h = self.heard.get(c, {})
            loc = (on.get(c) or {}).get("loc") or h.get("loc") or self.known_loc.get(c, "")
            info = []
            if c in on:
                d = on[c]
                info.append(tr("en ligne") + (f", {audio.format_freq(d['freq'], True)}" if d.get("freq") else ""))
            if self._is_hyb(c, on):
                info.append(tr("en mode hybride (image par Internet)"))
            if c in mine:
                rep, t = mine[c]
                info.append(tr("a reçu votre image") + ("" if rep is None else f" (report {rep:+d} dB)")
                            + " " + clocktz.fmt("%H:%M", t))
            elif h.get("t"):
                info.append(tr("entendue à {0}").replace("{0}", clocktz.fmt("%H:%M", h["t"])))
            if h.get("snr") is not None:
                info.append(f"SNR {h['snr']:+.0f} dB")
            if h.get("freq") and c not in on:
                info.append(audio.format_freq(h["freq"], True))
            # trait depuis notre station seulement vers ceux qui ont reçu NOTRE image
            ok = c in mine
            out.append({"call": c, "loc": loc, "pos": protocol.locator_to_latlon(loc), "ok": ok,
                        "info": "   —   ".join(info), "rep": mine[c][0] if ok else None,
                        "name": self.opnames.get(c, "")})
        return me, out

    def show_map(self, call=None):
        if self.map_win is None or not self.map_win.alive():
            self.map_win = stationmap.MapWindow(self, self._map_data, tr=tr, lang=i18n.get_lang,
                                                on_paste=self._map_to_tx,
                                                show_all=bool(self.conf.get("map_all", False)),
                                                on_show_all=self._map_all_changed)
            self.look.apply(self.map_win.win)
            self.map_win.win.update_idletasks()
            me, st = self._map_data()
            self.map_win.set_view("*" if any(x["ok"] for x in st) or (self.conf.get("map_all") and st)
                                  else "Europe")
        else:
            self.map_win.win.deiconify()
            self.map_win.win.lift()
        if call:
            self.map_win.win.update_idletasks()
            self.map_win.focus(call)

    def _map_all_changed(self, v):
        self.conf["map_all"] = bool(v)
        self._save_conf_file()

    def _map_to_tx(self, img):
        """« Coller l'image dans la fenêtre TX » (comme EasyPal) : la carte devient l'image à émettre."""
        self.src_img = img.convert("RGB")
        self.src_raw = self.src_kind = self.src_anim = None
        self.tx = None
        self._show(self.lb_src, "src", self.src_img)
        self._set_text(self.lb_src_info, f"Carte des stations — {img.width}×{img.height}")
        self.show_tab("tx")
        self.prepare()
        self.log("Carte des stations placée dans la fenêtre TX.")

    @staticmethod
    def _mhz(hz):
        return f"{hz / 1e6:.3f}" if hz else "—"

    def _heard(self, call, snr=None, what="", loc=None, hyb=False):
        """Une station utilisant HFImage a été entendue (image, annonce, BSR, ACK, QRV)."""
        call = self._station_call(call)
        if not call or call == "?" or call == self.mycall():
            return
        h = self.heard.setdefault(call, {"loc": ""})
        h.update(t=time.time(), freq=self.rig_freq, what=what)
        if hyb or "hybride" in (what or "").lower():
            h["hyb_t"] = time.time()              # annonce / image hybride entendue par radio
        if snr is not None:
            h["snr"] = snr
        if loc:
            h["loc"] = loc
            self._remember_loc(call, loc)
        self._heard_refresh()

    def _rxok_add(self, call, report, iid=None):
        """Une station a bien reçu l'image iid (sans iid : l'image affichée)."""
        call = self._station_call(call)
        if not call or call == "?":
            return
        iid = self.rxok_ctx if iid is None else iid
        d = self.rxok_by_id.setdefault(iid, {})
        old = d.get(call)
        if report is None and old is not None and old[0] is not None:
            report = old[0]                       # on garde le report déjà connu
        d[call] = (report, time.time())
        if iid == self.rxok_ctx:
            self._heard_refresh()

    def _rxok_show(self, iid):
        """Rx Ok affiche désormais l'image iid (nouvelle émission, ou image reçue)."""
        if iid != self.rxok_ctx:
            self.rxok_ctx = iid
            self.rxok = self.rxok_by_id.setdefault(iid, {})
            # on ne garde en mémoire que les 50 dernières images
            for k in list(self.rxok_by_id)[:-50]:
                if k != iid:
                    del self.rxok_by_id[k]
        self._heard_refresh()

    def _rxok_reset(self, iid=None):
        if iid is None:
            self.rxok_by_id.pop(self.rxok_ctx, None)
            iid = self.rxok_ctx
        else:
            self.rxok_by_id.pop(iid, None)
        self.rxok_ctx = None
        self._rxok_show(iid)

    # ------------------------------------------------- changer de fréquence par CAT (idée de G7VQV)
    def _freq_presets(self):
        out = []
        for item in self.conf.get("freq_presets") or DEFAULTS["freq_presets"]:
            try:
                hz, side = int(item[0]), str(item[1]).upper()
                out.append((hz, side if side in ("LSB", "USB") else ("LSB" if hz < 10_000_000 else "USB")))
            except (TypeError, ValueError, IndexError):
                continue
        return out

    def _fill_qsy_menu(self, m):
        m.delete(0, "end")
        for hz, side in self._freq_presets():
            band = audio.band_of(hz) or ""
            mark = "● " if self.rig_freq and abs(int(self.rig_freq) - hz) < 1500 else "   "
            m.add_command(label=f"{mark}{hz / 1e6:.3f} MHz   {band}  {side}",
                          command=lambda h=hz, s=side: self._qsy(h, s))
        m.add_separator()
        m.add_command(label=tr("Autre fréquence…"), command=self._qsy_ask)
        m.add_command(label=tr("Modifier la liste…"), command=self._qsy_edit)

    def _freq_menu_at(self, w):
        """Menu des fréquences ouvert sous le bouton « Fréquence ▾ »."""
        m = tk.Menu(self, tearoff=0)
        self._fill_qsy_menu(m)
        m.tk_popup(w.winfo_rootx(), w.winfo_rooty() + w.winfo_height())

    def _freq_menu(self, event=None):
        """Clic sur la fréquence affichée : menu des fréquences image."""
        m = tk.Menu(self, tearoff=0)
        self._fill_qsy_menu(m)
        x, y = (event.x_root, event.y_root) if event else (self.winfo_pointerx(), self.winfo_pointery())
        m.tk_popup(x, y)

    def _qsy(self, hz, side=None):
        """Envoie le poste sur `hz` (Hz) par CAT, en tâche de fond."""
        if self.tx_busy:
            messagebox.showinfo(APP, tr("Émission en cours : changez de fréquence après."))
            return
        if radio.rig_entry(self.radio_cfg["rig"])["kind"] == "none":
            messagebox.showinfo(APP, tr("Pas de liaison CAT : choisissez d'abord le poste (Réglages → Poste "
                                        "radio…) pour que HFImage puisse changer la fréquence."))
            return
        side = side or ("LSB" if hz < 10_000_000 else "USB")
        self.log(tr("Changement de fréquence :") + f" {hz / 1e6:.3f} MHz {side}…")

        def run():
            try:
                with self.rig_lock:
                    r = self._rig_open()
                    if not getattr(r, "can_qsy", True):
                        # commandes CAT perso sans CI-V : HFImage ne connaît pas la commande de fréquence
                        self.ui(self.log, tr("Commandes CAT personnalisées : changez la fréquence sur le poste."))
                        return
                    msg = r.qsy(hz, side)
                self.ui(self.log, msg)
            except Exception as e:
                self.ui(self.log_exc, "Changement de fréquence", e)
                self.ui(messagebox.showerror, APP, tr("Changement de fréquence impossible :") + f"\n{tr(str(e))}")
            self._rig_kick.set()                  # relecture tout de suite (fréquence, mode, bande)
        threading.Thread(target=run, daemon=True).start()

    @staticmethod
    def _parse_mhz(txt):
        """« 7.058 », « 7,058 », « 7058 » (kHz) ou « 7058000 » (Hz) -> Hz, sinon None."""
        t = str(txt or "").strip().lower().replace(",", ".").replace("mhz", "").replace("khz", "").strip()
        try:
            v = float(t)
        except ValueError:
            return None
        hz = v * 1e6 if v < 1000 else (v * 1e3 if v < 1e6 else v)
        return int(round(hz)) if 1_000_000 <= hz <= 470_000_000 else None

    def _qsy_ask(self):
        from tkinter import simpledialog
        cur = f"{self.rig_freq / 1e6:.3f}" if self.rig_freq else ""
        t = simpledialog.askstring(APP, tr("Fréquence (MHz), ex. 7.058 :"), initialvalue=cur, parent=self)
        if t is None:
            return
        hz = self._parse_mhz(t)
        if hz is None:
            messagebox.showerror(APP, tr("Fréquence illisible :") + f" {t}")
            return
        self._qsy(hz)

    # ------------------------------------------------------------- phrases des bulles
    DEFAULT_PHRASES = ("Bonjour de {MOI}", "Bonsoir de {MOI}", "Merci pour l'image ! 73 de {MOI}",
                       "Image bien reçue 5/5", "Bon week-end à tous !", "{MOI} — {PRENOM} — {LOC}")

    def _bubble_phrases(self):
        """Phrases du menu « Phrases ▾ » : celles de l'utilisateur, sinon la liste de départ traduite."""
        lst = self.conf.get("bub_phrases")
        if isinstance(lst, list):
            return [str(p) for p in lst if str(p).strip()]
        return [tr(p) for p in self.DEFAULT_PHRASES]

    def _phrase_fill(self, p):
        """{MOI} / {CALL}, {PRENOM} / {NAME}, {LOC} -> indicatif, prénom, locator."""
        call = self.mycall() or ""
        name = self.myname() or ""
        loc = self.v_loc.get().strip().upper() if hasattr(self, "v_loc") else ""
        out = str(p)
        for keys, val in ((("{MOI}", "{CALL}"), call), (("{PRENOM}", "{NAME}"), name), (("{LOC}",), loc)):
            for k in keys:
                out = out.replace(k, val).replace(k.lower(), val)
        if "—" in out:                                  # sans prénom : « F4GOP — IN98QR », pas « F4GOP —  — »
            out = " — ".join(x.strip() for x in out.split("—") if x.strip())
        return re.sub(r"  +", " ", out).strip()

    def _phrases_edit(self, parent=None):
        """Liste des phrases des bulles, une par ligne."""
        w = tk.Toplevel(parent or self)
        w.title(tr("Phrases des bulles"))
        w.transient(parent or self)
        f = ttk.Frame(w, padding=10)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text=tr("Une phrase par ligne. {MOI} = votre indicatif, {PRENOM} = votre prénom, "
                             "{LOC} = votre locator."), wraplength=420, justify="left").pack(anchor="w")
        t = tk.Text(f, width=48, height=12, font=("TkDefaultFont", 10), wrap="none")
        t.pack(fill="both", expand=True, pady=6)
        t.insert("1.0", "\n".join(self._bubble_phrases()))
        b = ttk.Frame(f)
        b.pack(fill="x")

        def save():
            self.conf["bub_phrases"] = [x.strip() for x in t.get("1.0", "end").splitlines() if x.strip()]
            self._save_conf_file()
            w.destroy()

        def reset():
            t.delete("1.0", "end")
            t.insert("1.0", "\n".join(tr(p) for p in self.DEFAULT_PHRASES))
        ttk.Button(b, text=tr("Enregistrer"), command=save).pack(side="right")
        ttk.Button(b, text=tr("Annuler"), command=w.destroy).pack(side="right", padx=6)
        ttk.Button(b, text=tr("Liste d'origine"), command=reset).pack(side="left")
        self._translate_ui(w)
        return w

    def _qsy_edit(self):
        """Liste des fréquences du menu, une par ligne : « 7.058 LSB »."""
        w = tk.Toplevel(self)
        w.title(tr("Fréquences du menu"))
        w.transient(self)
        f = ttk.Frame(w, padding=10)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text=tr("Une fréquence par ligne, en MHz, suivie de LSB ou USB (ex. « 7.058 LSB »)."),
                  wraplength=380, justify="left").pack(anchor="w")
        t = tk.Text(f, width=28, height=10, font=("TkFixedFont", 10))
        t.pack(fill="both", expand=True, pady=6)
        t.insert("1.0", "\n".join(f"{hz / 1e6:.3f} {side}" for hz, side in self._freq_presets()))
        b = ttk.Frame(f)
        b.pack(fill="x")

        def save():
            out, bad = [], []
            for line in t.get("1.0", "end").splitlines():
                parts = line.split()
                if not parts:
                    continue
                hz = self._parse_mhz(parts[0])
                side = parts[1].upper() if len(parts) > 1 else ""
                if hz is None or side not in ("", "LSB", "USB"):
                    bad.append(line.strip())
                    continue
                out.append([hz, side or ("LSB" if hz < 10_000_000 else "USB")])
            if bad:
                messagebox.showerror(APP, tr("Lignes illisibles :") + "\n" + "\n".join(bad), parent=w)
                return
            self.conf["freq_presets"] = sorted(out)
            self._save_conf_file()
            w.destroy()

        def reset():
            t.delete("1.0", "end")
            t.insert("1.0", "\n".join(f"{hz / 1e6:.3f} {side}" for hz, side in DEFAULTS["freq_presets"]))
        ttk.Button(b, text=tr("Enregistrer"), command=save).pack(side="right")
        ttk.Button(b, text=tr("Annuler"), command=w.destroy).pack(side="right", padx=6)
        ttk.Button(b, text=tr("Liste d'origine"), command=reset).pack(side="left")

    def _qsy_station(self):
        """Clic droit dans la liste des stations : aller sur la fréquence de la station choisie."""
        lst = self.lst_heard
        sel = lst.curselection()
        if not sel:
            messagebox.showinfo(APP, tr("Choisissez d'abord une station dans la liste."))
            return
        call = self._heard_names[sel[0]]
        on = {str(d["call"]).upper(): d for d in self.online.values()}
        hz = (on.get(call) or {}).get("freq") or self.heard.get(call, {}).get("freq")
        if not hz:
            messagebox.showinfo(APP, tr("Fréquence de cette station inconnue."))
            return
        hz = int(hz)
        side = next((s for f, s in self._freq_presets() if abs(f - hz) < 50_000), None)
        if messagebox.askyesno(APP, tr("Aller sur") + f" {hz / 1e6:.3f} MHz ({call}) ?"):
            self._qsy(hz, side)

    def _heard_clear(self):
        self.heard.clear()
        self._heard_refresh()

    def _heard_refresh(self):
        now = time.time()
        for c in [c for c, h in self.heard.items() if now - h["t"] > HEARD_KEEP_S]:
            del self.heard[c]
        for k in [k for k, d in self.online.items() if now - float(d.get("t", 0)) > presence.STALE_S]:
            del self.online[k]
        # stations en ligne (Internet, avec LEUR fréquence) + stations entendues par radio
        on = {str(d["call"]).upper(): d for d in self.online.values()}
        self._heard_names = sorted(set(on) | set(self.heard))
        # colonne de l'indicatif à la largeur du plus long (PA0041SWL, F4FRC/P…) : colonnes alignées
        cw = max([7] + [len(c) for c in self._heard_names])
        P = self.look.palette() if hasattr(self, "look") else None
        rows = []
        for c in self._heard_names:
            hyb = self._is_hyb(c, on)
            tag = " HYB" if hyb else ""                                # HYB = mode hybride, après la fréquence
            h = self.heard.get(c, {})
            if c in on:
                d = on[c]
                mark = "*" if d.get("state") == "TX" else " "        # * = en émission
                # fréquence publiée par la station ; sinon celle où on l'a entendue par radio
                fq = d.get("freq") or h.get("freq")
                dot = ("● " if P else "")                                  # Moderne : ● en ligne
                rows.append((f"{dot}{c:<{cw}}{mark}{self._mhz(fq):>6}{tag}",
                             self._c("#c01818" if d.get("state") == "TX" else ("#1f4fbf" if hyb else "#062e06"))))
            else:
                # entendue par radio seulement (pas en ligne) : en gris-vert (bleu pâle si hybride)
                dot = ("○ " if P else "")                                  # Moderne : ○ entendue par radio
                rows.append((f"{dot}{c:<{cw}} {self._mhz(h.get('freq')):>6}{tag}",
                             self._c(("#5a78b8" if hyb else "#4a7a4a") if now - h["t"] < 1800 else "#8a9a8a")))
        App._sync_list(self.lst_heard, self._heard_names, rows)
        self._rxok_names = sorted(self.rxok)
        rw = max([7] + [len(c) for c in self._rxok_names])
        rows = []
        for c in self._rxok_names:
            rep = self.rxok[c][0]
            if P and rep is not None:
                # Moderne : couleur selon le report (mêmes couleurs que la légende de la carte)
                col = "#%02x%02x%02x" % stationmap.report_color(rep)
                if P["dark"]:                                     # fond sombre : couleur éclaircie
                    h_, l_, s_ = theme._hls(col)
                    col = theme._from_hls(h_, max(l_, 0.6), s_)
                rows.append((f"{c:<{rw}}{f'{rep:+d} dB':>7}{self._name_tail(c)}", col))
            else:
                rows.append((f"{c:<{rw}}{'' if rep is None else f'{rep:+d} dB':>7}{self._name_tail(c)}", None))
        App._sync_list(self.lst_rxok, self._rxok_names, rows)
        fr = f" - {self._mhz(self.rig_freq)}" if self.rig_freq else ""
        self._set_text(self.lb_heard, tr(f"Stations ({len(self._heard_names)})") + fr)
        self._net_status()
        self._set_text(self.lb_rxok, tr(f"Rx Ok ({len(self.rxok)})"))
        if self.map_win is not None and self.map_win.alive() and self.map_win._drag is None:
            self.map_win.redraw()

    @staticmethod
    def _no_xscroll(lb):
        """xscrollcommand qui ramène aussitôt la liste au début de la ligne."""
        def cb(first, last):
            if float(first) > 0:
                lb.after_idle(lambda: lb.xview_moveto(0))
        return cb

    @staticmethod
    def _sync_list(lst, keys, rows):
        """Met à jour une liste (Stations, Rx Ok) sans la faire « sauter » (demande de SWLPete) :
        rien n'est touché si rien n'a changé ; sinon seules les lignes modifiées sont réécrites, et
        la station sélectionnée et la partie de la liste qu'on regarde restent les mêmes.
        keys : indicatif de chaque ligne ; rows : [(texte, couleur ou None)]."""
        old_keys = getattr(lst, "_keys", [])
        old_rows = getattr(lst, "_rows", [])
        if old_keys == list(keys) and old_rows == list(rows):
            lst.xview_moveto(0)                         # toujours depuis le début de la ligne
            return
        sel = lst.curselection()
        sel_key = old_keys[sel[0]] if sel and sel[0] < len(old_keys) else None
        top = lst.nearest(0) if old_keys else 0
        top_key = old_keys[top] if 0 <= top < len(old_keys) else None
        frac = lst.yview()[0]
        if old_keys == list(keys):                      # mêmes stations : on réécrit les lignes changées
            for i, (a, b) in enumerate(zip(old_rows, rows)):
                if a != b:
                    lst.delete(i)
                    lst.insert(i, b[0])
                    if b[1]:
                        lst.itemconfigure(i, fg=b[1])
        else:
            lst.delete(0, "end")
            for text, fg in rows:
                lst.insert("end", text)
                if fg:
                    lst.itemconfigure("end", fg=fg)
        lst._keys, lst._rows = list(keys), list(rows)
        # même station en haut de la partie visible (une station qui arrive plus haut ne décale rien)
        if top_key in keys:
            lst.yview(keys.index(top_key))
        else:
            lst.yview_moveto(frac)
        if sel_key in keys:
            lst.selection_clear(0, "end")
            lst.selection_set(keys.index(sel_key))
        # toujours affichée depuis le début de la ligne : un glisser à la souris décalait la liste
        # vers la droite et coupait le début des indicatifs (« 4FR79 » pour « 14FR79 »)
        lst.xview_moveto(0)

    def _is_hyb(self, c, on=None):
        """La station est-elle en mode hybride ? (présence Internet, sinon annonce hybride
        entendue par radio dans la dernière demi-heure)."""
        on = on if on is not None else {str(d["call"]).upper(): d for d in self.online.values()}
        if c in on and "hyb" in on[c]:
            return bool(on[c]["hyb"])
        return time.time() - self.heard.get(c, {}).get("hyb_t", 0) < 1800

    def _heard_detail(self, lst=None):
        lst = lst or self.lst_heard
        sel = lst.curselection()
        names = self._heard_names if lst is self.lst_heard else self._rxok_names
        if not sel or sel[0] >= len(names):
            return
        c = names[sel[0]]
        h = self.heard.get(c, {})
        parts = [self._label(c)]
        d = next((x for x in self.online.values() if str(x.get("call")).upper() == c), None)
        if d:
            parts.append(tr("en ligne") + (f", {audio.format_freq(d['freq'], True)}" if d.get("freq") else "")
                         + (f" {d['mode']}" if d.get("mode") else "")
                         + (" — " + tr("en émission") if d.get("state") == "TX" else ""))
        if self._is_hyb(c):
            parts.append(tr("en mode hybride (image par Internet)"))
        loc = h.get("loc") or self.known_loc.get(c)
        if loc:
            parts.append(loc)
        if h.get("t"):
            parts.append(tr("entendue à {0}").replace("{0}", clocktz.fmt("%H:%M", h["t"])))
        if h.get("freq"):
            parts.append(audio.format_freq(h["freq"], True))
        if h.get("snr") is not None:
            parts.append(f"SNR {h['snr']:+.0f} dB")
        if h.get("what"):
            parts.append(tr(h["what"]))
        if c in self.rxok:
            rep = self.rxok[c][0]
            parts.append(tr("a reçu votre image") + ("" if rep is None else f" ({rep:+d} dB)"))
        self.log(" — ".join(parts))
        self.show_map(c)

    def send_qrv(self):
        call = self.mycall()
        if not call:
            messagebox.showinfo(APP, "Indiquez d'abord votre indicatif (Réglages).")
            return
        if self.send_control(protocol.qrv_frame(call, self.v_loc.get()), "présence (QRV)"):
            self.station_event(call, "Présence (QRV) envoyée", "DATAC0")

    def station_event(self, call, evt, mode="", snr=None, detail=""):
        """Ajoute une ligne au journal des stations (écran + stations.csv)."""
        hh = clocktz.fmt("%H:%M:%S", suffix=False)
        snr_s = "" if snr is None else f"{snr:+.0f} dB"
        if call and call != "?" and snr is not None and mode != "DATAC0":
            self.snr_by_call[call] = snr
        if self.rig_freq:
            detail = (detail + " — " if detail else "") + audio.format_freq(self.rig_freq, True)
        self.tree.insert("", 0, values=(hh, call or "?", tr(evt), mode, snr_s, tr(detail)))
        try:
            os.makedirs(DEFAULT_OUT, exist_ok=True)
            p = os.path.join(DEFAULT_OUT, "stations.csv")
            new = not os.path.exists(p)
            with open(p, "a", encoding="utf-8") as f:
                if new:
                    f.write("date_utc;indicatif;evenement;mode;snr;detail\n")
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())};{call};{evt};{mode};"
                        f"{snr_s};{detail}\n")
        except Exception:
            pass

    def _tab_sim(self, nb):
        w = self.tab_sim = tk.Frame(nb)
        t = ttk.Frame(w, padding=10)
        t.pack(fill="both", expand=True)
        nb.add(w, text="  Simulation  ")
        ttk.Label(t, text="Teste l'image préparée dans l'onglet Émission sur un canal HF simulé "
                          "(bruit + fading CCIR), avec compléments automatiques (NACK).",
                  wraplength=700).pack(anchor="w")
        g = ttk.Frame(t)
        g.pack(anchor="w", pady=10)
        self.v_snr = tk.DoubleVar(value=5)
        self.v_fading = tk.StringVar(value="moderate")
        ttk.Label(g, text="SNR (dB, dans 3 kHz)").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(g, textvariable=self.v_snr, from_=-10, to=30, increment=1, width=8).grid(row=0, column=1, padx=6)
        ttk.Label(g, text="Canal").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Combobox(g, textvariable=self.v_fading, values=["none", "good", "moderate", "poor"],
                     width=10, state="readonly").grid(row=1, column=1, padx=6)
        ttk.Button(t, text="Lancer la simulation", command=self.simulate).pack(anchor="w")
        self.v_sim = TrVar(value="")
        ttk.Label(t, textvariable=self.v_sim, justify="left", font=("TkFixedFont", 10)).pack(anchor="w", pady=10)

    def _tab_conf(self, nb=None):
        win = self.win_conf = tk.Toplevel(self)
        win.title(f"{APP} — Réglages")
        win.withdraw()
        win.transient(self)
        win.protocol("WM_DELETE_WINDOW", win.withdraw)
        # contenu dans une zone qui défile : sur un écran moyen, la fenêtre ne dépasse pas
        # l'écran et les boutons du bas (Enregistrer, Fermer) restent toujours visibles
        sc = tk.Frame(win)
        sc.pack(side="top", fill="both", expand=True)
        cv = self._conf_canvas = tk.Canvas(sc, highlightthickness=0, bd=0)
        vs = ttk.Scrollbar(sc, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=vs.set)
        vs.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        t = self._conf_inner = ttk.Frame(cv, padding=10)
        tid = cv.create_window(0, 0, window=t, anchor="nw")

        def _inner_cfg(_e=None):
            cv.configure(scrollregion=(0, 0, t.winfo_reqwidth(), t.winfo_reqheight()))
            need = t.winfo_reqheight() > cv.winfo_height() + 1
            if need and not vs.winfo_ismapped():
                vs.pack(side="right", fill="y", before=cv)
            elif not need and vs.winfo_ismapped():
                vs.pack_forget()
                cv.yview_moveto(0)

        def _canvas_cfg(e):
            cv.itemconfigure(tid, width=max(e.width, t.winfo_reqwidth()))
            _inner_cfg()

        t.bind("<Configure>", _inner_cfg)
        cv.bind("<Configure>", _canvas_cfg)

        def _wheel(e):
            if t.winfo_reqheight() <= cv.winfo_height():
                return
            w = e.widget
            if isinstance(w, (ttk.Combobox, ttk.Spinbox, tk.Spinbox)):
                return                                  # la molette sert à la liste / au compteur
            step = -1 if (getattr(e, "num", 0) == 4 or e.delta > 0) else 1
            cv.yview_scroll(step * 3, "units")

        win.bind("<MouseWheel>", _wheel, add="+")
        win.bind("<Button-4>", _wheel, add="+")
        win.bind("<Button-5>", _wheel, add="+")
        colL = ttk.Frame(t)
        colL.pack(side="left", fill="both", expand=True, padx=(0, 6))
        st = ttk.LabelFrame(colL, text="Station", padding=8)
        st.pack(fill="x", pady=(0, 10))
        ttk.Label(st, text="Indicatif").grid(row=0, column=0, sticky="w")
        ttk.Entry(st, textvariable=self.v_call, width=12).grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(st, text="Locator").grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Entry(st, textvariable=self.v_loc, width=8).grid(row=0, column=3, sticky="w", padx=6)
        ttk.Label(st, text="Prénom").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(st, textvariable=self.v_opname, width=12).grid(row=2, column=1, sticky="w", padx=6, pady=(6, 0))
        ttk.Label(st, text="Langue / Language").grid(row=1, column=0, sticky="w", pady=(6, 0))
        names = list(i18n.LANGS.values())
        self.v_lang = tk.StringVar(value=i18n.LANGS.get(i18n.get_lang(), "Français"))
        cb = ttk.Combobox(st, textvariable=self.v_lang, values=names, width=12, state="readonly")
        cb.grid(row=1, column=1, columnspan=2, sticky="w", padx=6, pady=(6, 0))
        cb.bind("<<ComboboxSelected>>", lambda e: self.set_language(
            [k for k, v in i18n.LANGS.items() if v == self.v_lang.get()][0]))
        colR = ttk.Frame(t)
        colR.pack(side="left", fill="both", expand=True, padx=(6, 0))

        g = ttk.LabelFrame(colL, text="Audio", padding=8)
        g.pack(fill="x")
        self.v_out = tk.StringVar(value=self.conf["out_dev"])
        self.v_in = tk.StringVar(value=self.conf["in_dev"])
        self.v_lvl = tk.IntVar(value=self.conf["level"])
        self.cb_out = ttk.Combobox(g, textvariable=self.v_out, width=44, state="readonly")
        self.cb_in = ttk.Combobox(g, textvariable=self.v_in, width=44, state="readonly")
        ttk.Label(g, text="Sortie (vers le poste)").grid(row=0, column=0, sticky="w")
        self.cb_out.grid(row=0, column=1, padx=6, pady=3, sticky="w")
        ttk.Label(g, text="Entrée (depuis le poste)").grid(row=1, column=0, sticky="w")
        self.cb_in.grid(row=1, column=1, padx=6, pady=3, sticky="w")
        ttk.Label(g, text="Niveau d'émission (%)").grid(row=2, column=0, sticky="w")
        ttk.Scale(g, variable=self.v_lvl, from_=1, to=100, length=260).grid(row=2, column=1, sticky="w", padx=6)
        bf = ttk.Frame(g)
        bf.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Button(bf, text="Actualiser", command=lambda: self._rescan_audio(manual=True)).pack(side="left")
        self.cb_in.bind("<<ComboboxSelected>>", lambda e: self._in_changed())
        self.cb_out.bind("<<ComboboxSelected>>", lambda e: self.save_conf(quiet=True))
        ttk.Button(bf, text="Tester la sortie (1 kHz)", command=self.test_audio).pack(side="left", padx=6)
        ttk.Label(g, text="Kenwood : « Haut-parleurs (USB Audio CODEC) » et\n"
                          "« Microphone (USB Audio CODEC) », de préférence en [MME].\n"
                          "Réglez le niveau pour que l'ALC ne bouge pas.",
                  foreground="#555", justify="left").grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.v_qrm = tk.BooleanVar(value=bool(self.conf.get("qrm_filter", True)))

        def _qrm_changed():
            self.conf["qrm_filter"] = bool(self.v_qrm.get())
            if self.rx_engine is not None:
                self.rx_engine.qrm = self.conf["qrm_filter"]
            self._save_conf_file()
            self.log("Coupe-QRM à la réception : " + ("marche" if self.conf["qrm_filter"] else "arrêt"))
        ttk.Checkbutton(g, text="Coupe-QRM à la réception (porteuses, CW, RTTY, signaux voisins)",
                        variable=self.v_qrm, command=_qrm_changed).grid(row=5, column=0, columnspan=2,
                                                                        sticky="w", pady=(6, 0))

        c = ttk.LabelFrame(colL, text="Poste radio (CAT / PTT)", padding=8)
        c.pack(fill="x", pady=10)
        self.lb_radio = ttk.Label(c, text="", wraplength=380, justify="left")
        self.lb_radio.grid(row=0, column=0, columnspan=2, sticky="w")
        pb = ttk.Frame(c)
        pb.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Button(pb, text="Poste radio…", command=self.radio_dialog).pack(side="left")
        ttk.Button(pb, text="Vérifier le poste", command=self.check_rig).pack(side="left", padx=6)
        ttk.Button(pb, text="Tester le PTT (1 s)", command=self.test_ptt).pack(side="left")
        da = ttk.Frame(c)
        da.grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(da, text="Poste pas en DATA avant d'émettre :").pack(side="left")
        self._data_act_names = {tr(v): k for k, v in DATA_ACTIONS.items()}
        self.v_dataact = tk.StringVar(value=tr(DATA_ACTIONS.get(self.conf.get("data_action", "switch"), DATA_ACTIONS["ask"])))
        cbd = ttk.Combobox(da, textvariable=self.v_dataact, values=list(self._data_act_names), state="readonly", width=46)
        cbd.pack(side="left", padx=4)

        def _act_changed(_e=None):
            self.conf["data_action"] = self._data_act_names.get(self.v_dataact.get(), "ask")
            self._save_conf_file()
        cbd.bind("<<ComboboxSelected>>", _act_changed)
        ttk.Label(c, text="Plus de 300 postes (Hamlib), Kenwood en direct, OmniRig, FLRig.\n"
                          "Le port doit être libre : fermez les autres logiciels qui l'utilisent,\n"
                          "ou passez par OmniRig / FLRig pour partager le poste.",
                  foreground="#555", justify="left").grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self._radio_summary()

        h = ttk.LabelFrame(colR, text="Mode hybride (serveur web)", padding=8)
        h.pack(fill="x")
        self.v_hhost = tk.StringVar(value=self.conf["hyb_host"])
        self.v_hport = tk.IntVar(value=self.conf["hyb_port"])
        self.v_huser = tk.StringVar(value=self.conf["hyb_user"])
        self.v_hpass = tk.StringVar(value=hybrid.unprotect(self.conf["hyb_pass"]))
        self.v_hdir = tk.StringVar(value=self.conf["hyb_dir"])
        self.v_htls = tk.BooleanVar(value=self.conf["hyb_tls"])
        self.v_hurl = tk.StringVar(value=self.conf["hyb_url"])
        self.v_hauto = tk.BooleanVar(value=self.conf["hyb_auto"])
        self.v_hwidth = tk.StringVar(value=str(self.conf["hyb_width"]))
        self.v_hkb = tk.DoubleVar(value=self.conf["hyb_kb"])
        rows = [("Serveur FTP", ttk.Entry(h, textvariable=self.v_hhost, width=30)),
                ("Port", ttk.Entry(h, textvariable=self.v_hport, width=6)),
                ("Identifiant", ttk.Entry(h, textvariable=self.v_huser, width=30)),
                ("Mot de passe", ttk.Entry(h, textvariable=self.v_hpass, width=30, show="•")),
                ("Dossier", ttk.Entry(h, textvariable=self.v_hdir, width=30)),
                ("Lien public", ttk.Entry(h, textvariable=self.v_hurl, width=30))]
        for i, (lab, w) in enumerate(rows):
            ttk.Label(h, text=lab).grid(row=i, column=0, sticky="w")
            w.grid(row=i, column=1, sticky="w", padx=6, pady=2)
        ttk.Checkbutton(h, text="FTPS (connexion chiffrée)", variable=self.v_htls).grid(
            row=6, column=1, sticky="w", padx=6)
        ttk.Label(h, text="Image hybride : largeur max (px) / taille (ko)").grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(6, 0))
        sz = ttk.Frame(h)
        sz.grid(row=8, column=0, columnspan=2, sticky="w")
        ttk.Combobox(sz, textvariable=self.v_hwidth, values=HYB_WIDTHS,
                     width=7).pack(side="left")
        ttk.Spinbox(sz, textvariable=self.v_hkb, from_=5, to=5000, increment=20, width=7).pack(side="left", padx=6)
        gf = ttk.Frame(h)
        gf.grid(row=9, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Label(gf, text="GIF animé : taille max (ko)").pack(side="left")
        self.v_gifkb = tk.DoubleVar(value=self.conf.get("gif_kb", 2000))
        ttk.Spinbox(gf, textvariable=self.v_gifkb, from_=50, to=8000, increment=250, width=7).pack(side="left", padx=6)
        ttk.Checkbutton(h, text="Télécharger automatiquement les images hybrides reçues",
                        variable=self.v_hauto).grid(row=12, column=0, columnspan=2, sticky="w", pady=(6, 0))
        rxm = ttk.Frame(h)
        rxm.grid(row=13, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Label(rxm, text="Fichiers hybrides reçus : taille max").pack(side="left")
        self.v_hrxmax = TrVar()
        self.v_hrxmax.set(self._rxmax_label(self.conf.get("hyb_rx_max_mb", 200)))
        cb = ttk.Combobox(rxm, textvariable=self.v_hrxmax, values=[tr(x) for x in HYB_RX_MAX], width=12,
                          state="readonly")
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._rxmax_changed())
        kp = ttk.Frame(h)
        kp.grid(row=14, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Label(kp, text="Mes images gardées sur le serveur").pack(side="left")
        self.v_hkeep = TrVar()
        self.v_hkeep.set(self._keep_label(self.conf.get("hyb_keep", 3)))
        cb = ttk.Combobox(kp, textvariable=self.v_hkeep, values=[tr(x) for x in HYB_KEEP], width=20,
                          state="readonly")
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._keep_changed())
        hb = ttk.Frame(h)
        hb.grid(row=10, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Button(hb, text="Tester le serveur", command=self.test_hybrid).pack(side="left")
        ttk.Button(hb, text="Site web / Digi-Sites…", command=self.web_dialog).pack(side="left", padx=6)
        ttk.Label(h, text="Ex. : serveur ftpperso.free.fr, lien http://monsite.free.fr/hfimage/\n"
                          "Le lien public doit pointer vers le dossier ci-dessus.\n"
                          "Seul ce lien passe par radio, jamais le mot de passe.",
                  foreground="#555", justify="left").grid(row=11, column=0, columnspan=2, sticky="w", pady=(6, 0))

        af = ttk.LabelFrame(colR, text="Apparence", padding=8)
        af.pack(fill="x", pady=(10, 0))
        self._theme_names = {tr(n): n for n in list(theme.THEMES) + ["Personnalisée"]}
        self._size_names = {tr(n): n for n in theme.FONT_SIZES}
        self.v_theme = tk.StringVar(value=tr(self.conf.get("theme", "Vert EasyPal")))
        self.v_font = tk.StringVar(value=self.conf.get("font_family", "(par défaut)"))
        self.v_fsize = tk.StringVar(value=theme.size_name(self.conf.get("font_size", "9")))
        try:
            have = {f.lower() for f in tkfont.families(self)}
        except tk.TclError:
            have = set()
        fonts = [f for f in theme.FONTS if f.startswith("(") or not have or f.lower() in have]
        ttk.Label(af, text="Couleurs").grid(row=0, column=0, sticky="w")
        cb_t = ttk.Combobox(af, textvariable=self.v_theme, values=list(self._theme_names), state="readonly", width=16)
        cb_t.grid(row=0, column=1, sticky="w", padx=4)
        ttk.Button(af, text="Couleur personnalisée…", command=self._pick_color).grid(row=0, column=2, padx=4)
        ttk.Label(af, text="Police").grid(row=1, column=0, sticky="w", pady=(4, 0))
        cb_f = ttk.Combobox(af, textvariable=self.v_font, values=fonts, state="readonly", width=16)
        cb_f.grid(row=1, column=1, sticky="w", padx=4, pady=(4, 0))
        ttk.Label(af, text="Taille").grid(row=1, column=2, sticky="e", pady=(4, 0))
        cb_s = ttk.Combobox(af, textvariable=self.v_fsize, values=list(self._size_names), state="readonly", width=11)
        cb_s.grid(row=1, column=3, sticky="w", padx=4, pady=(4, 0))
        for cb in (cb_t, cb_f, cb_s):
            cb.bind("<<ComboboxSelected>>", lambda e: self._apply_look())
        ttk.Checkbutton(af, text="Gras", variable=self.v_fbold, command=self._font_menu).grid(
            row=1, column=4, sticky="w", padx=4, pady=(4, 0))
        ttk.Label(af, text="Couleur du texte").grid(row=2, column=0, sticky="w", pady=(4, 0))
        tcf = ttk.Frame(af)
        tcf.grid(row=2, column=1, columnspan=3, sticky="w", padx=4, pady=(4, 0))
        self.sw_text = tk.Label(tcf, width=6, relief="solid", bd=1, font=("TkDefaultFont", 7))
        self.sw_text._no_theme = True
        self.sw_text.pack(side="left")
        ttk.Button(tcf, text="Choisir…", command=self._pick_text_color).pack(side="left", padx=4)
        ttk.Button(tcf, text="Couleur du thème", command=self._reset_text_color).pack(side="left")
        self._text_swatch()
        # 1.54 : style Classique (EasyPal) ou Moderne (plat, barre du haut), 3 ambiances
        ttk.Label(af, text="Style").grid(row=3, column=0, sticky="w", pady=(8, 0))
        stf = ttk.Frame(af)
        stf.grid(row=3, column=1, columnspan=4, sticky="w", padx=4, pady=(8, 0))
        self.v_lookstyle = tk.StringVar(value=tr("Moderne") if self.conf.get("look_style") == "moderne"
                                        else tr("Classique (EasyPal)"))
        self._modern_names = {tr(n): n for n in theme.MODERN}
        self.v_modern = tk.StringVar(value=tr(self.conf.get("modern_theme", "Vert EasyPal")))
        cb_st = ttk.Combobox(stf, textvariable=self.v_lookstyle, values=[tr("Classique (EasyPal)"), tr("Moderne")],
                             state="readonly", width=18)
        cb_st.pack(side="left")
        ttk.Label(stf, text="Ambiance").pack(side="left", padx=(12, 4))
        cb_am = ttk.Combobox(stf, textvariable=self.v_modern, values=list(self._modern_names), state="readonly",
                             width=12)
        cb_am.pack(side="left")

        def style_ui(*_):
            moderne = self.v_lookstyle.get() == tr("Moderne")
            cb_am.configure(state="readonly" if moderne else "disabled")
            cb_t.configure(state="disabled" if moderne else "readonly")     # couleurs : style Classique
        style_ui()
        for cb in (cb_st, cb_am):
            cb.bind("<<ComboboxSelected>>", lambda e: (style_ui(), self._apply_look()))

        nf = ttk.LabelFrame(colR, text="Internet : stations en ligne (comme EasyPal)", padding=8)
        nf.pack(fill="x", pady=(10, 0))
        self.v_net = tk.BooleanVar(value=bool(self.conf.get("net_on", True)))
        self.v_nethost = tk.StringVar(value=self.conf.get("net_host", presence.DEFAULT_HOST))
        self.v_netport = tk.IntVar(value=int(self.conf.get("net_port", presence.DEFAULT_PORT)))
        ttk.Checkbutton(nf, text="Me signaler et voir les stations qui ont HFImage ouvert",
                        variable=self.v_net, command=self.net_start).grid(row=0, column=0, columnspan=4, sticky="w")
        self.v_updchk = tk.BooleanVar(value=bool(self.conf.get("update_check", True)))

        def _upd_changed():
            self.conf["update_check"] = bool(self.v_updchk.get())
            self._save_conf_file()
        ttk.Checkbutton(nf, text="Vérifier les mises à jour au démarrage (GitHub)", variable=self.v_updchk,
                        command=_upd_changed).grid(row=4, column=0, columnspan=5, sticky="w", pady=(6, 0))
        ttk.Label(nf, text="Serveur").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(nf, textvariable=self.v_nethost, width=24).grid(row=1, column=1, sticky="w", padx=4, pady=(4, 0))
        ttk.Label(nf, text="Port").grid(row=1, column=2, sticky="w", pady=(4, 0))
        ttk.Entry(nf, textvariable=self.v_netport, width=6).grid(row=1, column=3, sticky="w", padx=4, pady=(4, 0))
        ttk.Button(nf, text="Appliquer", command=self.net_start).grid(row=1, column=4, padx=4, pady=(4, 0))
        self.lb_netstat = ttk.Label(nf, text="", foreground="#0a6b0a")
        self.lb_netstat.grid(row=2, column=0, columnspan=5, sticky="w", pady=(4, 0))
        ttk.Label(nf, text="Partage seulement indicatif, locator et fréquence (serveur MQTT public).\n"
                           "Toutes les stations doivent utiliser le même serveur.\n"
                           "Port 1883 bloqué par un pare-feu : HFImage essaie seul 8883, 8884 et 8000.",
                  foreground="#555", justify="left").grid(row=3, column=0, columnspan=5, sticky="w", pady=(4, 0))

        d = ttk.LabelFrame(colR, text="Dossier des images reçues", padding=8)
        d.pack(fill="x", pady=10)
        self.v_folder = tk.StringVar(value=self.conf["folder"])
        df = ttk.Frame(d)
        df.pack(fill="x")
        ttk.Entry(df, textvariable=self.v_folder, width=40).pack(side="left")
        ttk.Button(df, text="…", width=3, command=self._pick_folder).pack(side="left", padx=4)
        cf = ttk.Frame(d)
        cf.pack(fill="x", pady=(6, 0))
        self.v_clean = tk.BooleanVar(value=bool(self.conf.get("rx_clean", True)))
        self.v_clean_days = tk.IntVar(value=int(self.conf.get("rx_clean_days", rxclean.DEFAULT_DAYS)))
        ttk.Checkbutton(cf, text="Effacer les images de plus de", variable=self.v_clean).pack(side="left")
        ttk.Spinbox(cf, from_=1, to=3650, width=5, textvariable=self.v_clean_days).pack(side="left", padx=4)
        ttk.Label(cf, text="jours").pack(side="left")
        ttk.Label(d, text="Images rangées par jour (AAAA-MM-JJ). Seuls ces dossiers sont effacés ;\n"
                          "les fichiers reçus et les anciennes images ne sont jamais touchés.",
                  foreground="#555", justify="left").pack(anchor="w", pady=(4, 0))
        sk = ttk.Frame(d)
        sk.pack(fill="x", pady=(6, 0))
        ttk.Label(sk, text="Images envoyées gardées (dossier « envoyees »)").pack(side="left")
        self.v_sentkeep = TrVar()
        self.v_sentkeep.set(next((k for k, v in SENT_KEEP.items() if v == int(self.conf.get("sent_keep", 0) or 0)),
                                 "Toutes"))
        cb = ttk.Combobox(sk, textvariable=self.v_sentkeep, values=[tr(x) for x in SENT_KEEP], width=20,
                          state="readonly")
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._sentkeep_changed())

        bb = ttk.Frame(win, padding=(10, 6, 10, 8))
        bb.pack(side="bottom", fill="x", before=sc)
        ttk.Separator(win, orient="horizontal").pack(side="bottom", fill="x", before=bb)
        ttk.Button(bb, text="Enregistrer les réglages", command=self.save_conf).pack(side="left")
        ttk.Button(bb, text="Ouvrir le journal", command=self.open_journal).pack(side="left", padx=6)
        ttk.Button(bb, text="Fermer", command=lambda: (self.save_conf(quiet=True), win.withdraw())).pack(side="right")
        self._fill_devices()

    # ------------------------------------------------------------ utilitaires
    def journal_path(self):
        return os.path.join(DEFAULT_OUT, "journal.txt")

    def _journal(self, text):
        try:
            os.makedirs(DEFAULT_OUT, exist_ok=True)
            p = self.journal_path()
            if os.path.exists(p) and os.path.getsize(p) > 2_000_000:
                os.replace(p, p + ".old")
            with open(p, "a", encoding="utf-8") as f:
                f.write(text)
        except Exception:
            pass

    LOG_KEEP = 300               # lignes gardées dans le journal à l'écran

    def log(self, msg):
        line = time.strftime("%H:%M:%S ") + tr(msg) + "\n"
        self.logbox.configure(state="normal")
        self.logbox.insert("end", line)
        # journal à l'écran vidé tout seul : on garde les LOG_KEEP dernières lignes (le programme
        # reste ouvert des jours ; tout reste dans le fichier journal, menu Fichiers → journal)
        n = int(self.logbox.index("end-1c").split(".")[0])
        if n > self.LOG_KEEP + 100:
            self.logbox.delete("1.0", f"{n - self.LOG_KEEP}.0")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")
        self._journal(time.strftime("%Y-%m-%d ") + line)

    def log_exc(self, where, e):
        """Message court à l'écran, trace complète dans le journal."""
        self.log(f"Erreur ({where}) : {e}")
        tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        self._journal(tb)

    def journal_devices(self):
        """Inventaire audio et COM écrit dans le journal (pour le diagnostic)."""
        lines = [f"===== {APP} {VERSION} — {time.strftime('%Y-%m-%d %H:%M:%S')} =====",
                 f"Système : {platform.platform()} — Python {sys.version.split()[0]}"]
        try:
            S = sd()
            lines.append(f"PortAudio : {S.get_portaudio_version()[1]}")
            for i, d in enumerate(S.query_devices()):
                lines.append(f"  {i:2d} {S.query_hostapis(d['hostapi'])['name']:20s} "
                             f"in {d['max_input_channels']} out {d['max_output_channels']} "
                             f"{d['default_samplerate']:.0f} Hz  {d['name']}")
        except Exception as e:
            lines.append(f"Audio indisponible : {e!r}")
        lines.append("Ports COM : " + ", ".join(f"{p} ({d})" for p, d in audio.ports_list()))
        self._journal("\n".join(lines) + "\n")

    def open_journal(self):
        self.journal_devices()
        p = self.journal_path()
        if sys.platform.startswith("win"):
            os.startfile(p)
        else:
            subprocess.Popen(["xdg-open", p])

    def ui(self, fn, *a):
        """Exécute fn dans le thread de l'interface."""
        self.uiq.put((fn, a))

    def _panel_tx(self, job, mode):
        tx = job.get("tx")
        self.panel.set_cell("Mode", "TX", mode or job["kind"])
        self.panel.set_cell("Bande kHz", "TX", f"{MODE_BW.get(mode, 0):.2f}" if mode else "—")
        self.panel.set_cell("Débit b/s", "TX", str(MODE_BPS.get(mode, "—")))
        if mode == engine.DRM_MODE:
            p = getattr(tx, "params", None) or self._drm_params()
            self.panel.set_cell("Mode", "TX", f"EP {'ABE'[p.mode]}/{(4, 16, 64)[p.qam]}")
            self.panel.set_cell("Bande kHz", "TX", "2.20" if p.bandwidth == 0 else "2.40")
            self.wf.mark_mode(waterfall.easypal_band_key(p.mode, p.bandwidth))
            rate = self._drm_rate(p.mode, p.bandwidth, p.qam, p.protection)
            self.panel.set_cell("Débit b/s", "TX", str(rate) if rate else "—")
        sender = getattr(tx, "sender", None)       # (une émission EasyPal n'en a pas)
        if sender is not None and not isinstance(tx, HybridJob):
            self.panel.set_cell("Total", "TX", str(sender.K))
            self.panel.set_cell("Segs OK", "TX", str(sender.sent))
        elif isinstance(tx, engine.DrmTransmission):
            self.panel.set_cell("Total", "TX", f"{len(tx.data)} o")
            self.panel.set_cell("Segs OK", "TX", "—")
        self.panel.set_cell("Position", "TX", tr("émission"))

    # ------------------------------------------------------------- poste radio (CAT)
    def _radio_summary(self):
        if hasattr(self, "lb_radio"):
            self._set_text(self.lb_radio, radio.describe(self.radio_cfg))

    def radio_dialog(self):
        w = getattr(self, "_radio_win", None)
        if w is not None and w.winfo_exists():
            w.lift()
            return
        self._radio_win = radiodlg.RadioDialog(self)

    def set_radio(self, cfg):
        """Nouveaux réglages du poste (fenêtre « Poste radio ») : enregistrés, liaison rouverte."""
        old = self.radio_cfg
        self.radio_cfg = dict(cfg)
        self.conf["radio"] = self.radio_cfg
        self._save_conf_file()
        self._radio_summary()
        self.log("Poste radio : " + radio.describe(self.radio_cfg))
        self._rig_err = None
        if radio.cat_signature(old) != radio.cat_signature(cfg):
            self._rig_close()
            self._rig_kick.set()
        # autre poste : son codec USB vient souvent d'être branché -> cartes son relues
        self.after(300, lambda: self._rescan_audio(manual=False))

    def _in_changed(self):
        """Nouvelle entrée audio choisie : l'écoute repart tout de suite sur elle
        (plus besoin de redémarrer le programme)."""
        self.save_conf(quiet=True)
        if self.tx_busy:
            return                                     # l'écoute reprendra après l'émission, sur la nouvelle entrée
        if self.rx_stream is not None:
            self.toggle_listen(quiet=True)             # arrêt
        if self.v_in.get():
            self.toggle_listen(quiet=True)             # reprise sur la nouvelle entrée
            if self.rx_stream is not None:
                self.log(f"Réception sur : {self.v_in.get()}")

    def _rescan_audio(self, manual=False):
        """Relit la liste des cartes son de Windows (un poste branché ou rallumé après le
        démarrage du programme n'apparaissait qu'après un redémarrage), puis relance l'écoute."""
        if self.tx_busy:
            if manual:
                messagebox.showinfo(APP, "Attendez la fin de l'émission pour actualiser les cartes son.")
            return
        listening = self.rx_stream is not None
        if listening:
            self.toggle_listen(quiet=True)
        try:
            S = sd()
            S._terminate()
            S._initialize()
        except Exception as e:
            self.log(f"Audio : relecture des cartes son impossible ({e})")
        self._fill_devices()
        n_in = len(self.cb_in["values"] or ())
        n_out = len(self.cb_out["values"] or ())
        if manual or listening:
            self.log(f"Cartes son relues : {n_out} sortie(s), {n_in} entrée(s).")
        if (listening or manual) and self.v_in.get() and self.rx_stream is None:
            self.toggle_listen(quiet=True)
    def _rig_close(self):
        with self.rig_lock:
            r, self.rig = self.rig, None
            self.rig_freq = self.rig_mode = None
        if r is not None:
            try:
                r.close()
            except Exception:
                pass
        self.ui(self._show_freq)

    @contextlib.contextmanager
    def rig_hold(self):
        """Libère le port du poste le temps d'un test (fenêtre « Poste radio »)."""
        with self.rig_lock:
            self._rig_hold += 1
        try:
            self._rig_close()
            yield
        finally:
            with self.rig_lock:
                self._rig_hold -= 1
            self._rig_kick.set()

    def _rig_open(self):
        """Liaison CAT ouverte selon les réglages (None : pas de CAT). Peut lever une erreur."""
        with self.rig_lock:
            cfg = self.radio_cfg
            if self.rig is not None and self.rig._sig == radio.cat_signature(cfg):
                return self.rig
            if self.rig is not None:
                self._rig_close()
            if radio.rig_entry(cfg["rig"])["kind"] == "none":
                return None
            r = radio.make_rig(cfg)
            r._sig = radio.cat_signature(cfg)
            self.rig = r
            self.ui(self.log, f"Liaison CAT : {r.model or 'poste'} ({r.port})")
            return r

    def _rig_open_now(self):
        """Comme _rig_open, sans bloquer la fenêtre : si la liaison vient d'échouer, ou si le fil de
        fond est justement en train de l'ouvrir, on donne tout de suite la dernière erreur."""
        if self.rig is not None and self.rig._sig == radio.cat_signature(self.radio_cfg):
            return self.rig
        err = self._rig_err
        if err and time.time() - err[0] < 30:
            raise err[1]
        if not self.rig_lock.acquire(timeout=0.3):
            raise RuntimeError(tr("liaison CAT en cours d'ouverture, réessayez dans quelques secondes"))
        try:
            return self._rig_open()
        except Exception as e:
            self._rig_err = (time.time(), e)
            raise
        finally:
            self.rig_lock.release()

    def _rig_loop(self):
        """Fil de fond : garde la liaison CAT ouverte et lit fréquence / mode régulièrement."""
        last_err, n, last_msg = 0.0, 0, ""
        while not self._closing:
            self._rig_kick.clear()
            cfg = self.radio_cfg
            poll = max(1, int(cfg.get("poll") or 1))
            if radio.rig_entry(cfg["rig"])["kind"] == "none" or self._rig_hold:
                if self.rig is not None and not self._rig_hold:
                    self._rig_close()
                self._rig_kick.wait(1)
                continue
            if self.tx_busy:
                # pendant l'émission, on ne lit pas le poste : une erreur de lecture (HF dans le
                # câble USB…) fermerait la liaison et le poste ne recevrait plus l'arrêt du PTT
                self._rig_kick.wait(0.5)
                continue
            if self.rig is None or self.rig._sig != radio.cat_signature(cfg):
                if time.time() - last_err < 10 and not self._rig_kick.is_set():
                    self._rig_kick.wait(1)
                    continue
                try:
                    self._rig_open()
                    last_msg = ""
                    self._rig_err = None
                except Exception as e:
                    last_err = time.time()
                    self._rig_err = (last_err, e)
                    if str(e) != last_msg:
                        last_msg = str(e)
                        self.ui(self.log, f"Fréquence non lue : {e}")
                    continue
            r = self.rig
            if r is None:
                continue
            if not getattr(r, "reads_freq", True):
                f = r.freq()                           # CAT personnalisé : fréquence envoyée par HFImage
                if f and f != self.rig_freq:
                    self.rig_freq = f
                    self.ui(self._show_freq)
                self._rig_kick.wait(poll)              # port gardé ouvert, rien à lire
                continue
            try:
                f = r.freq()
                if n % max(1, 5 // poll) == 0:
                    self.rig_mode = r.mode()
                if f is None and self.rig_freq is None:
                    raise RuntimeError("le poste ne donne pas sa fréquence")
                if f is not None:
                    self.rig_freq = f
                self.ui(self._show_freq)
            except Exception as e:
                if self.rig is r and not self._rig_hold and not self.tx_busy:
                    self._rig_close()
                    last_err = time.time()
                    self.ui(self.log, f"Liaison CAT perdue : {e}")
            n += 1
            self._rig_kick.wait(poll)

    def _show_freq(self):
        f = self.rig_freq
        if not f:
            self.panel.set_freq("", "")
            self.lb_freq.configure(text="")
            return
        band = audio.band_of(f)
        sub = " · ".join(x for x in (self.rig_mode or "", band) if x)
        self.panel.set_freq(audio.format_freq(f), sub)
        self.lb_freq.configure(text=f"{audio.format_freq(f, True)}  {self.rig_mode or ''}")

    def _clock_text(self):
        """Horloge : heure de Windows (locale, heure d'été comprise), et/ou UTC — clic pour changer."""
        how = self.conf.get("clock", "local")
        loc = time.strftime("%H:%M:%S", time.localtime())
        utc = time.strftime("%H:%M", time.gmtime())
        if how == "utc":
            return time.strftime("%H:%M:%S UTC", time.gmtime())
        if how == "both":
            return f"{loc}   ·   {utc} UTC"
        return loc

    def _clock_cycle(self):
        order = ["local", "both", "utc"]
        cur = self.conf.get("clock", "local")
        self.conf["clock"] = order[(order.index(cur) + 1) % 3 if cur in order else 0]
        clocktz.MODE = self.conf["clock"]
        self._save_conf_file()
        try:
            self.tree.heading("heure", text=clocktz.label(tr("Heure")))
        except (AttributeError, tk.TclError):
            pass
        self._tc_cache = None
        self.lb_clock.configure(text=self._clock_text())
        self.log({"local": "Horloge : heure de Windows", "both": "Horloge : heure de Windows et UTC",
                  "utc": "Horloge : UTC"}[self.conf["clock"]])

    def _clock(self):
        self.lb_clock.configure(text=self._clock_text())
        self._topbar_update()
        if int(time.time()) % 15 == 0 and any(not m["acks"] for m in self.sent_msgs.values()):
            self._msg_sent_refresh()                # « en attente » -> « pas d'accusé » au bout de 3 min
        # liste des stations : fréquence affichée et couleurs selon l'ancienneté
        fr = self.rig_freq
        if fr != getattr(self, "_heard_fr", None) or int(time.time()) % 30 == 0:
            self._heard_fr = fr
            self._heard_refresh()
        # présence Internet : republiée à chaque changement (fréquence, émission…) et chaque minute
        if self.net is not None:
            st = (fr, self.rig_mode, "TX" if self.tx_busy else "RX", self.v_loc.get().strip(),
                  self.mycall(), bool(self.v_hyb.get()), self.myname(), self._my_site())
            now = time.time()
            # indicatif ou prénom en cours de frappe : on attend 3 s sans changement
            # (avant, chaque lettre tapée créait une nouvelle présence : « F4LTX CH », « F4LTX CHR »…)
            typed = (st[4], st[6])
            if typed != getattr(self, "_net_typed", None):
                self._net_typed, self._net_typed_t = typed, now
            settled = now - self._net_typed_t >= 3
            if st != getattr(self, "_net_st", None) or now - getattr(self, "_net_t", 0) > 60:
                if st[4] and st[4] != self.net.call:
                    if settled:
                        self.net_start()                     # indicatif changé : nouvelle présence
                elif settled or st[6] == (self._net_st or (None,) * 8)[6]:
                    self._net_st, self._net_t = st, now
                    self.net.update(freq=fr, mode=self.rig_mode, state=st[2], loc=st[3], hyb=st[5],
                                    name=st[6], site=st[7])
        self.after(1000, self._clock)

    def _tick(self):
        """Toutes les 300 ms : panneau d'état, BSR/ACK automatiques, FIX automatique."""
        try:
            self._update_panel()
            self._bsr_check()
            self._fix_due()
        except Exception as e:
            self.log_exc("Mise à jour", e)
        self.after(300, self._tick)

    _drm_rates = {}

    def _drm_rate(self, mode, bw, qam, prot):
        """Débit utile EasyPal (bit/s) pour ces réglages, calculé par le modem (mis en cache)."""
        key = (mode, bw, qam, prot)
        if key not in self._drm_rates and hamdrm.AVAILABLE:
            try:
                p = hamdrm.make_params("RATE", mode=mode, bandwidth=bw, qam=qam, protection=prot)
                d = hamdrm.estimate(60000, p) - hamdrm.estimate(20000, p)
                self._drm_rates[key] = int(round(8 * 40000 / d)) if d > 0 else None
            except Exception:
                self._drm_rates[key] = None
        return self._drm_rates.get(key)

    def _update_panel_drm(self, eng, now, listening):
        """Panneau de gauche quand la réception la plus récente est en mode EasyPal.
        -> True si le panneau a été rempli avec les infos EasyPal."""
        st = getattr(eng, "drm_status", None) or {}
        if now - eng.drm_t > 10:
            self._drm_followed = False                   # plus de signal EasyPal : prochaine émission reçue
        if not st or not listening:
            return False
        act_t = max([a["t"] for a in eng.activity.values()] or [0])
        recent = now - eng.drm_t < 15                   # signal EasyPal décodé il y a peu
        if not (st.get("time_sync") or recent) or act_t > eng.drm_t:
            return False                                # rien en EasyPal, ou un mode DATAC plus récent
        P = self.panel
        P.set_led("Sync", LED_GREEN if st.get("time_sync") else LED_OFF)
        if st.get("fac_valid"):
            P.set_led("Trame", LED_GREEN if st.get("msc_valid") else LED_RED)
        else:
            P.set_led("Trame", LED_AMBER if st.get("frame_sync") else LED_OFF)
        if not recent:
            return True                                 # synchronisation en cours : seulement les voyants
        good = getattr(eng, "drm_good", None) or st      # derniers paramètres valides
        snr = good.get("snr")
        P.set_bar("SNR", snr, -10, 20, "" if snr is None else f"{snr:+.0f} dB")
        m = good.get("mode", -1)
        qam = good.get("qam", 0)
        bw = good.get("bandwidth", 1)
        prot = good.get("protection", 0)
        # cellule de 7 caractères : « EP B/16 » (EP = EasyPal)
        mode_txt = "EP " + ("ABE"[m] if 0 <= m <= 2 else "?") + (f"/{qam}" if qam else "")
        P.set_cell("Mode", "RX", mode_txt)
        P.set_cell("Bande kHz", "RX", "2.20" if bw == 0 else "2.40")
        self.wf.mark_mode(waterfall.easypal_band_key(m, bw))
        rate = self._drm_rate(m, bw, {4: 0, 16: 1, 64: 2}.get(qam, 1), 1 if prot == 1 else 0) \
            if 0 <= m <= 2 else None
        P.set_cell("Débit b/s", "RX", str(rate) if rate else "—")
        if st.get("callsign") or good.get("callsign"):
            self._rx_call(st.get("callsign") or good.get("callsign"), eng.drm_t)
        got, K = st.get("seg_received", 0), st.get("seg_total", 0)
        if K > 0:
            self._rx_tab_auto(("easypal", K, st.get("callsign") or good.get("callsign")))
            # dès le début : mode EasyPal (A/B/E et QAM repris quand l'image sera complète).
            # Une seule fois par émission reçue : l'état EasyPal reste affiché après la fin du signal,
            # et le mode choisi ensuite à la main (Auto…) ne doit pas être remis sur EasyPal (1.10).
            if time.time() - eng.drm_t < 3 and not getattr(self, "_drm_followed", False):
                self._drm_followed = True
                self._follow_mode({"call": st.get("callsign") or good.get("callsign"), "hybrid": True}, None, True)
            done = eng.drm_done_t >= eng.drm_t - 1 and got >= K
            P.set_cell("Total", "RX", str(K))
            P.set_cell("Segs OK", "RX", str(min(got, K)))
            P.set_cell("Position", "RX", f"{100 * min(got, K) // K} %")
            P.set_led("Image", LED_GREEN if done or got >= K else LED_AMBER)
            P.set_led("BSR", LED_AMBER if eng.drm_incomplete() else LED_OFF)
        return True

    def _update_panel(self):
        P = self.panel
        now = time.time()
        listening = self.rx_stream is not None
        db = self.rx_dbfs if listening else None
        P.set_bar("RX", db, -60, 0, "" if db is None else f"{db:.0f} dBFS")
        if db is None or db < -60:
            P.set_led("Signal", LED_OFF)
        else:
            P.set_led("Signal", LED_RED if db > -3 else LED_GREEN)
        eng = self.rx_engine
        if eng is None:
            return
        try:
            if self._update_panel_drm(eng, now, listening):
                return
        except Exception as e:
            self.log_exc("Panneau EasyPal", e)
        last = eng.last
        snr = last.get("snr")
        fresh = any(now - m.last_ok < 10 for m in eng.modems.values())
        P.set_bar("SNR", snr if fresh else None, -10, 20, "" if snr is None or not fresh else f"{snr:+.0f} dB")
        P.set_led("Sync", LED_GREEN if listening and any(m.sync for m in eng.modems.values()) else LED_OFF)
        lok = max(m.last_ok for m in eng.modems.values())
        lfail = max(m.last_fail for m in eng.modems.values())
        if now - max(lok, lfail) > 4:
            P.set_led("Trame", LED_OFF)
        else:
            P.set_led("Trame", LED_GREEN if lok >= lfail else LED_RED)
        # image la plus récente
        if eng.activity:
            iid, act = max(eng.activity.items(), key=lambda kv: kv[1]["t"])
            s = eng.rcv.sessions.get(iid)
            mode = act["mode"]
            P.set_cell("Mode", "RX", mode)
            P.set_cell("Bande kHz", "RX", f"{MODE_BW.get(mode, 0):.2f}")
            P.set_cell("Débit b/s", "RX", str(MODE_BPS.get(mode, "—")))
            if s:
                c = s["info"]["call"]
                if c and c != "?":
                    self._rx_call(c, act["t"])
                elif act["t"] >= self.__dict__.get("_pcall", (0.0,))[0] and now - act["t"] < 20:
                    # image en cours, indicatif pas encore reçu (il arrive en fin d'émission) :
                    # pas l'indicatif de la station précédente ; celle qui émet sur notre
                    # fréquence d'après les stations en ligne, sinon « — »
                    g = self._guess_tx_call()
                    self._rx_call(g, act["t"], guess=bool(g))
                prog = eng.rcv.progress(iid)
                if prog:
                    got, K = prog
                    done = iid in eng.rcv.done
                    P.set_cell("Total", "RX", str(K))
                    P.set_cell("Segs OK", "RX", str(K if done else got))
                    P.set_cell("Position", "RX", f"{100 * (K if done else got) // K} %")
                    P.set_led("Image", LED_GREEN if done else LED_AMBER)
                    inc = [r for r in eng.incomplete() if r[3] > 0 and r[4] > 2]
                    P.set_led("BSR", LED_AMBER if inc else LED_OFF)

    def _poll(self):
        # Une erreur dans une mise à jour ne doit jamais arrêter cette boucle : sinon
        # plus rien ne passe (waterfall, fin d'émission, boutons) et le programme
        # paraît figé.
        try:
            while True:
                try:
                    fn, a = self.uiq.get_nowait()
                except queue.Empty:
                    break
                try:
                    fn(*a)
                except Exception as e:
                    try:
                        self.log_exc(f"Interface ({getattr(fn, '__name__', fn)})", e)
                    except Exception:
                        pass
        finally:
            self.after(100, self._poll)

    API_ORDER = {"MME": 0, "Windows DirectSound": 1, "Windows WASAPI": 2}

    def _fill_devices(self):
        try:
            devs = sd().query_devices()
        except Exception as e:
            self.log(f"Audio indisponible : {e}")
            devs = []
        if not devs:
            self.cb_out["values"] = self.cb_in["values"] = []
            return
        # un seul choix par appareil réel (plus les doublons MME / DirectSound / WASAPI)
        try:
            outs = audio.unique_devices(sd(), output=True)
            ins = audio.unique_devices(sd(), output=False)
        except Exception as e:
            self.log(f"Audio : {e}")
            outs, ins = [], []
        self.cb_out["values"] = [f"{i}: {name} [{api}]" for i, name, api in outs]
        self.cb_in["values"] = [f"{i}: {name} [{api}]" for i, name, api in ins]

    @staticmethod
    def _dev_index(s, output=None):
        """Retrouve le périphérique par son nom et son API (les numéros changent
        quand on branche/débranche un appareil USB), sinon par son numéro.
        output : True (sortie) / False (entrée) / None. L'entrée et la sortie d'un même
        codec peuvent porter exactement le même nom (ex. « TS-890 (2- USB AUDIO CODEC) »
        renommé dans Windows) : on ne garde que les appareils du bon sens."""
        if not s:
            return None
        idx, _, label = s.partition(": ")
        try:
            hostapis = sd().query_hostapis()
            devs = sd().query_devices()
            key = None if output is None else ("max_output_channels" if output else "max_input_channels")

            def ok(i):
                return key is None or devs[i][key] > 0

            cands = [i for i, d in enumerate(devs)
                     if f"{d['name']} [{hostapis[d['hostapi']]['name']}]" == label and ok(i)]
            if not cands:
                # le nom affiché est le nom complet ; en MME Windows le tronque à 31 caractères
                name, _, api = label.rpartition(" [")
                api = api.rstrip("]")
                cands = [i for i, d in enumerate(devs)
                         if hostapis[d["hostapi"]]["name"] == api and audio._same_device(name, d["name"]) and ok(i)]
            if cands:
                # plusieurs appareils du même nom : celui du numéro enregistré s'il en fait partie
                return int(idx) if idx.isdigit() and int(idx) in cands else cands[0]
        except Exception:
            pass
        return int(idx)

    def _clean_days(self):
        try:
            return max(1, min(3650, int(self.v_clean_days.get())))
        except (tk.TclError, ValueError):
            return rxclean.DEFAULT_DAYS

    def _auto_clean(self):
        """Efface les sous-dossiers par jour plus anciens que le nombre de jours choisi."""
        self.after(6 * 3600 * 1000, self._auto_clean)
        if not self.v_clean.get():
            return
        folder, days = self.v_folder.get() or DEFAULT_OUT, self._clean_days()

        def run():
            try:
                n, freed = rxclean.clean(folder, days)
                if n:
                    self.ui(self.log, f"Nettoyage : {n} dossier(s) d'images de plus de {days} jours effacé(s) "
                                      f"({freed / 1e6:.1f} Mo libérés).")
            except Exception as e:
                self.ui(self.log_exc, "Nettoyage des anciennes images", e)

        threading.Thread(target=run, daemon=True).start()

    def _pick_folder(self):
        p = filedialog.askdirectory(initialdir=self.v_folder.get())
        if p:
            self.v_folder.set(p)

    def _hyb_cfg(self):
        return {"host": self.v_hhost.get().strip(), "port": int(self.v_hport.get() or 21),
                "user": self.v_huser.get().strip(), "password": self.v_hpass.get(),
                "dir": self.v_hdir.get().strip(), "tls": bool(self.v_htls.get()),
                "url": self.v_hurl.get().strip()}

    def save_conf(self, quiet=False):
        try:
            self.conf.update(
                callsign=self.mycall(), opname=self.myname(), mode=self.v_mode.get(),
                width=self.v_width.get(), seconds=int(self.v_sec.get()),
                fmt=self._fmt_mem["radio"] if self._fmt_side == "hyb" else self.v_fmt.get(),
                hyb_fmt=self.v_fmt.get() if self._fmt_side == "hyb" else self._fmt_mem["hyb"],
                overhead=self._robust_conf(), conf_v=64,
                out_dev=self.v_out.get(), in_dev=self.v_in.get(), level=int(self.v_lvl.get()),
                radio=self.radio_cfg,
                folder=self.v_folder.get(),
                hyb_on=bool(self.v_hyb.get()), hyb_flash=bool(self.v_flash.get()),
                rx_clean=bool(self.v_clean.get()), rx_clean_days=self._clean_days(),
                hyb_host=self.v_hhost.get().strip(),
                hyb_port=int(self.v_hport.get() or 21), hyb_user=self.v_huser.get().strip(),
                hyb_pass=hybrid.protect(self.v_hpass.get()), hyb_dir=self.v_hdir.get().strip(),
                hyb_tls=bool(self.v_htls.get()), hyb_url=self.v_hurl.get().strip(),
                hyb_auto=bool(self.v_hauto.get()), hyb_width=self.v_hwidth.get(),
                preview=bool(self.v_prev.get()), locator=self.v_loc.get().strip().upper(),
                bsr_auto=bool(self.v_bsr_auto.get()), fix_auto=bool(self.v_fix_auto.get()),
                ack_auto=bool(self.v_ack_auto.get()), listen_after=bool(self.v_listen_after.get()),
                follow_mode=bool(self.v_follow.get()), cwid=bool(self.v_cwid.get()), lang=i18n.get_lang(),
                wav_volume=int(self.v_wavvol.get()), wft_font=self.v_wftfont.get(),
                wft_neg=bool(self.v_wftneg.get()), wft_text=self.txt_wft.get("1.0", "end").strip(),
                hyb_kb=float(self.v_hkb.get()), gif_kb=float(self.v_gifkb.get()),
                net_on=bool(self.v_net.get()), net_host=self.v_nethost.get().strip() or presence.DEFAULT_HOST,
                net_port=int(self.v_netport.get() or presence.DEFAULT_PORT))
            for k in ("cat_on", "ptt", "cat_port", "cat_baud", "cat_cmd", "cat_freq"):
                self.conf.pop(k, None)              # anciens réglages : repris dans « radio »
            with open(CONF_PATH, "w", encoding="utf-8") as f:
                json.dump(self.conf, f, indent=1)
            private_file(CONF_PATH)
            if not quiet:
                self.log("Réglages enregistrés.")
            if getattr(self, "gal_store", None) is not None:
                self._gallery_open()
        except Exception as e:
            self.log(f"Impossible d'enregistrer les réglages : {e}")

    def _fix_public_url(self, base):
        old = self.v_hurl.get().strip()
        self.v_hurl.set(base)
        self.save_conf(quiet=True)
        self.log(f"Lien public corrigé automatiquement : {old} → {base} (le dossier FTP "
                 f"« {self.v_hdir.get()} » n'était pas dans le lien).")
        if isinstance(self.tx, HybridJob):
            self.prepare()

    @staticmethod
    def _keep_label(n):
        n = int(n or 0)
        return next((lab for lab, v in HYB_KEEP.items() if v == n), "Les 3 dernières")

    def _keep_changed(self):
        lab = self.v_hkeep.get()
        n = next((v for x, v in HYB_KEEP.items() if tr(x) == lab or x == lab), 3)
        self.conf["hyb_keep"] = n
        self._save_conf_file()
        self.log(tr("Mes images gardées sur le serveur") + f" : {lab}")

    @staticmethod
    def _rxmax_label(mb):
        mb = int(mb or 0)
        return "Sans limite" if mb <= 0 else (f"{mb // 1024} Go" if mb >= 1024 else f"{mb} Mo")

    def _rxmax_changed(self):
        lab = self.v_hrxmax.get()
        mb = next((0 if x == "Sans limite" else int(x.split()[0]) * (1024 if x.endswith("Go") else 1)
                   for x in HYB_RX_MAX if tr(x) == lab or x == lab), 200)
        self.conf["hyb_rx_max_mb"] = mb
        hybrid.set_max_download(mb)
        self._save_conf_file()
        self.log(tr("Fichiers hybrides reçus : taille max") + f" : {lab}")

    def test_hybrid(self):
        cfg = self._hyb_cfg()
        self.log(f"Test du serveur {cfg['host']}…")
        if not hybrid.has_public_url(cfg):
            return self._test_ftp_only(cfg)

        def run():
            try:
                url, base = hybrid.test_server(cfg)
                if base.rstrip("/") != cfg["url"].rstrip("/"):
                    self.ui(self._fix_public_url, base)
                self.ui(self.log, f"Serveur OK : dépôt FTP et lecture par {url} réussis.")
                self.ui(messagebox.showinfo, APP, "Serveur hybride OK :\ndépôt FTP et lecture "
                                                  "par le lien public réussis.")
            except Exception as e:
                self.ui(self.log_exc, "Test serveur hybride", e)
                self.ui(messagebox.showerror, APP, f"Test du serveur échoué :\n{e}")

        threading.Thread(target=run, daemon=True).start()

    def _test_ftp_only(self, cfg):
        """Lien public absent (ou « ftp.… » au lieu d'une adresse web) : on teste quand même le dépôt FTP,
        qui suffit pour l'hybride EasyPal, et on explique le lien public (nécessaire pour l'hybride HFImage)."""
        def run():
            try:
                hybrid.test_ftp(cfg)
            except Exception as e:
                self.ui(self.log_exc, "Test serveur hybride", e)
                self.ui(messagebox.showerror, APP, f"Test du serveur échoué :\n{e}")
                return
            self.ui(self._ftp_only_ok, cfg)
        threading.Thread(target=run, daemon=True).start()

    def _ftp_only_ok(self, cfg):
        self.log(f"Dépôt FTP réussi sur {cfg['host']}.")
        given = cfg.get("url", "").strip()
        sug = hybrid.suggest_public_url(cfg)
        msg = ("Dépôt FTP réussi : le serveur convient pour l'hybride EasyPal (mode EasyPal).\n\n"
               "Pour l'hybride HFImage, il faut aussi le lien public : l'adresse web (http:// ou https://) "
               "où l'on voit ce dossier dans un navigateur, pas l'adresse du serveur FTP.")
        if given:
            msg += "\n" + f"« {given} » n'est pas une adresse web."
        if sug and messagebox.askyesno(APP, msg + "\n\n" + "Lien public probable :" + f"\n{sug}\n\n" + "L'utiliser et refaire le test ?"):
            self.v_hurl.set(sug)
            self.save_conf(quiet=True)
            self.test_hybrid()
        elif not sug:
            messagebox.showinfo(APP, msg + "\n" + "Exemple : https://www.qsl.net/votreindicatif/easypal/")

    # -------------------------------------------------------------- émission
    def _remember_sent(self, tx):
        """Images envoyées gardées pour répondre aux BSR / FIX : les 32 dernières seulement
        (chacune garde son modem en mémoire ; programme ouvert des jours)."""
        self.sent_images[tx.image_id] = tx
        for k in list(self.sent_images)[:-32]:
            del self.sent_images[k]

    def _cmp_click(self, e):
        p0 = getattr(self, "_cmp_press", None)
        self._cmp_press = None
        if p0 is None or abs(e.x - p0[0]) > 4 or abs(e.y - p0[1]) > 4 or self.lb_cmp.zoom > 1.0:
            return                                    # glisser (image agrandie) : pas un clic
        if self.src_img is not None and getattr(self, "_cmp_edit_click", False):
            self._cmp_edit_click = False
            return                                    # clic sur un texte / logo (ou désélection) : pas d'ouverture
        if not self.tx_busy:
            self.open_image()

    # ------------------------------------------------------------- édition directe sur l'image TX (1.52)
    @staticmethod
    def _tr(s):
        return tr(s)

    def _edit_preview(self, size):
        """Aperçu rapide de l'image à émettre à la taille de l'écran (édition à la souris)."""
        c = getattr(self, "_edit_base", None)
        if not c or c[0] is not self.src_img or c[1] != size:
            self._edit_base = c = (self.src_img, size, self.src_img.convert("RGB").resize(size, Image.BILINEAR))
        im = c[2]
        if self.conf.get("pip_on") and self.pips:
            im = self._pip_compose(im)[0]
        im = self._tc_apply(im, cache=False)
        return bubbles.draw(im, self.bubbles)

    def _edit_ask_text(self, initial="", title=None, single=False):
        """Petite fenêtre de saisie du texte d'une bulle (avec les phrases toutes prêtes).
        -> texte, ou None si annulé."""
        w = tk.Toplevel(self)
        w.title(title or tr("Texte"))
        w.transient(self)
        f = ttk.Frame(w, padding=10)
        f.pack(fill="both", expand=True)
        res = [None]
        if single:
            v = tk.StringVar(value=initial)
            ent = ttk.Entry(f, textvariable=v, width=40)
            ent.pack(fill="x")
            ent.focus_set()
            get = lambda: v.get()
        else:
            top = ttk.Frame(f)
            top.pack(fill="x")
            ttk.Label(top, text=tr("Texte")).pack(side="left")
            txt = tk.Text(f, width=40, height=4, wrap="word", font=("TkDefaultFont", 10))
            mb = ttk.Menubutton(top, text=tr("Phrases") + " ▾")
            mb.pack(side="right")
            pm = tk.Menu(mb, tearoff=0)
            mb["menu"] = pm
            for p in self._bubble_phrases():
                lab = self._phrase_fill(p)
                pm.add_command(label=lab if len(lab) <= 50 else lab[:48] + "…",
                               command=lambda p=p: (txt.delete("1.0", "end"), txt.insert("1.0", self._phrase_fill(p))))
            txt.pack(fill="both", expand=True, pady=(4, 0))
            txt.insert("1.0", initial)
            txt.focus_set()
            get = lambda: txt.get("1.0", "end").rstrip("\n")
        b = ttk.Frame(f)
        b.pack(fill="x", pady=(8, 0))

        def ok(*_):
            res[0] = get()
            w.destroy()
        ttk.Button(b, text="OK", command=ok).pack(side="right")
        ttk.Button(b, text=tr("Annuler"), command=w.destroy).pack(side="right", padx=6)
        w.bind("<Escape>", lambda e: w.destroy())
        if single:
            w.bind("<Return>", ok)
        else:
            w.bind("<Control-Return>", ok)
        try:
            w.grab_set()
        except tk.TclError:
            pass
        self.wait_window(w)
        return res[0]

    def _edit_ask_file(self):
        types = " ".join("*" + e for e in self.PIP_LOCAL_TYPES)
        return filedialog.askopenfilename(parent=self, title=tr("Image à incruster"),
                                          filetypes=[(tr("Images"), types), (tr("Tous les fichiers"), "*.*")])

    def _edit_info(self, msg):
        messagebox.showinfo(APP, msg)

    def _edit_error(self, msg):
        messagebox.showerror(APP, msg)

    IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".avif", ".svg", ".svgz", ".tif", ".tiff",
                  ".jp2", ".j2k")

    def _dropped(self, paths):
        """Fichiers glissés depuis l'Explorateur : une image s'ouvre dans l'onglet TX ;
        un autre fichier est proposé à l'envoi (par radio, ou en hybride sans limite)."""
        paths = [p for p in paths if os.path.isfile(p)]
        if not paths:
            return
        p = paths[0]
        if p.lower().endswith(self.IMAGE_EXTS):
            self.show_tab("tx")
            self.load_image(p)
        elif messagebox.askyesno(APP, tr("Envoyer ce fichier ?") + f"\n{os.path.basename(p)}"):
            self.send_file(p)

    def open_image(self):
        p = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.svg *.svgz *.bmp *.gif *.webp *.avif *.tif *.tiff"),
                                                  ("JPEG", "*.jpg *.jpeg"), ("SVG", "*.svg *.svgz"),
                                                  ("Tous", "*.*")])
        if not p:
            return
        self.load_image(p)

    def load_image(self, p):
        try:
            notes = []
            self.src_img, self.src_raw, self.src_kind = imgfmt.load_source(p, notes)
            if notes:
                self.log(tr("Photo remise dans le bon sens (indication du téléphone)."))
            self.bubbles = []                 # les bulles étaient placées pour l'image précédente
            self.src_path = p                 # nom repris pour les fichiers EasyPal (« de_…-photo.jpg »)
        except Exception as e:
            messagebox.showerror(APP, f"Image illisible : {e}")
            return
        self.tx = None
        self.src_anim = None
        if self.src_kind == "gif" and imgfmt.is_animated_gif(self.src_raw):
            n, secs = imgfmt.gif_info(self.src_raw)
            self.src_anim = imgfmt.gif_frames(self.src_raw)
            if self.v_hyb.get():
                self.v_fmt.set("original")
                self.log(f"GIF animé ({n} images, {secs:.1f} s) : envoyé tel quel en hybride.")
            else:
                self.log(f"GIF animé ({n} images, {secs:.1f} s) : l'animation part en mode hybride "
                         f"(cochez « Mode hybride »). En radio seule, la première image est envoyée.")
        self._show(self.lb_src, "src", self.src_img)
        self._set_text(self.lb_src_info, f"{os.path.basename(p)} — {imgfmt.describe(self.src_kind)} — "
                                         f"{self.src_img.width}×{self.src_img.height} — {len(self.src_raw) / 1000:.1f} K")
        if self.src_kind == "svg" and self.v_fmt.get() != "original":
            # un dessin vectoriel est bien plus petit envoyé tel quel (texte compressé)
            self.v_fmt.set("original")
            self.log(f"SVG : envoi du dessin tel quel (format « original », {len(imgfmt.svg_pack(self.src_raw))} octets compressés).")
        elif (not self.v_hyb.get() and self.v_fmt.get() == "original" and self.src_kind != "svg"
              and len(self.src_raw) > 30000):
            # « original » resté d'un SVG : une photo de cette taille demanderait trop longtemps en radio
            self.v_fmt.set("avif")
            self.log(f"Photo de {len(self.src_raw) / 1000:.0f} K : format avif pour la radio "
                     "(« original » reste possible en mode hybride).")
        self.prepare()

    def _rotate_tx(self, deg):
        """Tourne l'image à émettre d'un quart de tour (deg = 90 : à gauche, -90 : à droite)."""
        if self.src_img is None or self.tx_busy:
            return
        if self.src_kind == "svg" or self.src_anim is not None:
            self.log(tr("Les dessins SVG et les GIF animés ne peuvent pas être tournés ici."))
            return
        self.src_img = self.src_img.rotate(deg, expand=True)
        self.src_raw, self.src_kind = imgfmt.reencode(self.src_img, self.src_kind)
        self.bubbles = []                     # placées pour l'ancienne orientation
        self.tx = None
        self._show(self.lb_src, "src", self.src_img)
        name = os.path.basename(getattr(self, "src_path", "") or "")
        self._set_text(self.lb_src_info, f"{name} — {imgfmt.describe(self.src_kind)} — "
                                         f"{self.src_img.width}×{self.src_img.height} — {len(self.src_raw) / 1000:.1f} K")
        self.prepare()

    def _payload(self, fmt, hybrid=False):
        """Mode « original » : octets du fichier tel quel -> (données, format radio)."""
        data = imgfmt.original_payload(self.src_raw, self.src_kind, hybrid)
        return data, protocol.detect_format(data)

    def _fmt(self):
        """Format choisi -> nom interne (« jpg » = JPEG)."""
        f = self.v_fmt.get()
        return {"jpg": "jpeg"}.get(f, f)

    def _mode_changed(self, _e=None):
        self._drm_hyb_mode()
        self.v_sec.set(MODE_SEC.get(self.v_mode.get(), 120))
        self._drm_ui_update()
        self.prepare()

    def _drm_ui_update(self):
        """Mode EasyPal : affiche ses réglages, la robustesse (code fontaine) est sans objet."""
        drm = self.v_mode.get() == engine.DRM_MODE
        shown = bool(self.drm_row.winfo_manager())     # (onglet Émission caché : pas « mapped »)
        if drm and not shown:
            self.drm_row.pack(fill="x", pady=(4, 0))
        elif not drm and shown:
            self.drm_row.pack_forget()
        if not self.v_hyb.get():
            self._robust_widget.configure(state="disabled" if drm else "readonly")

    def _drm_changed(self):
        for k, v in self.v_drm.items():
            self.conf[k] = v.get()
        self._save_conf_file()
        self.prepare()

    def _drm_params(self):
        v = self.v_drm
        return hamdrm.make_params(self.mycall() or "NOCALL",
                                  mode=DRM_MODES.index(v["drm_mode"].get()),
                                  bandwidth=DRM_BWS.index(v["drm_bw"].get()),
                                  qam=DRM_QAMS.index(v["drm_qam"].get()),
                                  protection=DRM_PROTS.index(v["drm_prot"].get()),
                                  rs=DRM_RSS.index(v["drm_rs"].get()))

    def _tx_source(self):
        """Image à émettre : l'image ouverte, + images des correspondants, + « mes conditions
        de trafic », + bulles de texte, selon les réglages."""
        im = self._tx_source_nobubbles()
        if im is None or not any((b.get("text") or "").strip() for b in self.bubbles):
            return im
        key = (id(im), json.dumps(self.bubbles, sort_keys=True))
        c = getattr(self, "_bub_cache", None)
        if c and c[0] == key:
            return c[1]
        out = bubbles.draw(im, self.bubbles)
        self._bub_cache = (key, out)
        return out

    def _tx_source_nobubbles(self):
        return self._tc_apply(self._pip_source())

    def _tc_apply(self, base, cache=True):
        """Bandeau « Mes conditions de trafic » sur l'image (si coché). cache=False : aperçu
        d'édition (image réduite, refaite à chaque mouvement)."""
        if base is None or not self.conf.get("tc_on"):
            return base
        freq = audio.format_freq(self.rig_freq, True) if self.rig_freq else ""
        model = getattr(self.rig, "model", "") if self.rig is not None else ""
        items = trafic.parts(self.conf, self.mycall(), self.v_loc.get().strip().upper(),
                             model or "", freq)
        style = {k: self.conf[k] for k in ("tc_font", "tc_bold", "tc_italic", "tc_color", "tc_stroke", "tc_bg",
                                           "tc_alpha", "tc_callcolor", "tc_frame") if k in self.conf}
        call = self.mycall()
        key = (id(base), tuple(i for i in items if not re.match(r"\d{4}-\d\d-\d\d \d\d:\d\d", i)),
               self.conf.get("tc_pos"), self.conf.get("tc_size"), tuple(sorted(style.items())))
        c = getattr(self, "_tc_cache", None)
        if cache and c and c[0] == key and c[2] is base:
            return c[1]
        im = trafic.overlay(base, items, self.conf.get("tc_pos", "bas"), self.conf.get("tc_size", "normale"),
                            style, call)
        if cache:
            self._tc_cache = (key, im, base)
        return im

    # ------------------------------------------------------------- images des correspondants
    # Jusqu'à PIP_MAX_N images reçues incrustées dans l'image émise, chacune avec sa
    # position et sa taille. self.pips = [{path, call, snr, corner, size, pos, scale}, …].
    # La disposition de chaque emplacement est gardée dans les réglages : l'emplacement 1
    # garde les anciennes clés (pip_corner, pip_size, pip_pos, pip_scale), les suivants
    # sont dans « pip_more ».
    PIP_MAX_N = 4
    PIP_CORNERS = ("haut-droite", "haut-gauche", "bas-droite", "bas-gauche")

    def _pip_caption(self, p):
        """Légende sous l'incrustation : celle écrite par l'utilisateur, sinon « de F4EMK — +12 dB »
        pour une image reçue, rien pour une image prise sur le PC."""
        if p.get("cap"):
            return str(p["cap"])
        if p.get("local"):
            return ""
        rep = p.get("snr")
        cap = tr("de") + f" {p.get('call') or '?'}"
        if rep is not None and self.conf.get("pip_report", True):
            cap += f"  —  {rep:+.0f} dB"
        return cap

    def _pip_slot_layout(self, i):
        """Disposition gardée pour l'emplacement i (0 = premier)."""
        if i == 0:
            return {"corner": self.conf.get("pip_corner", "haut-droite"), "size": self.conf.get("pip_size", "moyenne"),
                    "pos": self.conf.get("pip_pos"), "scale": self.conf.get("pip_scale"),
                    "rot": self.conf.get("pip_rot", 0), "tilt": self.conf.get("pip_tilt", 0),
                    "shape": self.conf.get("pip_shape", "rect")}
        more = self.conf.get("pip_more") or []
        if i - 1 < len(more) and isinstance(more[i - 1], dict):
            d = more[i - 1]
            return {"corner": d.get("corner", "haut-gauche"), "size": d.get("size", "petite"),
                    "pos": d.get("pos"), "scale": d.get("scale"), "rot": d.get("rot", 0), "tilt": d.get("tilt", 0),
                    "shape": d.get("shape", "rect")}
        used = {p.get("corner") for p in getattr(self, "pips", [])[:i] if not p.get("pos")}
        corner = next((c for c in self.PIP_CORNERS if c not in used), self.PIP_CORNERS[i % 4])
        return {"corner": corner, "size": "petite", "pos": None, "scale": None, "rot": 0, "tilt": 0, "shape": "rect"}

    def _pip_save_layouts(self):
        """Garde la disposition de chaque image incrustée (dans l'ordre de la liste)."""
        for i, p in enumerate(self.pips):
            lay = {k: p.get(k) for k in ("corner", "size", "pos", "scale", "rot", "tilt", "shape")}
            if i == 0:
                self.conf.update(pip_corner=lay["corner"], pip_size=lay["size"], pip_pos=lay["pos"],
                                 pip_scale=lay["scale"], pip_rot=lay["rot"] or 0, pip_tilt=lay["tilt"] or 0,
                                 pip_shape=lay["shape"] or "rect")
            else:
                more = list(self.conf.get("pip_more") or [])
                while len(more) < i:
                    more.append({})
                more[i - 1] = lay
                self.conf["pip_more"] = more[:self.PIP_MAX_N - 1]
        # emplacements libérés (image retirée) : une prochaine image prendra un coin libre
        self.conf["pip_more"] = (self.conf.get("pip_more") or [])[:max(0, len(self.pips) - 1)]

    def _pip_new(self, cand, i=None):
        """Nouvelle incrustation à partir d'une image reçue {path, call, snr}."""
        i = len(self.pips) if i is None else i
        return dict(cand, **self._pip_slot_layout(i))

    def _pip_thumb(self, path):
        cache = self.__dict__.setdefault("_pip_thumbs", {})
        if path not in cache:
            t = imgfmt.open_upright(path)            # photo de téléphone « couchée » : remise droite
            try:
                t.seek(0)
            except (AttributeError, EOFError):
                pass
            t = t.convert("RGBA" if trafic.has_alpha(t) else "RGB")    # logo PNG : transparence gardée
            t.thumbnail((1600, 1600))                # grande photo du PC : assez pour une incrustation
            cache[path] = t
            for k in [k for k in cache if k not in {p["path"] for p in self.pips} | {path}]:
                del cache[k]
        return cache[path]

    def _pip_compose(self, base):
        """base + les images incrustées -> (image, [rectangle (x, y, W, H) ou None par incrustation])."""
        im, rects = base, []
        for p in self.pips:
            try:
                th = self._pip_thumb(p["path"])
                cap = self._pip_caption(p)
                logo = bool(p.get("logo"))
                shape = p.get("shape") or "rect"
                rects.append(trafic.pip_layout(im.size, th.size, "" if logo else cap, p.get("corner", "haut-droite"),
                                               p.get("size", "moyenne"), p.get("pos"), p.get("scale"), logo,
                                               shape)[:4])
                im = trafic.pip(im, th, cap, p.get("corner", "haut-droite"), p.get("size", "moyenne"),
                                p.get("pos"), p.get("scale"), p.get("rot") or 0, p.get("tilt") or 0,
                                logo, p.get("opa", 1.0), shape)
            except Exception as e:
                self.log(f"Image du correspondant illisible : {e}")
                rects.append(None)
        return im, rects

    def _pip_source(self):
        """Image ouverte, avec les images des correspondants incrustées si la case est cochée."""
        if self.src_img is None or not self.conf.get("pip_on") or not self.pips:
            return self.src_img
        key = (id(self.src_img), self.conf.get("pip_report", True),
               tuple((p["path"], self._pip_caption(p), p.get("corner"), p.get("size"), tuple(p.get("pos") or ()),
                      p.get("scale"), p.get("rot") or 0, p.get("tilt") or 0, bool(p.get("logo")),
                      p.get("opa", 1.0), p.get("shape") or "rect") for p in self.pips))
        c = getattr(self, "_pip_cache", None)
        if c and c[0] == key:
            return c[1]
        im = self._pip_compose(self.src_img)[0]
        self._pip_cache = (key, im)
        return im

    def _pip_candidates(self):
        """Dernières images reçues : [(libellé, {path, call, snr})]."""
        out = []
        for e in (self.gal_store.latest("rx", 30) if self.gal_store else []):
            src = e.get("png") or e.get("file")
            if not src or not os.path.exists(src):
                continue
            call = e.get("call") or "?"
            snr = e.get("snr")
            if snr is None and call in self.heard:
                snr = self.heard[call].get("snr")
            lab = f"{call}  {time.strftime('%d/%m %H:%M', time.localtime(e.get('t', 0)))}  {e.get('mode', '')}"
            out.append((lab, {"path": src, "call": call, "snr": snr, "local": False}))
        # images prises sur le PC (bouton « Image du PC… ») : gardées pour être réutilisées
        for p in self.conf.get("pip_local") or []:
            if isinstance(p, str) and os.path.exists(p):
                out.append((self._pip_local_label(p), {"path": p, "call": "", "snr": None, "local": True}))
        return out

    @staticmethod
    def _pip_local_label(path):
        return "📁 " + os.path.basename(path)

    PIP_LOCAL_TYPES = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".avif", ".tif", ".tiff")

    def _pip_remember_local(self, path):
        """Image du PC choisie : en tête de la liste des images du PC (10 au plus)."""
        lst = [p for p in (self.conf.get("pip_local") or []) if isinstance(p, str) and p != path]
        self.conf["pip_local"] = [path] + lst[:9]

    def set_pip(self, entry, add=False):
        """Galerie → « Répondre avec cette image » (elle remplace les incrustations) ou
        « Ajouter cette image à mon image TX » (elle s'ajoute, 4 au maximum)."""
        src = entry.get("png") or entry.get("file")
        call = entry.get("call") or "?"
        snr = entry.get("snr")
        if snr is None and call in self.heard:
            snr = self.heard[call].get("snr")
        cand = {"path": src, "call": call, "snr": snr}
        if add and any(p["path"] == src for p in self.pips):
            pass                                            # déjà incrustée
        elif add and len(self.pips) >= self.PIP_MAX_N:
            messagebox.showinfo(APP, tr("4 images au maximum dans l'image TX. Retirez-en une dans "
                                        "« Image du correspondant… »."))
            return
        elif add:
            self.pips.append(self._pip_new(cand))
        else:
            self.pips = [self._pip_new(cand, 0)]
        self.conf["pip_on"] = True
        if hasattr(self, "v_pipon"):
            self.v_pipon.set(True)
        self._save_conf_file()
        self.show_tab("tx")
        if self.src_img is None:
            messagebox.showinfo(APP, "Ouvrez maintenant votre image : celle du correspondant y sera incrustée.")
        self.prepare()

    # ------------------------------------------------------------- bulles de texte (BD)
    def bubble_dialog(self):
        """Bulles de texte façon BD sur l'image émise : texte, style, taille, couleurs ;
        la bulle se déplace à la souris, sa pointe aussi (petit rond rouge)."""
        w = getattr(self, "_bub_win", None)
        if w is not None and w.winfo_exists():
            w.lift()
            return
        if self.src_img is None:
            messagebox.showinfo(APP, "Ouvrez d'abord une image (onglet TX).")
            return
        w = self._bub_win = tk.Toplevel(self)
        w.title(tr("Bulles de texte"))
        w.transient(self)
        f = ttk.Frame(w, padding=10)
        f.pack(fill="both", expand=True)
        styles = {"parole": tr("Parole"), "pensée": tr("Pensée"), "cri": tr("Cri"), "cartouche": tr("Cartouche"),
                  "texte": tr("Texte seul (sans bulle)")}
        sizes = {"petite": tr("Petite"), "moyenne": tr("Moyenne"), "grande": tr("Grande")}
        sel = [len(self.bubbles) - 1 if self.bubbles else None]
        geo = {}
        busy = [False]

        left = ttk.Frame(f)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        ttk.Label(left, text="Bulles").pack(anchor="w")
        lb = tk.Listbox(left, height=5, width=30, exportselection=False)
        lb.pack(fill="x")
        bb = ttk.Frame(left)
        bb.pack(fill="x", pady=(4, 8))
        tf = ttk.Frame(left)
        tf.pack(fill="x")
        ttk.Label(tf, text="Texte").pack(side="left")
        # phrases toutes prêtes (demande de M7WUV) : un clic les met dans la bulle
        mb = ttk.Menubutton(tf, text=tr("Phrases") + " ▾")
        mb.pack(side="right")
        pmenu = tk.Menu(mb, tearoff=0)
        mb["menu"] = pmenu
        txt = tk.Text(left, width=30, height=4, wrap="word", font=("TkDefaultFont", 10))
        txt.pack(fill="x")

        def use_phrase(p):
            if cur() is None:
                add()
            txt.delete("1.0", "end")
            txt.insert("1.0", self._phrase_fill(p))
            txt.focus_set()

        def save_phrase():
            t = txt.get("1.0", "end").strip()
            if not t:
                return
            lst = self._bubble_phrases()
            if t not in lst:
                self.conf["bub_phrases"] = lst + [t]
                self._save_conf_file()
                self.log(tr("Phrase enregistrée pour les bulles :") + f" {t}")

        def fill_menu():
            pmenu.delete(0, "end")
            for p in self._bubble_phrases():
                label = self._phrase_fill(p).replace("\n", " ")
                pmenu.add_command(label=label if len(label) <= 50 else label[:48] + "…",
                                  command=lambda p=p: use_phrase(p))
            pmenu.add_separator()
            pmenu.add_command(label=tr("Enregistrer cette phrase"), command=save_phrase)
            pmenu.add_command(label=tr("Modifier la liste…"), command=lambda: self._phrases_edit(w))
        pmenu.configure(postcommand=fill_menu)
        # émoticônes : un clic l'ajoute dans le texte, à l'endroit du curseur
        emo = tk.Frame(left)
        emo.pack(anchor="w", pady=(4, 0))
        geo["emo"] = []
        for k, ch in enumerate(bubbles.EMOJI):
            im = bubbles.emoji_image(ch, 22)
            if im is None:
                continue
            ph = ImageTk.PhotoImage(im)
            geo["emo"].append(ph)
            btn = tk.Button(emo, image=ph, relief="flat", bd=0, padx=1, pady=1, cursor="hand2",
                            command=lambda c=ch: (txt.insert("insert", (" " if txt.get("insert-1c", "insert")
                                                                        not in ("", " ", "\n") else "") + c),
                                                  txt.focus_set()))
            btn._no_theme = True
            btn.grid(row=k // 10, column=k % 10)
        v_anim = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="Émoticônes animées (mode hybride : GIF animé)", variable=v_anim,
                        command=lambda: changed()).pack(anchor="w", pady=(4, 0))
        ttk.Label(left, text="Style").pack(anchor="w", pady=(6, 0))
        v_style = tk.StringVar()
        ttk.Combobox(left, textvariable=v_style, values=list(styles.values()), state="readonly",
                     width=16).pack(anchor="w")
        ttk.Label(left, text="Taille du texte").pack(anchor="w", pady=(6, 0))
        v_size = tk.StringVar()
        ttk.Combobox(left, textvariable=v_size, values=list(sizes.values()), state="readonly",
                     width=16).pack(anchor="w")
        cf = ttk.Frame(left)
        cf.pack(anchor="w", pady=(8, 0))
        sw_bg = tk.Label(cf, width=3, relief="solid", bd=1)
        sw_fg = tk.Label(cf, width=3, relief="solid", bd=1)
        sw_bg._no_theme = sw_fg._no_theme = True
        ttk.Label(left, text="Glissez la bulle à la souris ; le rond rouge est la pointe.",
                  wraplength=190, foreground="#555", justify="left").pack(anchor="w", pady=(10, 0))

        cv = tk.Canvas(f, width=640, height=480, bg="#222", highlightthickness=0)
        cv.grid(row=0, column=1)

        def cur():
            i = sel[0]
            return self.bubbles[i] if i is not None and 0 <= i < len(self.bubbles) else None

        def base_small():
            im = self._tx_source_nobubbles() or self.src_img
            k = min(640 / im.width, 480 / im.height)
            size = (max(1, int(im.width * k)), max(1, int(im.height * k)))
            if geo.get("src") is not im or geo.get("size") != size:
                geo.update(src=im, size=size, small=im.resize(size, Image.LANCZOS),
                           off=((640 - size[0]) // 2, (480 - size[1]) // 2))
            return geo["small"]

        def preview():
            small = base_small()
            t = geo.get("t") if bubbles.has_anim(self.bubbles) else None
            pic = bubbles.draw(small, self.bubbles, t)
            geo["ph"] = ImageTk.PhotoImage(pic)
            cv.delete("all")
            ox, oy = geo["off"]
            cv.create_image(ox, oy, image=geo["ph"], anchor="nw")
            b = cur()
            if b is not None and (b.get("text") or "").strip():
                W, H = geo["size"]
                g = bubbles.layout(W, H, b)
                x0, y0, x1, y1 = g["box"]
                cv.create_rectangle(ox + x0, oy + y0, ox + x1, oy + y1, outline="#ffd400", dash=(4, 3))
                if b.get("style") not in bubbles.NO_TAIL:
                    tx, ty = ox + b["tx"] * W, oy + b["ty"] * H
                    cv.create_oval(tx - 6, ty - 6, tx + 6, ty + 6, fill="#e02020", outline="white")

        def refresh_list():
            lb.delete(0, "end")
            for b in self.bubbles:
                t = " ".join((b.get("text") or "").split()) or tr("(vide)")
                lb.insert("end", t if len(t) <= 30 else t[:28] + "…")
            if sel[0] is not None and sel[0] < len(self.bubbles):
                lb.selection_clear(0, "end")
                lb.selection_set(sel[0])

        def load_fields():
            b = cur()
            busy[0] = True
            txt.delete("1.0", "end")
            if b is not None:
                txt.insert("1.0", b.get("text", ""))
                v_style.set(styles.get(b.get("style"), styles["parole"]))
                v_size.set(sizes.get(b.get("size"), sizes["moyenne"]))
                sw_bg.configure(bg=b.get("bg", "#ffffff"))
                sw_fg.configure(bg=b.get("fg", "#000000"))
                v_anim.set(bool(b.get("anim")))
            busy[0] = False

        def changed(*_):
            if busy[0]:
                return
            b = cur()
            if b is None:
                return
            b["text"] = txt.get("1.0", "end").rstrip("\n")
            old_style = b.get("style")
            b["style"] = next((k for k, v in styles.items() if v == v_style.get()), "parole")
            if b["style"] == "texte" and old_style != "texte" and b.get("bg", "#ffffff").lower() == "#ffffff" \
                    and b.get("fg", "#000000").lower() == "#000000":
                b["fg"], b["bg"] = "#ffffff", "#000000"     # texte seul : blanc bordé de noir, lisible partout
                sw_bg.configure(bg=b["bg"])
                sw_fg.configure(bg=b["fg"])
            b["size"] = next((k for k, v in sizes.items() if v == v_size.get()), "moyenne")
            was = bool(b.get("anim"))
            b["anim"] = bool(v_anim.get())
            if b["anim"] and not was and not self.v_hyb.get():
                self.log(tr("Émoticônes animées : elles bougent en mode hybride (GIF animé) ; "
                            "en radio seule, elles restent fixes."))
            refresh_list()
            preview()

        def add():
            n = len(self.bubbles)
            b = bubbles.new(tr("73 de") + f" {self.mycall() or 'F4GOP'} !",
                            cy=0.2 + 0.18 * (n % 4), cx=0.3 + 0.2 * (n % 2))
            last = cur() or self.conf.get("bub_last") or {}
            # même style que la précédente (retenu aussi d'une image et d'une séance à l'autre)
            b.update({k: last[k] for k in ("style", "size", "bg", "fg", "anim") if k in last})
            self.bubbles.append(b)
            sel[0] = len(self.bubbles) - 1
            refresh_list()
            load_fields()
            preview()
            txt.focus_set()
            txt.tag_add("sel", "1.0", "end")

        def remove():
            if cur() is None:
                return
            del self.bubbles[sel[0]]
            sel[0] = (len(self.bubbles) - 1) if self.bubbles else None
            refresh_list()
            load_fields()
            preview()

        def pick(which):
            from tkinter import colorchooser
            b = cur()
            if b is None:
                return
            c = colorchooser.askcolor(color=b.get(which), parent=w)[1]
            if c:
                b[which] = c
                load_fields()
                preview()

        ttk.Button(bb, text="Ajouter", command=add).pack(side="left")
        ttk.Button(bb, text="Supprimer", command=remove).pack(side="left", padx=4)
        ttk.Label(cf, text="Fond").pack(side="left")
        sw_bg.pack(side="left", padx=(4, 12))
        ttk.Label(cf, text="Texte").pack(side="left")
        sw_fg.pack(side="left", padx=4)
        sw_bg.bind("<Button-1>", lambda e: pick("bg"))
        sw_fg.bind("<Button-1>", lambda e: pick("fg"))

        def to_frac(e):
            ox, oy = geo["off"]
            W, H = geo["size"]
            return min(1.0, max(0.0, (e.x - ox) / W)), min(1.0, max(0.0, (e.y - oy) / H))

        def press(e):
            if "size" not in geo:
                return
            ox, oy = geo["off"]
            W, H = geo["size"]
            h = bubbles.hit(W, H, self.bubbles, e.x - ox, e.y - oy, grab=10)
            if h is None:
                geo.pop("grab", None)
                return
            sel[0], part = h
            refresh_list()
            load_fields()
            b = cur()
            fx, fy = to_frac(e)
            geo["grab"] = (part, fx - (b["tx"] if part == "pointe" else b["cx"]),
                           fy - (b["ty"] if part == "pointe" else b["cy"]))
            preview()

        def drag(e):
            g = geo.get("grab")
            b = cur()
            if not g or b is None:
                return
            fx, fy = to_frac(e)
            if g[0] == "pointe":
                b["tx"], b["ty"] = fx - g[1], fy - g[2]
            else:
                nx, ny = fx - g[1], fy - g[2]
                b["tx"] += nx - b["cx"]                   # la pointe suit la bulle
                b["ty"] += ny - b["cy"]
                b["cx"], b["cy"] = nx, ny
            preview()

        def right(e):
            ox, oy = geo.get("off", (0, 0))
            W, H = geo.get("size", (1, 1))
            h = bubbles.hit(W, H, self.bubbles, e.x - ox, e.y - oy)
            if h is not None:
                sel[0] = h[0]
                remove()

        cv.bind("<ButtonPress-1>", press)
        cv.bind("<B1-Motion>", drag)
        cv.bind("<ButtonRelease-1>", lambda e: geo.pop("grab", None))
        cv.bind("<Button-3>", right)
        lb.bind("<<ListboxSelect>>", lambda e: (sel.__setitem__(0, lb.curselection()[0]) if lb.curselection()
                                                else None, load_fields(), preview()))
        txt.bind("<<Modified>>", lambda e: (txt.edit_modified(False), changed()))
        v_style.trace_add("write", changed)
        v_size.trace_add("write", changed)

        def close():
            self.bubbles[:] = [b for b in self.bubbles if (b.get("text") or "").strip()]
            if self.bubbles:                              # style retenu pour les prochaines bulles
                last = self.bubbles[-1]
                self.conf["bub_last"] = {k: last[k] for k in ("style", "size", "bg", "fg", "anim") if k in last}
                self._save_conf_file()
            w.destroy()
            self.prepare()

        bot = ttk.Frame(f)
        bot.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(bot, text="Tout effacer", command=lambda: (self.bubbles.clear(), sel.__setitem__(0, None),
                                                              refresh_list(), load_fields(), preview())
                   ).pack(side="left")
        ttk.Button(bot, text="OK", command=close).pack(side="right")
        w.protocol("WM_DELETE_WINDOW", close)
        if not self.bubbles:
            add()
        else:
            refresh_list()
            load_fields()
            preview()
        self._translate_ui(w)

        def tick(k=0):
            """Aperçu : les émoticônes des bulles animées bougent (pas de glisser en cours)."""
            if not w.winfo_exists():
                return
            if bubbles.has_anim(self.bubbles) and not geo.get("grab"):
                geo["t"] = (k % bubbles.ANIM_FRAMES) / bubbles.ANIM_FRAMES
                preview()
            w.after(bubbles.ANIM_MS, tick, k + 1)
        tick()

    def pip_dialog(self):
        w = getattr(self, "_pip_win", None)
        if w is not None and w.winfo_exists():
            w.lift()
            return
        w = self._pip_win = tk.Toplevel(self)
        w.title("Image du correspondant")
        w.transient(self)
        w.resizable(False, False)
        f = ttk.Frame(w, padding=12)
        f.pack(fill="both", expand=True)
        cands = self._pip_candidates()
        # les images déjà incrustées restent proposées même si elles ont quitté la galerie
        known = {p["path"] for _, p in cands}
        for p in self.pips:
            if p["path"] not in known and os.path.exists(p["path"]):
                lab = (self._pip_local_label(p["path"]) if p.get("local")
                       else f"{p.get('call') or '?'}  ({os.path.basename(p['path'])})")
                cands.append((lab, dict({k: p.get(k) for k in ("path", "call", "snr")}, local=bool(p.get("local")))))
        labels = [c[0] for c in cands]
        if not self.pips and cands:
            self.pips = [self._pip_new(cands[0][1], 0)]
        corners = {"haut-droite": tr("En haut à droite"), "haut-gauche": tr("En haut à gauche"),
                   "bas-droite": tr("En bas à droite"), "bas-gauche": tr("En bas à gauche"),
                   "libre": tr("Libre (à la souris)")}
        sizes = {"petite": tr("Petite"), "moyenne": tr("Moyenne"), "grande": tr("Grande"),
                 "libre": tr("Libre (molette)")}
        v_img, v_c, v_s = tk.StringVar(), tk.StringVar(), tk.StringVar()
        v_rep = tk.BooleanVar(value=bool(self.conf.get("pip_report", True)))
        v_on = tk.BooleanVar(value=bool(self.conf.get("pip_on")))
        sel = [0]                      # incrustation choisie (réglée par les listes et la souris)
        busy = [False]                 # pas de recalcul pendant qu'on change nous-mêmes les listes
        geo = {}                       # aperçu : échelle, décalage, taille de l'image, places des incrustations

        ttk.Checkbutton(f, text="Incruster les images des correspondants dans mon image", variable=v_on).grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(f, text="Images incrustées").grid(row=1, column=0, sticky="nw", pady=2)
        lf = ttk.Frame(f)
        lf.grid(row=1, column=1, sticky="w", padx=6, pady=2)
        lb = tk.Listbox(lf, height=self.PIP_MAX_N, width=36, exportselection=False, activestyle="none")
        lb.pack(side="left")
        bf = ttk.Frame(lf)
        bf.pack(side="left", padx=(6, 0), anchor="n")
        b_add = ttk.Button(bf, text="Ajouter une image", command=lambda: add())
        b_add.pack(fill="x")
        b_del = ttk.Button(bf, text="Retirer", command=lambda: remove())
        b_del.pack(fill="x", pady=(4, 0))
        b_pc = ttk.Button(bf, text="Image du PC…", command=lambda: add_pc())
        b_pc.pack(fill="x", pady=(4, 0))
        ttk.Label(f, text="Image reçue").grid(row=2, column=0, sticky="w", pady=2)
        cb_img = ttk.Combobox(f, textvariable=v_img, values=labels, width=34, state="readonly")
        cb_img.grid(row=2, column=1, sticky="w", padx=6)
        ttk.Label(f, text="Position").grid(row=3, column=0, sticky="w", pady=2)
        cb_c = ttk.Combobox(f, textvariable=v_c, values=list(corners.values()), width=20, state="readonly")
        cb_c.grid(row=3, column=1, sticky="w", padx=6)
        ttk.Label(f, text="Taille").grid(row=4, column=0, sticky="w", pady=2)
        sz_f = ttk.Frame(f)
        sz_f.grid(row=4, column=1, sticky="w", padx=6)
        cb_s = ttk.Combobox(sz_f, textvariable=v_s, values=list(sizes.values()), width=18, state="readonly")
        cb_s.pack(side="left")
        shapes = {"rect": tr("Rectangle"), "arrondi": tr("Coins arrondis"), "rond": tr("Rond"), "ovale": tr("Ovale")}
        v_shape = tk.StringVar(value=shapes["rect"])
        ttk.Label(sz_f, text="Forme").pack(side="left", padx=(12, 4))
        cb_shape = ttk.Combobox(sz_f, textvariable=v_shape, values=list(shapes.values()), width=14, state="readonly")
        cb_shape.pack(side="left")
        ttk.Checkbutton(f, text="Afficher le report (dB)", variable=v_rep).grid(row=5, column=1, sticky="w", padx=6)
        # légende libre (vide : « de F4EMK — +12 dB » pour une image reçue, rien pour une image du PC)
        v_cap = tk.StringVar()
        ttk.Label(f, text="Légende").grid(row=6, column=0, sticky="w", pady=2)
        cf_ = ttk.Frame(f)
        cf_.grid(row=6, column=1, sticky="w", padx=6)
        e_cap = ttk.Entry(cf_, textvariable=v_cap, width=30)
        e_cap.pack(side="left")
        ttk.Label(cf_, text="(vide : automatique)", foreground="#555").pack(side="left", padx=4)
        # rotation et perspective de l'incrustation choisie (demande de M7WUV)
        v_rot, v_tilt = tk.DoubleVar(value=0), tk.DoubleVar(value=0)
        # logo PNG à fond transparent (demande de RK1AT) : sans cadre, avec opacité
        v_logo, v_opa = tk.BooleanVar(value=False), tk.DoubleVar(value=100)
        lgf = ttk.Frame(f)
        lgf.grid(row=7, column=1, sticky="w", padx=6)
        ck_logo = ttk.Checkbutton(lgf, text="Logo (sans cadre, transparence gardée)", variable=v_logo)
        ck_logo.pack(side="left")
        ttk.Label(lgf, text="Opacité").pack(side="left", padx=(12, 4))
        sc_opa = ttk.Scale(lgf, from_=20, to=100, variable=v_opa, length=110)
        sc_opa.pack(side="left")
        lb_opa = ttk.Label(lgf, text="100 %", width=6)
        lb_opa.pack(side="left", padx=4)
        ttk.Label(f, text="Rotation").grid(row=8, column=0, sticky="w", pady=2)
        rf = ttk.Frame(f)
        rf.grid(row=8, column=1, sticky="w", padx=6)
        sc_rot = ttk.Scale(rf, from_=-trafic.PIP_ROT_MAX, to=trafic.PIP_ROT_MAX, variable=v_rot, length=200)
        sc_rot.pack(side="left")
        lb_rot = ttk.Label(rf, text="0°", width=5)
        lb_rot.pack(side="left", padx=4)
        b_straight = ttk.Button(rf, text="Remettre droit", command=lambda: straight())
        b_straight.pack(side="left", padx=(6, 0))
        ttk.Label(f, text="Perspective").grid(row=9, column=0, sticky="w", pady=2)
        tf_ = ttk.Frame(f)
        tf_.grid(row=9, column=1, sticky="w", padx=6)
        sc_tilt = ttk.Scale(tf_, from_=-100, to=100, variable=v_tilt, length=200)
        sc_tilt.pack(side="left")
        lb_tilt = ttk.Label(tf_, text="0", width=5)
        lb_tilt.pack(side="left", padx=4)
        cv = tk.Canvas(f, bg="black", width=480, height=360, highlightthickness=0, cursor="fleur")
        cv._no_theme = True
        cv.grid(row=10, column=0, columnspan=2, pady=(10, 0))
        ttk.Label(f, text="Souris : cliquez sur une image pour la choisir, faites-la glisser pour la placer, "
                          "molette pour l'agrandir ou la réduire, Maj + molette pour la tourner.",
                  foreground="#555", wraplength=480, justify="left").grid(
            row=11, column=0, columnspan=2, sticky="w", pady=(4, 0))

        def label_of(p):
            return next((l for l, c in cands if c["path"] == p["path"]), p.get("call") or "?")

        def refresh_list():
            """Liste, boutons et listes déroulantes d'après self.pips et l'incrustation choisie."""
            busy[0] = True
            try:
                lb.delete(0, "end")
                for i, p in enumerate(self.pips, 1):
                    lb.insert("end", f"{i}.  {label_of(p)}")
                if self.pips:
                    sel[0] = min(sel[0], len(self.pips) - 1)
                    lb.selection_clear(0, "end")
                    lb.selection_set(sel[0])
                    p = self.pips[sel[0]]
                    v_img.set(label_of(p))
                    v_c.set(corners["libre"] if p.get("pos") else corners.get(p.get("corner"), corners["haut-droite"]))
                    v_s.set(sizes["libre"] if p.get("scale") else sizes.get(p.get("size"), sizes["moyenne"]))
                    v_cap.set(p.get("cap") or "")
                    v_shape.set(shapes.get(p.get("shape") or "rect", shapes["rect"]))
                    v_logo.set(bool(p.get("logo")))
                    v_opa.set(round(float(p.get("opa", 1.0)) * 100))
                    v_rot.set(float(p.get("rot") or 0))
                    v_tilt.set(round(float(p.get("tilt") or 0) * 100))
                lb_opa.configure(text=f"{round(v_opa.get())} %")
                ck_logo.state(["!disabled"] if self.pips else ["disabled"])
                sc_opa.state(["!disabled"] if self.pips and v_logo.get() else ["disabled"])
                lb_rot.configure(text=f"{round(v_rot.get()):+d}°" if round(v_rot.get()) else "0°")
                lb_tilt.configure(text=f"{round(v_tilt.get()):+d}" if round(v_tilt.get()) else "0")
                for s_ in (sc_rot, sc_tilt):
                    s_.state(["!disabled"] if self.pips else ["disabled"])
                st = "readonly" if self.pips else "disabled"
                for c in (cb_img, cb_c, cb_s, cb_shape):
                    c.configure(state=st)
                e_cap.state(["!disabled"] if self.pips else ["disabled"])
                b_pc.state(["!disabled"] if len(self.pips) < self.PIP_MAX_N else ["disabled"])
                cb_img.configure(values=labels)
                b_add.state(["!disabled"] if len(self.pips) < self.PIP_MAX_N and cands else ["disabled"])
                b_del.state(["!disabled"] if self.pips else ["disabled"])
            finally:
                busy[0] = False

        def store():
            """Listes déroulantes -> incrustation choisie, puis réglages."""
            self.conf.update(pip_on=bool(v_on.get()), pip_report=bool(v_rep.get()))
            if self.pips:
                p = self.pips[sel[0]]
                if v_img.get() in labels:
                    p.update(cands[labels.index(v_img.get())][1])
                p["cap"] = v_cap.get().strip() or None
                p["shape"] = next((k for k, n in shapes.items() if n == v_shape.get()), "rect")
                p["logo"] = bool(v_logo.get())
                p["opa"] = round(v_opa.get()) / 100
                lb_opa.configure(text=f"{round(v_opa.get())} %")
                sc_opa.state(["!disabled"] if p["logo"] else ["disabled"])
                ck = next((k for k, n in corners.items() if n == v_c.get()), "haut-droite")
                sk = next((k for k, n in sizes.items() if n == v_s.get()), "moyenne")
                if ck == "libre":
                    if not p.get("pos"):
                        p["pos"] = [1.0, 0.0]
                else:
                    p["corner"], p["pos"] = ck, None
                if sk == "libre":
                    if not p.get("scale"):
                        p["scale"] = trafic.PIP_SCALE.get(p.get("size", "moyenne"), 0.34)
                else:
                    p["size"], p["scale"] = sk, None
                p["rot"] = int(round(v_rot.get()))
                p["tilt"] = round(v_tilt.get()) / 100
                lb_rot.configure(text=f"{p['rot']:+d}°" if p["rot"] else "0°")
                lb_tilt.configure(text=f"{round(p['tilt'] * 100):+d}" if p["tilt"] else "0")
                self._pip_save_layouts()
            if hasattr(self, "v_pipon"):
                self.v_pipon.set(bool(v_on.get()))
            self._save_conf_file()

        def preview(*_):
            if busy[0]:
                return
            store()
            real = self.src_img
            if real is None:
                real = geo.setdefault("blank", Image.new("RGB", (640, 480), (40, 90, 140)))
            if geo.get("src_id") != id(real):
                # aperçu sur une copie réduite : rapide même avec une photo de 12 Mpx
                # (positions et tailles sont en fractions de l'image : même résultat)
                small = real.copy()
                small.thumbnail((960, 720))
                geo["src_id"], geo["small"] = id(real), small
            im, geo["rects"] = self._pip_compose(geo["small"])
            geo["size"] = im.size
            im = im.copy()
            im.thumbnail((480, 360))
            k = geo["k"] = im.width / geo["size"][0]
            ox, oy = geo["off"] = ((480 - im.width) // 2, (360 - im.height) // 2)
            self._photos["pip"] = ImageTk.PhotoImage(im)
            cv.delete("all")
            cv.create_image(ox, oy, image=self._photos["pip"], anchor="nw")
            r = cur_rect()
            if r and len(self.pips) > 1:                      # cadre sur l'incrustation choisie
                x, y, W, H = r
                cv.create_rectangle(ox + x * k - 2, oy + y * k - 2, ox + (x + W) * k + 1, oy + (y + H) * k + 1,
                                    outline="#ffcc00", width=2, dash=(4, 2))
            self._pip_cache = None

        def select(i):
            if 0 <= i < len(self.pips) and i != sel[0]:
                sel[0] = i
                refresh_list()
                preview()

        def add():
            if len(self.pips) >= self.PIP_MAX_N or not cands:
                return
            used = {p["path"] for p in self.pips}
            cand = next((c for _, c in cands if c["path"] not in used), cands[0][1])
            self.pips.append(self._pip_new(cand))
            sel[0] = len(self.pips) - 1
            v_on.set(True)
            refresh_list()
            preview()

        def add_pc():
            """Bouton « Image du PC… » : une image de l'ordinateur, incrustée comme celles reçues."""
            if len(self.pips) >= self.PIP_MAX_N:
                messagebox.showinfo(APP, tr("4 images au maximum dans l'image TX. Retirez-en une dans "
                                            "« Image du correspondant… »."), parent=w)
                return
            types = " ".join("*" + e for e in self.PIP_LOCAL_TYPES)
            path = filedialog.askopenfilename(parent=w, title=tr("Image à incruster"),
                                              filetypes=[(tr("Images"), types), (tr("Tous les fichiers"), "*.*")])
            if not path:
                return
            try:
                self._pip_thumb(path)
            except Exception as e:
                messagebox.showerror(APP, tr("Image illisible :") + f" {e}", parent=w)
                return
            self._pip_remember_local(path)
            cand = {"path": path, "call": "", "snr": None, "local": True}
            lab = self._pip_local_label(path)
            if path not in [c["path"] for _, c in cands]:
                cands.append((lab, cand))
                labels.append(lab)
            # PNG à fond transparent : posé comme un logo (sans cadre), case déjà cochée
            logo = self._pip_thumb(path).mode == "RGBA"
            self.pips.append(dict(self._pip_new(cand), cap=None, logo=logo, opa=1.0))
            sel[0] = len(self.pips) - 1
            v_on.set(True)
            refresh_list()
            preview()

        def remove():
            if not self.pips:
                return
            del self.pips[sel[0]]
            sel[0] = max(0, sel[0] - 1)
            self._pip_save_layouts()
            refresh_list()
            preview()

        def set_free(pos=None, scale=None):
            """Glisser / molette : position et taille de l'incrustation choisie deviennent « Libre »."""
            p = self.pips[sel[0]]
            busy[0] = True
            try:
                if pos is not None:
                    p["pos"] = [round(min(1.0, max(0.0, v)), 4) for v in pos]
                    v_c.set(corners["libre"])
                if scale is not None:
                    p["scale"] = round(scale, 4)
                    v_s.set(sizes["libre"])
            finally:
                busy[0] = False
            preview()

        def cur_rect():
            rs = geo.get("rects") or []
            return rs[sel[0]] if self.pips and sel[0] < len(rs) and geo.get("k") else None

        def hit(e):
            """Incrustation sous la souris (la plus haute) -> indice, ou None."""
            k, (ox, oy) = geo.get("k"), geo.get("off", (0, 0))
            if not k:
                return None
            ix, iy = (e.x - ox) / k, (e.y - oy) / k
            for i in range(len(geo.get("rects") or []) - 1, -1, -1):
                r = geo["rects"][i]
                if r and r[0] <= ix <= r[0] + r[2] and r[1] <= iy <= r[1] + r[3]:
                    return i
            return None

        def pos_for(x, y, W, H):
            iw, ih = geo["size"]
            return (x / (iw - W) if iw > W else 0.0, y / (ih - H) if ih > H else 0.0)

        def press(e):
            i = hit(e)
            if i is not None:
                select(i)
            r = cur_rect()
            if not r:
                return
            k, (ox, oy) = geo["k"], geo["off"]
            ix, iy = (e.x - ox) / k, (e.y - oy) / k
            x, y, W, H = r
            # clic sur l'incrustation : on la saisit là ; ailleurs : elle vient se centrer sous la souris
            geo["grab"] = (ix - x, iy - y) if i is not None else (W / 2, H / 2)
            drag(e)

        def drag(e):
            r = cur_rect()
            if not r or "grab" not in geo:
                return
            k, (ox, oy) = geo["k"], geo["off"]
            x, y, W, H = r
            gx, gy = geo["grab"]
            set_free(pos=pos_for((e.x - ox) / k - gx, (e.y - oy) / k - gy, W, H))

        def wheel(e, step):
            i = hit(e)
            if i is not None:
                select(i)
            r = cur_rect()
            if not r:
                return
            p = self.pips[sel[0]]
            x, y, W, H = r
            cx, cy = x + W / 2, y + H / 2                     # le centre ne bouge pas
            cur = p.get("scale") or trafic.PIP_SCALE.get(p.get("size", "moyenne"), 0.34)
            new = min(trafic.PIP_MAX, max(trafic.PIP_MIN, cur * (1.1 if step > 0 else 1 / 1.1)))
            nW, nH = W * new / cur, H * new / cur
            set_free(pos=pos_for(cx - nW / 2, cy - nH / 2, nW, nH), scale=new)

        def straight():
            busy[0] = True
            v_rot.set(0)
            v_tilt.set(0)
            busy[0] = False
            preview()

        def turn(e, step):
            """Maj + molette : tourne l'incrustation sous la souris (ou la choisie) de 3°."""
            i = hit(e)
            if i is not None:
                select(i)
            if not self.pips:
                return
            busy[0] = True
            v_rot.set(max(-trafic.PIP_ROT_MAX, min(trafic.PIP_ROT_MAX, round(v_rot.get()) + 3 * step)))
            busy[0] = False
            preview()

        def on_list(_e):
            s = lb.curselection()
            if s:
                select(s[0])

        lb.bind("<<ListboxSelect>>", on_list)
        cv.bind("<ButtonPress-1>", press)
        cv.bind("<B1-Motion>", drag)
        cv.bind("<ButtonRelease-1>", lambda e: geo.pop("grab", None))
        cv.bind("<MouseWheel>", lambda e: wheel(e, 1 if e.delta > 0 else -1))
        cv.bind("<Button-4>", lambda e: wheel(e, 1))
        cv.bind("<Button-5>", lambda e: wheel(e, -1))
        cv.bind("<Shift-MouseWheel>", lambda e: turn(e, 1 if e.delta > 0 else -1))
        cv.bind("<Shift-Button-4>", lambda e: turn(e, 1))
        cv.bind("<Shift-Button-5>", lambda e: turn(e, -1))

        def changed(*_):
            if not busy[0]:
                self.after_idle(lambda: (preview(), refresh_list()))

        for var in (v_img, v_c, v_s, v_rep, v_on, v_rot, v_tilt, v_cap, v_logo, v_opa, v_shape):
            var.trace_add("write", changed)
        ttk.Button(f, text="OK", command=lambda: (store(), w.destroy(), self.prepare())).grid(
            row=12, column=1, sticky="e", pady=(10, 0))
        refresh_list()
        preview()
        self._translate_ui(w)

    def trafic_dialog(self):
        """Fenêtre « Mes conditions de trafic » (bandeau incrusté sur l'image émise)."""
        w = getattr(self, "_tc_win", None)
        if w is not None and w.winfo_exists():
            w.lift()
            return
        w = self._tc_win = tk.Toplevel(self)
        w.title("Mes conditions de trafic")
        w.transient(self)
        w.resizable(False, False)
        f = ttk.Frame(w, padding=12)
        f.pack(fill="both", expand=True)
        c = dict(trafic.DEFAULT, **{k: v for k, v in self.conf.items() if k.startswith("tc_")})
        model = getattr(self.rig, "model", "") if self.rig is not None else ""
        v = {k: tk.StringVar(value=str(c[k])) for k in ("tc_rig", "tc_power", "tc_ant", "tc_qth", "tc_extra")}
        b = {k: tk.BooleanVar(value=bool(c[k])) for k in ("tc_on", "tc_call", "tc_loc", "tc_freq", "tc_date")}
        pos_names = {"bas": tr("En bas"), "haut": tr("En haut")}
        size_names = {"petite": tr("Petite"), "normale": tr("Normale"), "grande": tr("Grande")}
        v_pos = tk.StringVar(value=pos_names.get(c["tc_pos"], pos_names["bas"]))
        v_size = tk.StringVar(value=size_names.get(c["tc_size"], size_names["normale"]))
        ttk.Checkbutton(f, text="Ajouter ces informations sur les images émises", variable=b["tc_on"]).grid(
            row=0, column=0, columnspan=3, sticky="w")
        rows = [("Poste", "tc_rig", tr("vide = poste lu par CAT") + (f" ({model})" if model else "")),
                ("Puissance (W)", "tc_power", "ex. 100"), ("Antenne", "tc_ant", "ex. dipôle 40 m, Yagi 3 él."),
                ("QTH", "tc_qth", "ex. Flers (61)"), ("Autre", "tc_extra", "ex. TNX QSO 73 !")]
        for i, (lab, k, hint) in enumerate(rows, 1):
            ttk.Label(f, text=lab).grid(row=i, column=0, sticky="w", pady=2)
            ttk.Entry(f, textvariable=v[k], width=30).grid(row=i, column=1, sticky="w", padx=6, pady=2)
            ttk.Label(f, text=hint, foreground="#777").grid(row=i, column=2, sticky="w")
        cf = ttk.Frame(f)
        cf.grid(row=7, column=0, columnspan=3, sticky="w", pady=(6, 0))
        for k, lab in (("tc_call", "Indicatif"), ("tc_loc", "Locator"), ("tc_freq", "Fréquence (CAT)"),
                       ("tc_date", clocktz.label(tr("Date et heure")))):
            ttk.Checkbutton(cf, text=lab, variable=b[k]).pack(side="left", padx=(0, 10))
        pf = ttk.Frame(f)
        pf.grid(row=8, column=0, columnspan=3, sticky="w", pady=(6, 0))
        ttk.Label(pf, text="Position").pack(side="left")
        ttk.Combobox(pf, textvariable=v_pos, values=list(pos_names.values()), width=8, state="readonly").pack(
            side="left", padx=6)
        ttk.Label(pf, text="Taille du texte").pack(side="left", padx=(10, 0))
        ttk.Combobox(pf, textvariable=v_size, values=list(size_names.values()), width=9, state="readonly").pack(
            side="left", padx=6)
        # --- police et couleurs
        fams = list(trafic.fonts()) or ["Arial"]
        v_font = tk.StringVar(value=c["tc_font"] if c["tc_font"] in fams else
                              ("Arial" if "Arial" in fams else fams[0]))
        sb = {k: tk.BooleanVar(value=bool(c[k])) for k in ("tc_bold", "tc_italic", "tc_frame")}
        col = {k: tk.StringVar(value=c[k]) for k in ("tc_color", "tc_stroke", "tc_bg", "tc_callcolor")}
        v_alpha = tk.IntVar(value=int(c["tc_alpha"]))
        sf = ttk.LabelFrame(f, text="Police et couleurs", padding=8)
        sf.grid(row=9, column=0, columnspan=3, sticky="we", pady=(8, 0))
        r1 = ttk.Frame(sf)
        r1.pack(fill="x")
        ttk.Label(r1, text="Police").pack(side="left")
        ttk.Combobox(r1, textvariable=v_font, values=fams, width=26, state="readonly").pack(side="left", padx=6)
        ttk.Checkbutton(r1, text="Gras", variable=sb["tc_bold"]).pack(side="left", padx=(6, 0))
        ttk.Checkbutton(r1, text="Italique", variable=sb["tc_italic"]).pack(side="left", padx=(6, 0))
        r2 = ttk.Frame(sf)
        r2.pack(fill="x", pady=(6, 0))

        def swatch(parent, key, label, can_none=False):
            fr = ttk.Frame(parent)
            fr.pack(side="left", padx=(0, 12))
            ttk.Label(fr, text=label).pack(side="left")
            btn = tk.Button(fr, width=3, relief="solid", bd=1)
            btn._no_theme = True
            btn.pack(side="left", padx=4)

            def paint(*_):
                vv = col[key].get()
                btn.configure(bg=vv or "#d9d9d9", activebackground=vv or "#d9d9d9",
                              text="" if vv else "—")

            def pick():
                from tkinter import colorchooser
                rgb, hx = colorchooser.askcolor(color=col[key].get() or "#ffffff", parent=w)
                if hx:
                    col[key].set(hx)
            btn.configure(command=pick)
            if can_none:
                ttk.Button(fr, text="✕", width=2, command=lambda: col[key].set("")).pack(side="left")
            col[key].trace_add("write", paint)
            paint()

        swatch(r2, "tc_color", tr("Texte"))
        swatch(r2, "tc_callcolor", tr("Indicatif"), True)
        swatch(r2, "tc_stroke", tr("Contour"), True)
        swatch(r2, "tc_bg", tr("Fond"))
        r3 = ttk.Frame(sf)
        r3.pack(fill="x", pady=(6, 0))
        ttk.Label(r3, text="Opacité du fond").pack(side="left")
        lb_a = ttk.Label(r3, width=5)
        ttk.Scale(r3, from_=0, to=100, variable=v_alpha, length=160,
                  command=lambda x: (v_alpha.set(round(float(x) / 5) * 5))).pack(side="left", padx=6)
        lb_a.pack(side="left")
        v_alpha.trace_add("write", lambda *a: lb_a.configure(text=f"{v_alpha.get()} %"))
        lb_a.configure(text=f"{v_alpha.get()} %")
        ttk.Checkbutton(r3, text="Filet de couleur au bord du bandeau", variable=sb["tc_frame"]).pack(
            side="left", padx=(12, 0))
        presets = {tr("Modèles…"): None,
                   tr("Classique (blanc sur noir)"): ("#ffffff", "", "#000000", "#000000", 60, False),
                   tr("Jaune et rouge"): ("#ffff00", "#ff4040", "#000000", "#002060", 70, True),
                   tr("Vert radio"): ("#7CFC00", "#ffffff", "#000000", "#003000", 75, True),
                   tr("Noir sur blanc"): ("#000000", "#c00000", "", "#ffffff", 80, False),
                   tr("Sans fond (contour seul)"): ("#ffffff", "#ffd700", "#000000", "#000000", 0, False)}
        v_pre = tk.StringVar(value=tr("Modèles…"))

        def apply_preset(*_):
            p = presets.get(v_pre.get())
            if p:
                for k, x in zip(("tc_color", "tc_callcolor", "tc_stroke", "tc_bg"), p[:4]):
                    col[k].set(x)
                v_alpha.set(p[4])
                sb["tc_frame"].set(p[5])
                v_pre.set(tr("Modèles…"))
        cb_pre = ttk.Combobox(r1, textvariable=v_pre, values=list(presets), width=22, state="readonly")
        cb_pre.pack(side="right", padx=(12, 0))
        cb_pre.bind("<<ComboboxSelected>>", apply_preset)
        cv = tk.Label(f, bg="black")
        cv._no_theme = True
        cv.grid(row=10, column=0, columnspan=3, pady=(10, 0))

        def store():
            for k, var in v.items():
                self.conf[k] = var.get().strip()
            for k, var in b.items():
                self.conf[k] = bool(var.get())
            self.conf["tc_pos"] = next(k for k, n in pos_names.items() if n == v_pos.get())
            self.conf["tc_size"] = next(k for k, n in size_names.items() if n == v_size.get())
            self.conf["tc_font"] = v_font.get()
            for k, var in sb.items():
                self.conf[k] = bool(var.get())
            for k, var in col.items():
                self.conf[k] = var.get()
            self.conf["tc_alpha"] = int(v_alpha.get())
            self._save_conf_file()
            if hasattr(self, "v_tcon"):
                self.v_tcon.set(bool(self.conf["tc_on"]))

        def preview(*_):
            store()
            on = self.conf.get("tc_on")
            self.conf["tc_on"] = True
            base = self.src_img
            if base is None:
                base = Image.new("RGB", (640, 480), (40, 90, 140))
                self.src_img = base
                im = self._tx_source()
                self.src_img = None
            else:
                im = self._tx_source()
            self.conf["tc_on"] = on
            im = im.copy()
            im.thumbnail((480, 360))
            self._photos["tc"] = ImageTk.PhotoImage(im)
            cv.configure(image=self._photos["tc"])

        for var in list(v.values()) + list(b.values()) + list(sb.values()) + list(col.values()) + [
                v_pos, v_size, v_font, v_alpha]:
            var.trace_add("write", lambda *a: self._tc_preview_later(preview))
        bt = ttk.Frame(f)
        bt.grid(row=11, column=0, columnspan=3, sticky="e", pady=(10, 0))
        ttk.Button(bt, text="OK", command=lambda: (store(), w.destroy(), self.prepare())).pack(side="left")
        preview()
        self._translate_ui(w)

    def _tc_preview_later(self, fn):
        """Aperçu regroupé (le curseur d'opacité envoie beaucoup d'événements)."""
        if getattr(self, "_tc_job", None):
            self.after_cancel(self._tc_job)
        self._tc_job = self.after(120, lambda: (setattr(self, "_tc_job", None), fn()))

    def _robust_choice(self):
        """-> pourcentage choisi, ou None pour « Auto »."""
        v = self.v_over.get()
        for lab, p in ROBUST:
            if v in (lab, tr(lab)):
                return p
        digits = "".join(ch for ch in v if ch.isdigit())
        return int(digits) if digits else None

    def _robust_conf(self):
        p = self._robust_choice()
        return "auto" if p is None else p

    def _robust_pct(self, mode=None):
        """Redondance (%) effective. « Auto » : d'après la marge entre le report le plus
        faible et le seuil du mode — lien confortable 15 %, juste 25 %, limite 40 %."""
        p = self._robust_choice()
        if p is not None:
            return p
        snr = self._link_snr()[0]
        if snr is None:
            return 15
        margin = snr - MODE_THR.get(mode or self._tx_mode(), 10)
        return 15 if margin >= 4 else (25 if margin >= 2 else 40)

    def _link_snr(self):
        """Report le plus faible des stations ces 45 dernières minutes.
        -> (dB ou None, nombre de stations, origine)."""
        now, reps = time.time(), {}
        for iid, d in self.rxok_by_id.items():
            if iid in self.my_ids:                       # reports sur NOS images
                for call, (rep, t) in d.items():
                    if rep is not None and now - t < AUTO_MAX_AGE:
                        reps[call] = min(rep, reps.get(call, rep))
        if reps:
            return min(reps.values()), len(reps), "reports"
        # sinon : ce que nous avons mesuré en les entendant (le chemin retour ressemble à l'aller)
        snrs = {c: h["snr"] for c, h in self.heard.items()
                if h.get("snr") is not None and now - h.get("t", 0) < AUTO_MAX_AGE}
        if snrs:
            return min(snrs.values()), len(snrs), "écoute"
        return None, 0, ""

    def _tx_mode(self, explain=False):
        """Mode d'émission effectif (« Auto » : choisi d'après les reports)."""
        m = self.v_mode.get()
        if m != "Auto":
            return (m, "") if explain else m
        snr, n, src = self._link_snr()
        if snr is None:
            mode, why = AUTO_DEFAULT, "aucun report récent"
        else:
            mode = next(md for th, md in AUTO_STEPS if th is None or snr >= th)
            why = (f"report le plus faible {snr:+.0f} dB ({n} station{'s' if n > 1 else ''})"
                   if src == "reports" else f"stations entendues, la plus faible à {snr:+.0f} dB")
        return (mode, why) if explain else mode

    # ------------------------------------------------------------- préparation en tâche de fond
    def _cz(self, fn, *args, **kw):
        """Appel lourd de la préparation (compression…) : résultat gardé en mémoire. Pendant une
        préparation en tâche de fond, un calcul absent lève _NeedCompute : il est fait dans un
        autre fil, puis la préparation recommence et le trouve tout prêt."""
        obj = args[0]
        key = (getattr(fn, "__name__", str(fn)), id(obj), getattr(obj, "size", None), args[1:],
               tuple(sorted(kw.items())))
        cache = self.__dict__.setdefault("_cz_cache", {})
        hit = cache.get(key)
        if hit is not None and hit[0] is obj:
            return hit[1]
        if getattr(self, "_cz_async", False):
            raise _NeedCompute(key, obj, fn, args, kw)
        res = fn(*args, **kw)
        self._cz_put(key, obj, res)
        return res

    def _cz_put(self, key, obj, res):
        cache = self.__dict__.setdefault("_cz_cache", {})
        cache[key] = (obj, res)
        while len(cache) > 40:
            cache.pop(next(iter(cache)))

    def prepare(self, sync=False):
        """Prépare l'image à émettre sans figer la fenêtre : les compressions longues sont
        faites en tâche de fond (« Calcul de l'image… »), un nouveau réglage relance le calcul.
        sync=True : tout de suite (au moment d'émettre)."""
        if sync:
            self._cz_async = False
            self._prep_waiting = False
            return self._prepare_sync()
        self._cz_async = True
        try:
            self._prepare_sync()
            self._prep_waiting = False
            self._prep_show_busy(False)
        except _NeedCompute as nc:
            self._prep_waiting = True
            self._prep_show_busy(True)
            self._prep_start(nc)
        finally:
            self._cz_async = False

    def _prep_start(self, nc):
        if getattr(self, "_prep_thread_busy", False):
            self._prep_again = True                    # un calcul tourne : on refera la préparation après
            return
        self._prep_thread_busy, self._prep_again = True, False

        def run():
            try:
                res = nc.fn(*nc.args, **nc.kw)
                self.ui(self._cz_put, nc.key, nc.obj, res)
            except Exception as e:
                self.ui(self.log_exc, "Préparation de l'image", e)
                self.ui(self._prep_failed, nc)
                return
            finally:
                self.ui(setattr, self, "_prep_thread_busy", False)
            self.ui(self.prepare)

        threading.Thread(target=run, daemon=True).start()

    def _prep_failed(self, nc):
        self._prep_waiting = False
        self._prep_show_busy(False)

    def _prep_show_busy(self, busy):
        if busy == getattr(self, "_prep_busy_shown", False):
            return
        self._prep_busy_shown = busy
        if busy:
            self.v_txinfo.set(tr("Calcul de l'image…"))
            self._set_text(self.lb_cmp_info, tr("Calcul de l'image…"))
        try:
            self.lb_cmp.configure(cursor="watch" if busy else "")
        except tk.TclError:
            pass

    def _prepare_sync(self):
        """Fait tenir l'image dans la durée demandée : calcule le budget en octets
        pour le mode et la redondance, puis la taille/qualité qui y entrent."""
        hyb = bool(self.v_hyb.get())
        for w in getattr(self, "_radio_widgets", []):     # sans objet en hybride
            w.configure(state="disabled" if hyb else
                        ("readonly" if getattr(w, "_ro", False) else "normal"))
        if self.src_img is None or self.tx_busy:
            return
        if hyb:
            return self._prepare_hybrid()
        try:
            (mode, auto_why), width, fmt = self._tx_mode(explain=True), self.v_width.get(), self._fmt()
            seconds = int(float(self.v_sec.get()))
            over = self._robust_pct(mode) / 100
        except (tk.TclError, ValueError):
            return
        src = self._tx_source()
        if mode == engine.DRM_MODE:
            return self._prepare_drm(src, width, fmt, seconds)
        if fmt == "original" and (self.src_raw is None or self.src_kind not in ORIGINAL_KINDS
                                  or src is not self.src_img):
            fmt = "jpeg"                      # carte QSL, BMP, TIFF, bandeau ajouté… : réencodé en JPEG
        pfmt = fmt if fmt in ("avif", "webp") else "avif"
        # aperçu rapide : seulement pour les émissions longues, pris sur la durée totale
        preview = None
        if self.v_prev.get() and seconds >= PREVIEW_MIN_S:
            w = {"DATAC1X": 200, "DATAC1": 160, "DATAC3": 128, "DATAC4": 96}[mode]
            preview = self._cz(engine.compress, src, w, PREVIEW_BYTES[mode], pfmt)[0]
            seconds_main = seconds - engine.Transmission(preview, pfmt, "X", mode, 0.25).estimate_s() + 0.7
        else:
            seconds_main = seconds
        budget = engine.max_bytes_for(mode, seconds_main, over)
        if fmt == "original":
            data, fmt = self._payload(fmt)
            q, size = None, (self.src_img.width, self.src_img.height)
        elif width == "auto":
            data, q, size = self._cz(engine.compress_auto, src, budget, fmt)
        else:
            data, q, size = self._cz(engine.compress, src, width, budget, fmt)
        if len(data) > budget:
            mini = seconds
            while engine.max_bytes_for(mode, mini, over) < len(data) and mini < 7200:
                mini += 15
            self.tx = None
            self._set_text(self.lb_cmp_info, "")
            if q is None:
                self.v_txinfo.set(f"Fichier original ({len(data)} octets) : {seconds} s, c'est trop court en {mode}.\n"
                                  f"Minimum : environ {_fmt_s(mini)}, ou choisissez avif / jpeg pour le réduire.")
            else:
                if fmt == "jpeg":
                    self.v_txinfo.set(f"{seconds} s, c'est trop court pour une image en {mode}.\n"
                                      f"JPEG : minimum environ {_fmt_s(mini)} (le JPEG demande plus d'octets "
                                      f"que l'AVIF), ou choisissez avif.")
                else:
                    self.v_txinfo.set(f"{seconds} s, c'est trop court pour une image en {mode}.\n"
                                      f"Minimum : environ {_fmt_s(mini)}, ou choisissez un mode plus rapide.")
            return
        call = self.mycall() or "NOCALL"
        text = self.txt_msg.get("1.0", "end").strip() if self.v_txtinc.get() else ""
        if text:
            data = protocol.pack_text(text, data)
        key = (data, fmt, call, mode, over, preview)
        if self.tx is None or getattr(self.tx, "key", None) != key:
            # nouvelle image ou nouveaux réglages ; sinon on garde l'émetteur pour que
            # « Compléter » et les réémissions envoient des symboles jamais émis
            self.tx = engine.Transmission(data, "hft" if text else fmt, call, mode, over, preview=preview)
            self.tx.key = key
            self.tx.msg_text = text
        if q is None and fmt == "gif" and self.src_anim is not None:
            self.lb_cmp.set_animation(*self.src_anim)      # GIF animé en radio (fichier original)
        else:
            self._show(self.lb_cmp, "cmp", self.src_img if q is None else
                       Image.open(io.BytesIO(protocol.unpack_text(data)[1])))
        desc = (f"{imgfmt.describe(fmt)} original" + (", gzip" if fmt == "svg" else "")) if q is None \
            else engine.quality_label(fmt, q)
        self._set_text(self.lb_cmp_info, f"{size[0]}×{size[1]} — {len(data)} octets ({desc})"
                                   + (" + texte" if text else ""))
        est = self.tx.estimate_s()
        lines = [(f"Mode Auto → {mode} ({auto_why})" if self.v_mode.get() == "Auto" else f"Mode {mode}")
                 + f" (~{MODE_BPS[mode]} bit/s), robustesse {self._robust_pct(mode)} %"
                 + (" (auto)" if self._robust_choice() is None else ""),
                 f"{self.tx.sender.K} symboles de {self.tx.sender.T} octets",
                 f"Durée d'émission : {_fmt_s(est)}"]
        if preview:
            lines.append(f"Aperçu reçu après ~{self.tx.preview_s():.0f} s")
        if q is not None and q < 35:
            # combien de temps pour une qualité correcte à cette taille ?
            need = self._cz(engine.bytes_for_quality, src, size[0], 45, fmt)
            t_need = seconds
            while engine.max_bytes_for(mode, t_need, over) < need and t_need < 7200:
                t_need += 15
            lines.append(f"Qualité faible (q{q}). Pour {size[0]} px en bonne qualité : "
                         f"~{_fmt_s(t_need)}, ou réduisez la largeur.")
        self.v_txinfo.set("\n".join(lines))
        self._update_comp()

    def _prepare_drm(self, src, width, fmt, seconds):
        """Mode EasyPal (HamDRM) : image en JPEG 2000 (ou JPEG) pour tenir dans la durée,
        lisible par les stations EasyPal et QSSTV."""
        params = self._drm_params()
        if fmt == "original" and self.src_raw is not None and self.src_kind in ("jpeg", "png") \
                and src is self.src_img:
            data, fmt, q = self.src_raw, self.src_kind, None
            size = (self.src_img.width, self.src_img.height)
        else:
            fmt = DRM_FORMATS.get(fmt, "jp2")
            budget = engine.drm_budget(seconds, params)
            if width == "auto":
                data, q, size = self._cz(engine.compress_auto, src, budget, fmt,
                                         widths=(800, 640, 480, 400, 320, 240, 160))
            else:
                data, q, size = self._cz(engine.compress, src, width, budget, fmt)
            if len(data) > budget:
                mini = seconds
                while engine.drm_budget(mini, params) < len(data) and mini < 7200:
                    mini += 15
                self.tx = None
                self._set_text(self.lb_cmp_info, "")
                self.v_txinfo.set(f"{seconds} s, c'est trop court pour une image en mode EasyPal.\n"
                                  f"Minimum : environ {_fmt_s(mini)}, ou un mode plus rapide (A, QAM64).")
                return
        call = self.mycall() or "NOCALL"
        key = ("drm", data, fmt, call, tuple(getattr(params, f) for f, _ in params._fields_))
        if self.tx is None or getattr(self.tx, "key", None) != key:
            base = os.path.splitext(os.path.basename(getattr(self, "src_path", "") or "image"))[0]
            self.tx = engine.DrmTransmission(data, fmt, call, params, f"{call}_{base}")
            self.tx.key = key
        self._show(self.lb_cmp, "cmp", self.src_img if q is None else Image.open(io.BytesIO(data)))
        desc = f"{imgfmt.describe(fmt)} original" if q is None else engine.quality_label(fmt, q)
        self._set_text(self.lb_cmp_info, f"{size[0]}×{size[1]} — {len(data)} octets ({desc})")
        lines = [f"Mode EasyPal (HamDRM) : {hamdrm.describe(params)}",
                 "Lisible par les stations EasyPal et QSSTV ; réparation par BSR / FIX",
                 f"Durée d'émission : {_fmt_s(self.tx.estimate_s())}"]
        if self.v_txtinc.get():
            lines.append("« Texte inclus » n'existe pas en mode EasyPal : seule l'image part.")
        self.v_txinfo.set("\n".join(lines))
        self._update_comp()

    def _prepare_hybrid(self):
        """Mode hybride : l'image peut être bien plus grande, elle passe par Internet."""
        try:
            width, kb = self.v_hwidth.get(), float(self.v_hkb.get())
        except (tk.TclError, ValueError):
            return
        fmt = self._fmt()
        anim = self.src_anim is not None
        # bulles avec émoticônes animées : l'image part en GIF animé (mode hybride seulement)
        banim = not anim and bubbles.has_anim(self.bubbles)
        if anim and fmt != "original":
            self.v_fmt.set("original")         # un GIF animé part tel quel (animation gardée)
            fmt = "original"
        src = self.src_img if anim else self._tx_source()
        if fmt == "original" and (self.src_raw is None or self.src_kind not in ORIGINAL_KINDS
                                  or src is not self.src_img):
            fmt = "jpeg"
        drm_hyb = self.v_mode.get() == engine.DRM_MODE
        if drm_hyb and (fmt in ("avif", "webp") or (fmt == "original" and self.src_kind in ("avif", "webp", "svg"))):
            fmt = "jpeg"                      # EasyPal n'affiche ni AVIF, ni WebP, ni SVG
        how = ""
        if anim:
            try:
                limit = int(float(self.v_gifkb.get()) * 1000)
            except (tk.TclError, ValueError):
                limit = 2_000_000
            if any((b.get("text") or "").strip() for b in self.bubbles):
                # GIF animé reçu + bulles : bulles dessinées sur chaque image, animation gardée
                data, how = self._cz(bubbles.gif_with_bubbles, self.src_raw,
                                     json.dumps(self.bubbles, sort_keys=True), limit)
            else:
                data, how = self._cz(imgfmt.gif_shrink, self.src_raw, limit)
            fmt, q = "gif", None
            im0 = Image.open(io.BytesIO(data))
            size = im0.size
        elif banim:
            base = self._tx_source_nobubbles() or self.src_img
            try:
                wmax = min(1024, int(width))
            except (TypeError, ValueError):
                wmax = 800
            try:
                limit = int(float(self.v_gifkb.get()) * 1000)
            except (tk.TclError, ValueError):
                limit = 2_000_000
            data, how = self._cz(bubbles.make_gif, base, json.dumps(self.bubbles, sort_keys=True), wmax, limit)
            fmt, q, anim = "gif", None, True
            size = Image.open(io.BytesIO(data)).size
        elif fmt == "original":
            data, fmt = self._payload(fmt, hybrid=True)
            q, size = None, (self.src_img.width, self.src_img.height)
            if len(data) > HYB_MAX_BYTES:
                # trop gros pour les stations qui reçoivent (8 Mo au plus) : même image, recompressée
                fmt = "jpeg"
                data, q, size = self._cz(engine.compress, src, "originale", HYB_MAX_BYTES, fmt)
                if len(data) > HYB_MAX_BYTES:            # même à qualité minimale : image réduite
                    data, q, size = self._cz(engine.compress_auto, src, HYB_MAX_BYTES, fmt)
        else:
            data, q, size = self._cz(engine.compress, src, width, int(kb * 1000), fmt)
        call = self.mycall() or "NOCALL"
        key = ("hyb", data, fmt, call)
        if self.tx is None or getattr(self.tx, "key", None) != key:
            self.tx = HybridJob(data, fmt, call)
            self.tx.key = key
        if anim:
            self.lb_cmp.set_animation(*imgfmt.gif_frames(data))
            n, secs = imgfmt.gif_info(data)
            desc = f"GIF animé, {n} images, {secs:.1f} s" + (f", {how}" if how else "")
        else:
            self._show(self.lb_cmp, "cmp", self.src_img if q is None else Image.open(io.BytesIO(data)))
            desc = f"{imgfmt.describe(fmt)} original" if q is None else engine.quality_label(fmt, q)
        self._set_text(self.lb_cmp_info, f"{size[0]}×{size[1]} — {len(data)} octets ({desc})")
        if drm_hyb:
            self.tx.drm = True
            cfg = self._hyb_cfg()
            srv = cfg["host"] or "(serveur FTP non réglé)"
            ann = hamdrm.estimate(120, easypal_hybrid_params(cfg_call=call)) if hamdrm.AVAILABLE else 0
            self.v_txinfo.set(f"Mode hybride EasyPal (lisible par EasyPal et QSSTV)\n"
                              f"Image déposée par FTP sur {srv}, dossier {easypal_hybrid.FILES_DIR}\n"
                              f"Annonce radio : ~{ann:.0f} s (HamDRM mode E, QAM4)\n"
                              f"Attention : l'identifiant et le mot de passe FTP partent dans l'annonce "
                              f"(compte FTP dédié conseillé)")
            self._update_comp()
            return
        srv = self.v_hurl.get().strip() or "(lien public non réglé)"
        slow = (fmt in ("avif", "webp") and q is not None
                and size[0] * size[1] >= engine.SAMPLE_MIN_PX_AVIF)
        self.v_txinfo.set(f"Mode hybride\nImage déposée par FTP sur :\n{srv}\n"
                          + ("Annonce radio : ~9 s (DATAC13 robuste + DATAC0, éclair : lien par Internet)"
                             if self.v_flash.get() else "Annonce radio : ~11 s (DATAC3)")
                          + ("\n" + tr("AVIF sur une grande photo : choisissez jpg ou original pour une image "
                                        "prête tout de suite.") if slow else ""))
        self._update_comp()

    def _update_comp(self):
        if isinstance(self.tx, HybridJob):
            if self.tx.announce is not None:
                self._set_text(self.btn_comp, f"↻  Répéter l'annonce ({self.tx.announce.estimate_s():.0f} s)")
            else:
                self._set_text(self.btn_comp, "↻  Répéter l'annonce")
            return
        if isinstance(self.tx, engine.DrmTransmission):
            self._set_text(self.btn_comp, f"↻  Réémettre ({self.tx.estimate_s():.0f} s)")
            return
        if self.tx:
            n = self.tx.complement_size()
            self._set_text(self.btn_comp, f"+  Compléter ({n} symboles, {self.tx.estimate_s(n):.0f} s)")
        else:
            self._set_text(self.btn_comp, "+  Compléter")

    def save_wav(self):
        if not self.tx:
            messagebox.showinfo(APP, "Ouvrez d'abord une image.")
            return
        if isinstance(self.tx, HybridJob):
            messagebox.showinfo(APP, "En mode hybride, l'annonce dépend du dépôt sur le serveur : "
                                     "émettez directement.")
            return
        p = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV", "*.wav")],
                                         initialfile=f"hfimage_{self.tx.mode}.wav")
        if not p:
            return
        import wave
        up = audio.Upsampler()
        with wave.open(p, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(audio.FS_CARD)
            for c in self.tx.audio_chunks():
                w.writeframes((up.process(c) * 0.7 * 32767).astype(np.int16).tobytes())
        self.log(f"WAV enregistré (48 kHz) : {p}")

    def _ptt_settings(self):
        return dict(self.radio_cfg)

    def _start_job(self, job, quiet=False):
        """Lance une émission (image, texte, hybride, BSR/ACK, accord, ID).
        quiet=True : déclenchée automatiquement, pas de boîte de dialogue."""
        if self.tx_busy:
            return False
        if is_swl(self.mycall()):
            # station d'écoute : jamais d'émission radio (ni ACK / BSR automatiques) ;
            # les reports partent par Internet (Rx Ok)
            if not quiet:
                messagebox.showinfo(APP, tr("Indicatif d'écouteur (SWL) : HFImage n'émet pas. Vos reports de "
                                            "réception partent par Internet (Rx Ok)."))
            elif not getattr(self, "_swl_noted", False):
                self._swl_noted = True
                self.log(tr("Indicatif d'écouteur (SWL) : pas d'accusé ni de BSR par radio, "
                            "reports par Internet (Rx Ok)."))
            return False
        if not self.v_out.get():
            if not quiet:
                messagebox.showinfo(APP, "Choisissez la sortie audio dans l'onglet Réglages.")
            return False
        ptt = self._ptt_settings()
        if ptt["ptt"] in ("RTS", "DTR") and not (ptt["ptt_port"] or ptt["port"]):
            if not quiet:
                messagebox.showerror(APP, "Choisissez le port COM pour le PTT (Réglages → Poste radio).")
            return False
        if ptt["ptt"] == "CAT" and radio.rig_entry(ptt["rig"])["kind"] == "none":
            if not quiet:
                messagebox.showerror(APP, "PTT par CAT : choisissez d'abord le poste (Réglages → Poste radio).")
            return False
        if not quiet and not self._check_rig_before_tx(ptt):
            return False
        job.setdefault("volume", int(self.v_wavvol.get()))
        job.update(ptt=ptt, level=self.v_lvl.get() / 100.0, dev=self.v_out.get(),
                   cwid=bool(self.v_cwid.get()), call=self.mycall() or "NOCALL")
        was_listening = self.rx_stream is not None
        if was_listening:
            self.toggle_listen(quiet=True)     # semi-duplex : on coupe la réception pendant l'émission
        job["relisten"] = was_listening or (bool(self.v_listen_after.get()) and bool(self.v_in.get())
                                            and job["kind"] in ("image", "text", "hybrid", "wav", "wftext", "file"))
        self.tx_busy = True
        self.stop_tx.clear()
        self.v_state.set("ÉMISSION EN COURS")
        self._set_text(self.gbtn["tx"], "STOP")
        self._btn_color(self.gbtn["tx"], "tx")
        if job["kind"] in ("image", "text", "hybrid", "file"):
            self.show_tab("tx", focus=False)
        threading.Thread(target=self._tx_thread, args=(job,), daemon=True).start()
        return True

    def transmit(self, complement=False, extra=None, tx=None, quiet=False):
        if tx is None and getattr(self, "_prep_waiting", False) and not self.tx_busy:
            self.prepare(sync=True)       # calcul de l'image encore en cours : on le termine maintenant
            self._prep_show_busy(False)
        if tx is None and self.tx is not None and isinstance(self.tx, HybridJob) != bool(self.v_hyb.get()):
            self.tx = None
            self.prepare(sync=True)       # l'image prête était pour l'autre mode
        tx = tx or self.tx
        if not tx or self.tx_busy:
            if not tx and not quiet:
                messagebox.showinfo(APP, "Ouvrez d'abord une image." if self.src_img is None else
                                    "L'image n'est pas prête pour l'émission : voir le message sous l'image "
                                    "(durée trop courte, format…).")
            return False
        if ((self.v_mode.get() == "Auto" or self._robust_choice() is None) and not complement
                and tx is self.tx and not isinstance(tx, (HybridJob, engine.DrmTransmission))
                and (tx.mode != self._tx_mode()
                     or abs(tx.overhead - self._robust_pct(self._tx_mode()) / 100) > 1e-6)):
            # les reports ont changé depuis la préparation : image refaite pour le nouveau mode
            old = tx.mode
            self.prepare(sync=True)
            if self.tx is None:
                return False
            tx = self.tx
            self.log(f"Mode Auto : {old} → {tx.mode}, robustesse {round(tx.overhead * 100)} % "
                     f"({self._tx_mode(explain=True)[1]})")
        job = {"kind": "image", "tx": tx, "complement": complement, "extra": extra}
        if isinstance(tx, engine.DrmTransmission) and complement and self.drm_pending_bsr:
            job.update(drm_bsr=self.drm_pending_bsr["bsr"], drm_need=self.drm_pending_bsr["need"])
        if isinstance(tx, HybridJob):
            job["kind"] = "hybrid"
            job["flash"] = bool(self.v_flash.get())
            if complement and tx.announce is None and not getattr(tx, "drm", False):
                messagebox.showinfo(APP, "Rien à répéter : émettez d'abord l'image.")
                return False
            job["drm_hybrid"] = bool(getattr(tx, "drm", False))
            if complement and job["drm_hybrid"]:
                if getattr(tx, "drm_announce", None) is None:
                    messagebox.showinfo(APP, "Rien à répéter : émettez d'abord l'image.")
                    return False
            elif not complement:
                cfg = self._hyb_cfg()
                if job["drm_hybrid"]:
                    if not cfg["host"]:
                        messagebox.showinfo(APP, "Mode hybride EasyPal : renseignez le serveur FTP "
                                                 "dans l'onglet Réglages.")
                        return False
                elif not cfg["host"] or not cfg["url"]:
                    messagebox.showinfo(APP, "Mode hybride : renseignez le serveur FTP et le lien "
                                             "public dans l'onglet Réglages.")
                    return False
                job["cfg"] = cfg
        else:
            self._remember_sent(tx)
            self.my_ids.add(tx.image_id)
        if not complement:
            # nouvelle image : nouvelle liste Rx Ok (l'id d'une annonce hybride est connu plus tard)
            self._rxok_reset(None if isinstance(tx, HybridJob) else tx.image_id)
            if not isinstance(tx, HybridJob):
                self.last_tx_id = tx.image_id     # pour la carte : qui a reçu NOTRE dernière image
        ok = self._start_job(job, quiet)
        if ok and isinstance(tx, engine.DrmTransmission):
            self.drm_last_tx = tx                 # pour répondre aux BSR des stations EasyPal
        if ok and not complement and not isinstance(tx, HybridJob) and getattr(tx, "msg_text", ""):
            self._msg_sent(tx.image_id, tx.msg_text, tx.mode, with_image=True)
        return ok

    # ------------------------------------------------------------- hybride : dépôt (d'avance ou à l'émission)
    @staticmethod
    def _pre_sig(tx, cfg, drm):
        """Ce qui doit être identique entre le dépôt d'avance et l'émission."""
        return (bool(drm), zlib.crc32(tx.data), len(tx.data), tx.fmt, tx.call,
                cfg.get("host"), cfg.get("port"), cfg.get("user"), cfg.get("dir"), cfg.get("url"))

    def _hyb_upload(self, tx, cfg, drm):
        """Dépose l'image (fil de fond). -> lien public (HFImage) ou (nom, blob) (EasyPal)."""
        prog = lambda f: self.ui(self.pb_tx.configure, {"value": 100 * f})
        keep = int(self.conf.get("hyb_keep", 3) or 0)
        log = lambda m: self.ui(self.log, m)
        if drm:
            if cfg.get("tls"):
                self.ui(self.log, "Hybride EasyPal : les stations EasyPal téléchargent en FTP simple "
                                  "(sans TLS) : vérifiez que votre serveur l'accepte.")
            n = int(self.conf.get("drm_hyb_n", 0)) + 1
            self.conf["drm_hyb_n"] = n
            fname = getattr(tx, "filename", "")
            if fname:                              # fichier : son nom et son extension d'origine
                base, ext = os.path.splitext(fname)
                name = easypal_hybrid.file_name(tx.call, n, base, ext.lstrip(".") or "bin")
            else:
                base = os.path.splitext(os.path.basename(getattr(self, "src_path", "") or "image"))[0]
                name = easypal_hybrid.file_name(tx.call, n, base, imgfmt.ext_for(tx.fmt))
            blob = easypal_hybrid.encrypt(cfg["host"], cfg.get("user", ""), cfg.get("password", ""),
                                          cfg.get("dir", ""))
            self.ui(self.log, f"Hybride EasyPal : dépôt de {len(tx.data)} octets "
                              f"({easypal_hybrid.FILES_DIR}/{name}) sur {cfg['host']}…")
            easypal_hybrid.upload(cfg, name, tx.data, progress=prog)
            # ménage des anciennes images : en tâche de fond, n'attarde pas l'émission
            easypal_hybrid.cleanup_async(cfg, tx.call, keep, log=log)
            self.ui(self.log, "Hybride EasyPal : image déposée.")
            return name, blob
        name = hybrid.remote_name(tx.call, imgfmt.ext_for(tx.fmt), getattr(tx, "filename", ""))
        self.ui(self.log, f"Hybride : dépôt de {len(tx.data)} octets sur {cfg['host']}…")
        hybrid.upload(cfg, name, tx.data, progress=prog)
        # on vérifie que l'image est bien lisible par le lien public AVANT d'émettre
        url, base = hybrid.verify_public(cfg, name, tx.data)
        if base.rstrip("/") != cfg["url"].rstrip("/"):
            self.ui(self._fix_public_url, base)
        self.ui(self.log, f"Hybride : image en ligne et vérifiée : {url}")
        hybrid.cleanup_async(cfg, cfg.get("dir"), hybrid.mine_pattern(tx.call), keep, log=log)
        return url

    def _pre_or_upload(self, tx, cfg, drm):
        """À l'émission : réutilise le dépôt fait d'avance s'il correspond à cette image et à ce
        serveur (l'annonce part tout de suite), sinon dépose maintenant."""
        sig = self._pre_sig(tx, cfg, drm)
        pre = getattr(tx, "pre", None)
        if pre is not None and pre[0] == sig:
            tx.pre = None                       # un dépôt d'avance sert pour une émission
            self.ui(self.log, tr("Hybride : image déjà déposée, l'annonce part tout de suite."))
            return pre[1]
        return self._hyb_upload(tx, cfg, drm)

    def hyb_preupload(self):
        """Bouton « ⇪ Déposer » (mode hybride) : l'image part sur le serveur tout de suite ;
        au moment d'émettre, seule l'annonce radio reste à envoyer (comme l'ancien EasyPal)."""
        tx = self.tx
        if not isinstance(tx, HybridJob) or not self.v_hyb.get():
            messagebox.showinfo(APP, tr("Cochez « Mode hybride » et choisissez d'abord une image."))
            return
        if self.tx_busy or getattr(self, "_preupload_busy", False):
            return
        drm = bool(getattr(tx, "drm", False))
        cfg = self._hyb_cfg()
        if not cfg["host"] or (not drm and not cfg["url"]):
            messagebox.showinfo(APP, "Mode hybride : renseignez le serveur FTP et le lien "
                                     "public dans l'onglet Réglages.")
            return
        sig = self._pre_sig(tx, cfg, drm)
        if tx.pre is not None and tx.pre[0] == sig:
            self.log(tr("Cette image est déjà déposée : prête à émettre."))
            return
        self._preupload_busy = True
        self._set_text(self.btn_pre, "Dépôt…")

        def run():
            try:
                res = self._hyb_upload(tx, cfg, drm)
                tx.pre = (sig, res)
                self.ui(self.log, tr("Image déposée d'avance : à votre tour, « Émettre » envoie "
                                     "directement l'annonce."))
            except Exception as e:
                self.ui(self.log_exc, "Dépôt hybride", e)
                self.ui(messagebox.showerror, APP, tr("Dépôt impossible :") + f"\n{e}")
            finally:
                self.ui(setattr, self, "_preupload_busy", False)
                self.ui(self._set_text, self.btn_pre, "⇪ Déposer")
                self.ui(self.pb_tx.configure, {"value": 0})
        threading.Thread(target=run, daemon=True).start()

    def send_text(self):
        text = self.txt_msg.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo(APP, "Écrivez d'abord le texte à envoyer.")
            return
        call = self.mycall() or "NOCALL"
        mode = self._tx_mode()
        if mode == engine.DRM_MODE:
            # comme EasyPal / QSSTV : un petit fichier .txt (Windows : CRLF, accents en cp1252)
            data = text.replace("\r\n", "\n").replace("\n", "\r\n").encode("cp1252", "replace")
            params = self._drm_params()
            tx = engine.DrmTransmission(data, "txt", call, params,
                                        f"{call}_texte_{time.strftime('%H%M%S', time.gmtime())}")
            self._remember_sent(tx)
            self.my_ids.add(tx.image_id)
            self.log(f"Texte EasyPal : {len(text)} caractères, {hamdrm.describe(params)}, "
                     f"~{_fmt_s(tx.estimate_s())}")
            if self._start_job({"kind": "text", "tx": tx, "complement": False, "extra": None}):
                self.drm_last_tx = tx             # une station EasyPal peut aussi demander un BSR
                self._msg_sent(tx.image_id, text, engine.DRM_MODE)
            return
        tx = engine.Transmission(protocol.pack_text(text), "hft", call, mode, 0.25)
        self._remember_sent(tx)
        self.log(f"Texte : {len(text)} caractères, {mode}, ~{_fmt_s(tx.estimate_s())}")
        self.my_ids.add(tx.image_id)
        if self._start_job({"kind": "text", "tx": tx, "complement": False, "extra": None}):
            self._msg_sent(tx.image_id, text, mode)

    def send_file(self, p=None):
        """Envoi d'un fichier quelconque (texte, PDF, ZIP, ADIF…) par radio, ou par Internet en hybride."""
        if self.tx_busy:
            return
        p = p or filedialog.askopenfilename(title=tr("Fichier à envoyer"), filetypes=[(tr("Tous les fichiers"), "*.*")])
        if not p:
            return
        try:
            with open(p, "rb") as f:
                raw = f.read()
        except OSError as e:
            messagebox.showerror(APP, f"Fichier illisible : {e}")
            return
        name = os.path.basename(p)
        data = protocol.pack_file(name, raw)
        call = self.mycall() or "NOCALL"
        if len(data) >= 16_000_000 and not self.v_hyb.get():
            # par radio seulement : en hybride, aucune limite de taille ni de type (comme EasyPal)
            messagebox.showerror(APP, "Fichier trop gros pour la radio (16 Mo maximum) : utilisez le mode hybride.")
            return
        if self.v_hyb.get():
            cfg = self._hyb_cfg()
            if not cfg["host"] or not cfg["url"]:
                messagebox.showinfo(APP, "Mode hybride : renseignez le serveur FTP et le lien public dans "
                                         "l'onglet Réglages.")
                return
            if not messagebox.askyesno(APP, f"Envoyer {name} ({_fmt_size(len(raw))}) par Internet (mode hybride) ?\n"
                                            f"Seul le lien passe par radio (~11 s)."):
                return
            # 1.25 : le fichier part TEL QUEL, sous son nom d'origine : le lien public s'ouvre
            # directement dans un navigateur (vidéo, son, page web…)
            job = HybridJob(raw, "file", call)
            job.filename = name
            self.log(f"Fichier {name} : {len(raw)} octets, mode hybride (déposé tel quel)")
            return self.transmit(tx=job)
        mode = self._tx_mode()
        if mode == engine.DRM_MODE:
            messagebox.showinfo(APP, "En mode EasyPal, seules les images partent : choisissez un mode DATAC "
                                     "(ou Auto) pour envoyer un fichier.")
            return
        over = self._robust_pct(mode) / 100
        tx = engine.Transmission(data, "file", call, mode, over)
        est = tx.estimate_s()
        msg = (f"{name} : {_fmt_size(len(raw))}" + (f" ({_fmt_size(len(data))} compressé)" if len(data) < len(raw) else "")
               + f"\nMode {mode}, robustesse {round(over * 100)} % : émission d'environ {_fmt_s(est)}.")
        if est > 600:
            msg += "\n\nC'est long : pensez au mode hybride (le fichier passe par Internet, seul le lien par radio)."
        if not messagebox.askyesno(APP, msg + "\n\nÉmettre ?"):
            return
        self._remember_sent(tx)
        self.my_ids.add(tx.image_id)
        self._rxok_reset(tx.image_id)
        self.log(f"Fichier {name} : {len(raw)} octets, {mode}, ~{_fmt_s(est)}")
        self._start_job({"kind": "file", "tx": tx, "complement": False, "extra": None})

    def send_tune(self):
        self._start_job({"kind": "tune"})

    def send_cwid(self):
        self._start_job({"kind": "cw"})

    def send_control(self, payload, what):
        self.log(f"Envoi {what}")
        return self._start_job({"kind": "control", "payload": payload, "what": what}, quiet=True)

    def _rig_status(self, r):
        """-> (texte, en DATA ? True / False / None si inconnu)."""
        f, m = r.freq(), r.mode()
        txt = f"{r.model} : {audio.format_freq(f) + ' kHz' if f else 'fréquence ?'}, mode {m or '?'}"
        if not m:
            return txt, None
        if r.is_data(m):
            return txt + " (DATA : OK).", True
        return txt + " — le poste n'est pas en mode DATA : l'audio USB / arrière risque de ne pas partir.", False

    def _offer_hamlib(self):
        """Hamlib manque pour piloter le poste : proposer de l'installer tout de suite."""
        if getattr(self, "_hamlib_busy", False):
            messagebox.showinfo(APP, tr("Installation de Hamlib en cours… Relancez l'émission dans quelques secondes."))
            return
        if not sys.platform.startswith("win"):
            # Linux : Hamlib vient du système (une commande dans un terminal)
            messagebox.showinfo(APP, tr("Hamlib n'est pas installé : il est nécessaire pour piloter ce poste "
                                        "(PTT par CAT).") + "\n\n" +
                                tr("Sous Linux, installez-le dans un terminal :") + f"\n\n    {radio.LINUX_HAMLIB_HINT}\n\n" +
                                tr("puis relancez l'émission."))
            return
        if not messagebox.askyesno(APP, tr("Hamlib n'est pas installé : il est nécessaire pour piloter ce poste "
                                           "(PTT par CAT).") + "\n\n" +
                                   tr("L'installer maintenant ? Téléchargement depuis le site officiel de Hamlib, "
                                      "quelques secondes.")):
            return
        self._hamlib_busy = True
        self.log(tr("Installation de Hamlib…"))

        def run():
            try:
                d = radio.install_hamlib()
                self.ui(self._hamlib_installed, d, None)
            except Exception as e:
                self.ui(self._hamlib_installed, None, e)
        threading.Thread(target=run, daemon=True).start()

    def _hamlib_installed(self, d, err):
        self._hamlib_busy = False
        if err:
            self.log_exc("Installation de Hamlib", err)
            messagebox.showerror(APP, tr("Installation de Hamlib impossible :") + f"\n{err}\n\n" +
                                 tr("Vérifiez la connexion Internet. Si votre antivirus a bloqué rigctld.exe, "
                                    "ajoutez-le à ses exceptions, puis réessayez."))
            return
        self.log(f"Hamlib {radio.HAMLIB_VERSION} installé dans {d}")
        if radio.find_rigctld():
            messagebox.showinfo(APP, tr("Hamlib est installé. Vous pouvez relancer l'émission."))
        else:
            messagebox.showerror(APP, tr("Hamlib a été installé, mais rigctld.exe a disparu : votre antivirus l'a "
                                         "probablement mis en quarantaine. Restaurez-le ou ajoutez-le à ses "
                                         "exceptions."))

    def _check_rig_before_tx(self, cfg):
        """Avant d'émettre : liaison CAT, mode du poste (réglage « Mode », ou contrôle du mode DATA)."""
        kind = radio.rig_entry(cfg["rig"])["kind"]
        if kind == "none":
            return True
        try:
            r = self._rig_open_now()
            if r is None or not getattr(r, "reads_freq", True):
                return True                          # CAT personnalisé : ni mode ni fréquence à contrôler
            if self.conf.get("data_auto"):
                return True                          # « DATA auto » : passage en DATA au moment d'émettre
            if cfg.get("set_mode") in ("usb", "data"):
                m = r.mode() or ""
                want_data = cfg["set_mode"] == "data"
                if (r.is_data(m) if want_data else m.upper() == "USB"):
                    return True
                ok, msg = r.set_mode(cfg["set_mode"])
                self.log(msg)
                if not ok:
                    return messagebox.askyesno(APP, msg + "\n\nÉmettre quand même ?")
                return True
            # contrôle du mode DATA dès que le CAT est relié, quel que soit le PTT (CAT, RTS,
            # DTR ou VOX) ; sauf « Avant / Micro » : le poste émet alors l'audio sans DATA
            if cfg.get("tx_audio") == "front":
                return True
            txt, ok = self._rig_status(r)
        except radio.HamlibMissing as e:
            self.log(str(e))
            if cfg["ptt"] != "CAT":
                return True                          # PTT sans CAT : on émet quand même
            self._offer_hamlib()
            return False
        except Exception as e:
            self.log_exc("Poste (CAT)", e)
            if cfg["ptt"] != "CAT":
                return True                          # PTT sans CAT : on émet quand même
            messagebox.showerror(APP, f"PTT par CAT impossible :\n{e}")
            return False
        self.log(txt)
        if ok is False:
            act = self.conf.get("data_action", "switch")
            if act not in ("switch", "send"):
                act, remember = self._ask_data_mode(txt)
                if remember and act in ("switch", "send"):
                    self.conf["data_action"] = act
                    if hasattr(self, "v_dataact"):
                        self.v_dataact.set(tr(DATA_ACTIONS[act]))
                    self._save_conf_file()
            if act == "cancel":
                return False
            if act == "send":
                self.log("Réglage « Émettre sans rien dire » : le poste reste dans son mode. Pour le passage "
                         "automatique en DATA : Réglages → « Poste pas en DATA avant d'émettre ».")
            if act == "switch":
                try:
                    ok2, msg = r.set_mode("data")
                except Exception as e:
                    msg, ok2 = f"Passage en DATA impossible : {e}", False
                self.log(msg)
                if not ok2:
                    if cfg["ptt"] != "CAT":
                        # PTT par RTS / DTR / VOX : on n'empêche pas l'émission, on prévient
                        self.log("Poste pas passé en DATA : vérifiez son mode si l'audio ne part pas.")
                        return True
                    return messagebox.askyesno(APP, msg + "\n\nÉmettre quand même ?")
        return True

    def _ask_data_mode(self, txt):
        """Poste pas en DATA : passer en DATA (USB-DATA ou LSB-DATA), émettre quand même ou annuler,
        avec « Ne plus me demander ». -> (choix, mémoriser)."""
        win = tk.Toplevel(self)
        win.title(APP)
        win.transient(self)
        win.resizable(False, False)
        res = {"act": "cancel"}
        f = ttk.Frame(win, padding=14)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text=txt, wraplength=460, justify="left").pack(anchor="w")
        ttk.Label(f, text="Si votre poste est réglé pour émettre l'audio USB sans le mode DATA, choisissez "
                          "« Avant / Micro » comme source audio dans Réglages → Poste radio : ce message ne s'affichera plus.",
                  wraplength=460, justify="left", foreground="#555").pack(anchor="w", pady=(8, 0))
        remember = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Ne plus me demander (faire pareil les prochaines fois)",
                        variable=remember).pack(anchor="w", pady=(10, 0))
        b = ttk.Frame(f)
        b.pack(fill="x", pady=(12, 0))

        def done(act):
            res["act"] = act
            win.destroy()

        first = ttk.Button(b, text="Passer en DATA et émettre", command=lambda: done("switch"))
        first.pack(side="left")
        ttk.Button(b, text="Émettre quand même", command=lambda: done("send")).pack(side="left", padx=6)
        ttk.Button(b, text="Annuler", command=lambda: done("cancel")).pack(side="right")
        win.protocol("WM_DELETE_WINDOW", lambda: done("cancel"))
        self._translate_ui(win)
        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - win.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - win.winfo_height()) // 3
        win.geometry(f"+{max(0, x)}+{max(0, y)}")
        first.focus_set()
        win.grab_set()
        self.wait_window(win)
        return res["act"], bool(remember.get())

    def _save_conf_file(self):
        try:
            with open(CONF_PATH, "w", encoding="utf-8") as f:
                json.dump(self.conf, f, indent=1)
        except Exception:
            pass

    def _job_audio(self, job):
        """-> (fabrique de morceaux 8 kHz, durée s, mode, description)."""
        kind = job["kind"]
        if kind == "tune":
            a = engine.tune_audio(10.0)
            return (lambda: iter([a])), len(a) / 8000, "", "accord (porteuse 1500 Hz)"
        if kind == "cw":
            a = engine.cw_audio("DE " + job["call"])
            return (lambda: iter([a])), len(a) / 8000, "", "identification morse"
        if kind == "wav":
            a = wavtext.normalize(engine.read_wav_8k(job["path"]), job["volume"])
            return (lambda: iter([a])), len(a) / 8000, "", f"fichier {os.path.basename(job['path'])}"
        if kind == "wftext":
            a = wavtext.synth(job["bitmap"], job["volume"])
            return (lambda: iter([a])), len(a) / 8000, "", "texte waterfall"
        if kind == "control":
            ct = engine.ControlTransmission(job["payload"])
            fr = ct.frames()
            return (lambda: ct.modem.modulate_iter(fr)), ct.estimate_s(), "DATAC0", job["what"]
        if kind == "drm_bsr":
            a = engine.drm_bsr_audio8k(job["params"])
            if a is None:
                raise RuntimeError("aucune image EasyPal incomplète à demander")
            return (lambda: iter([a])), len(a) / 8000, engine.DRM_MODE, job["what"]
        tx = job["tx"]
        drm_audio = None                  # mode EasyPal : signal HamDRM déjà fabriqué
        if isinstance(tx, engine.DrmTransmission):
            bsr = job.get("drm_bsr")
            drm_audio = tx.audio8k(bsr)
            if drm_audio is None:
                raise RuntimeError("le BSR reçu ne correspond plus à la dernière image émise")
            dur, mode = len(drm_audio) / 8000, engine.DRM_MODE
            what = (f"FIX EasyPal, {job.get('drm_need', '?')} segments" if bsr else
                    f"{'texte ' if tx.fmt == 'txt' else ''}EasyPal {hamdrm.describe(tx.params)}, "
                    f"{len(tx.data)} octets")
            modem = frames = None
        elif kind == "hybrid" and job.get("drm_hybrid"):
            # hybride façon EasyPal : image dans HybridFiles1, annonce « de_… » en HamDRM
            if not job["complement"] or getattr(tx, "drm_announce", None) is None:
                cfg = job["cfg"]
                tx.drm_announce = self._pre_or_upload(tx, cfg, drm=True)
                # même identifiant que chez les stations qui la téléchargent : Rx Ok
                iid = zlib.crc32(tx.data + b"hamdrm") & 0xFFFF
                self.my_ids.add(iid)
                self.ui(self._rxok_show, iid)
                self.ui(setattr, self, "last_tx_id", iid)
            name, blob = tx.drm_announce
            stem, ext = os.path.splitext(name)
            drm_audio = engine.drm_to_8k(hamdrm.tx_file(blob, stem, ext.lstrip("."),
                                                         easypal_hybrid_params(cfg_call=tx.call)))
            dur, mode = len(drm_audio) / 8000, engine.DRM_MODE
            what = f"annonce hybride EasyPal {name}"
            modem = frames = None
        elif kind == "hybrid":
            want_flash = bool(job.get("flash"))
            if want_flash and len(tx.data) >= 1 << 24:
                self.ui(self.log, "Hybride éclair : fichier de plus de 16 Mo, annonce normale à la place.")
                want_flash = False
            if want_flash and not (self.net is not None and self.net.connected):
                self.ui(self.log, "Hybride éclair : serveur des stations en ligne non connecté, "
                                  "annonce normale (DATAC3) à la place.")
                want_flash = False
            if not job["complement"]:
                cfg = job["cfg"]
                url = self._pre_or_upload(tx, cfg, drm=False)
                tx.announce = engine.HybridTransmission(tx.data, tx.fmt, tx.call, url, flash=want_flash)
                self.my_ids.add(tx.announce.image_id)
                self.ui(self._rxok_show, tx.announce.image_id)
                self.ui(setattr, self, "last_tx_id", tx.announce.image_id)
            elif tx.announce.flash != want_flash:      # « Répéter l'annonce » après avoir changé d'avis
                tx.announce = engine.HybridTransmission(tx.data, tx.fmt, tx.call, tx.announce.url, flash=want_flash)
            if tx.announce.flash:
                # le lien part par Internet juste avant la trame radio qui porte l'empreinte
                self.net.publish_flash(tx.announce.key, tx.call, tx.announce.url, len(tx.data),
                                       zlib.crc32(tx.data), tx.fmt, tx.announce.image_id)
                self.ui(self.log, f"Hybride éclair : lien publié (empreinte {tx.announce.key}).")
            tx.mode = tx.announce.mode
            modem, frames, mode = tx.announce, tx.announce.frames(), tx.announce.mode
            dur, what = tx.announce.estimate_s(), f"annonce hybride {mode}"
        else:
            extra = job.get("extra")
            if job["complement"] and extra is None:
                extra = tx.complement_size()
            dur = tx.estimate_s(extra)
            frames, modem, mode = tx.frames(extra), tx.modem, tx.mode
            if kind == "text":
                what = f"texte {mode}"
            elif extra:
                what = f"FIX {mode}, {extra} symboles"
            else:
                what = f"{mode}, {len(tx.data)} octets" + (" + aperçu" if tx.preview else "")
        cw = engine.cw_audio("DE " + job["call"]) if job.get("cwid") else None
        if cw is not None:
            dur += len(cw) / 8000
        # comme EasyPal : begin.wav avant l'émission, end.wav après (sauf FIX / compléments)
        begin = end = None
        if not job.get("complement"):
            begin, end = self._begin_end(job.get("volume", 5))
            for x in (begin, end):
                if x is not None:
                    dur += len(x) / 8000
            if begin is not None:
                what += " + begin.wav"
            if end is not None:
                what += " + end.wav"

        def chunks():
            if begin is not None:
                yield begin
            if drm_audio is not None:
                yield drm_audio
            else:
                yield from modem.modulate_iter(frames)
            if end is not None:
                yield end
            if cw is not None:
                yield cw
        return chunks, dur, mode, what

    def _begin_end(self, volume):
        out = []
        for name in ("begin.wav", "end.wav"):
            p = os.path.join(wavtext.wav_dir(DEFAULT_OUT), name)
            try:
                out.append(wavtext.normalize(engine.read_wav_8k(p), volume) if os.path.exists(p) else None)
            except Exception as e:
                self.ui(self.log, f"{name} illisible : {e}")
                out.append(None)
        return out

    def _tx_thread(self, job):
        ptt = rig = data_back = None
        try:
            make_chunks, dur, mode, what = self._job_audio(job)
            if mode:
                self.ui(self.wf.mark_mode, mode)
            self.ui(self.log, f"Émission {what} : {_fmt_s(dur)}")
            self.ui(self._panel_tx, job, mode)
            cfg = job["ptt"]
            rig = None
            if cfg["ptt"] == "CAT":
                rig = self._rig_open()
            elif radio.rig_entry(cfg["rig"])["kind"] != "none":
                # PTT sans CAT : la liaison si elle est ouverte, sans attendre un poste qui ne répond pas
                r = self.rig
                rig = r if r is not None and r._sig == radio.cat_signature(cfg) else None
            data_back = self._data_auto_on(rig, job)
            if cfg["ptt"] != "VOX":
                ptt = radio.Ptt(cfg, rig)
                ptt.tx()
                time.sleep(0.2)
            rows, shown = [], [0]
            rm = RowMaker()

            def on_chunk(c):                         # waterfall de notre propre signal
                rows.extend(rm.rows_from(c))

            def progress(t):
                self.ui(self.pb_tx.configure, {"value": min(100, 100 * t / max(dur, 0.1))})
                n = min(len(rows), int(t * 10))
                if n > shown[0]:
                    self.ui(self.wf.add_rows, rows[shown[0]:n])
                    shown[0] = n

            def player(S, d):
                rows.clear(); shown[0] = 0
                return audio.play_8k(S, d, make_chunks(), job["level"], self.stop_tx,
                                     progress, lambda m: self.ui(self.log, m), on_chunk)

            if not self._play_fallback(player, job["dev"]):
                self.ui(self.log, "Émission interrompue.")
            elif job["kind"] in ("image", "hybrid") and not job.get("complement"):
                self.ui(self._gallery_sent, job, mode)
        except Exception as e:
            self.ui(self.log_exc, "Émission", e)
            if job["kind"] != "control":
                self.ui(messagebox.showerror, APP, f"Émission impossible :\n{e}\n\n"
                                                  "Le détail est dans le journal (Réglages → Ouvrir le journal).")
        finally:
            if ptt:
                try:
                    err = ptt.close()
                except Exception as e:
                    err = e
                if err:
                    self.ui(self.log_exc, "PTT (retour en réception)", err)
                    self.ui(messagebox.showwarning, APP, tr("Le retour en réception a échoué : le poste est "
                                                            "peut-être resté en émission. Vérifiez-le.")
                            + f"\n\n{err}")
            self._data_auto_off(rig, data_back)
            self.ui(self._tx_done, job["relisten"])

    # ------------------------------------------------------------- « DATA auto »
    def _data_auto_on(self, rig, job):
        """Bouton « DATA auto » : LSB / USB -> LSB-DATA / USB-DATA juste avant d'émettre.
        -> bande latérale à remettre après l'émission (« LSB » / « USB »), ou None."""
        if not self.conf.get("data_auto") or rig is None or not getattr(rig, "reads_freq", True):
            return None
        try:
            m = (rig.mode() or "").upper().replace(" ", "")
            if not m or rig.is_data(m):
                return None                          # déjà en DATA (ou mode inconnu) : rien à faire
            if m not in ("LSB", "USB"):
                self.ui(self.log, tr("DATA auto : le poste est en") + f" {m}, " + tr("mode laissé tel quel."))
                return None
            ok, msg = rig.set_mode("data")
            self.ui(self.log, "DATA auto : " + msg)
            return m                                 # commande partie : retour en LSB / USB après, toujours
        except Exception as e:
            self.ui(self.log_exc, "DATA auto", e)
            return None

    def _data_auto_off(self, rig, side):
        """Après l'émission : retour en LSB / USB (phonie)."""
        if not side or rig is None:
            return
        try:
            rig.set_voice(side)
            self.ui(self.log, "DATA auto : " + tr("retour en") + f" {side}.")
        except Exception as e:
            self.ui(self.log_exc, "DATA auto (retour en " + side + ")", e)
        self._rig_kick.set()

    def _data_auto_toggle(self):
        self.conf["data_auto"] = not self.conf.get("data_auto")
        self._save_conf_file()
        self._data_auto_paint()
        if self.conf["data_auto"]:
            self.log(tr("DATA auto : le poste passe en LSB-DATA / USB-DATA pour émettre, puis revient en "
                        "LSB / USB à la fin."))
        else:
            self.log(tr("DATA auto : arrêté."))

    def _data_auto_paint(self):
        b = getattr(self, "bt_dauto", None)
        if b is not None:
            self._btn_color(b, "on" if self.conf.get("data_auto") else "off")

    def _play_fallback(self, player, dev_label):
        """Joue sur la sortie choisie ; si elle échoue ou reste muette, essaie le
        même périphérique par les autres interfaces Windows (MME, WASAPI,
        DirectSound) et garde celle qui marche."""
        S = sd()
        dev = self._dev_index(dev_label, output=True)
        tried = list(dict.fromkeys([dev] + audio.same_device_other_apis(S, dev, output=True)))
        errors = []
        for k, d in enumerate(tried):
            try:
                ok = player(S, d)
                if k > 0 and audio.device_label(S, d) != audio.device_label(S, dev):
                    label = f"{d}: {audio.device_label(S, d)}"
                    self.ui(self.log, f"La sortie « {dev_label} » ne fonctionne pas ; "
                                      f"« {label} » utilisée à la place (réglage mis à jour).")
                    self.ui(self._set_out_dev, label)
                return ok
            except Exception as e:
                errors.append(f"{audio.device_label(S, d)} : {e}")
                self.ui(self.log_exc, f"Sortie {audio.device_label(S, d)}", e)
        raise RuntimeError("aucune interface audio ne fonctionne pour cette sortie :\n- "
                           + "\n- ".join(errors))

    def _set_out_dev(self, label):
        self.v_out.set(label)
        self.save_conf(quiet=True)

    def _tx_done(self, relisten):
        self.tx_busy = False
        self._set_text(self.gbtn["tx"], "ÉMISSION")
        self._btn_color(self.gbtn["tx"], "off")
        self.pb_tx.configure(value=0)
        self.v_state.set("Réception arrêtée")
        self.log("Fin d'émission.")
        self.panel.set_cell("Position", "TX", tr("terminé"))
        if self.tx is None or isinstance(self.tx, HybridJob) != bool(self.v_hyb.get()):
            self.tx = None                # « hybride » coché / décoché pendant l'émission
            self.prepare()
        self._update_comp()
        if relisten and self.rx_stream is None and self.v_in.get():
            self.toggle_listen(quiet=True)

    def test_audio(self):
        """Tonalité 1 kHz de 2 s sur la sortie choisie (sans PTT)."""
        if not self.v_out.get():
            messagebox.showinfo(APP, "Choisissez d'abord la sortie audio.")
            return
        if self.tx_busy:
            return
        label = self.v_out.get()
        sig = audio.tone() * (self.v_lvl.get() / 100.0) / 0.3 * 0.5
        self.stop_tx.clear()

        def run():
            try:
                self._play_fallback(lambda S, d: audio.play(S, d, sig, self.stop_tx,
                                                            log=lambda m: self.ui(self.log, m)), label)
                self.ui(self.log, "Tonalité de test terminée.")
            except Exception as e:
                self.ui(messagebox.showerror, APP, f"Sortie audio impossible :\n{e}")

        threading.Thread(target=run, daemon=True).start()

    def test_ptt(self):
        cfg = self._ptt_settings()
        if cfg["ptt"] == "VOX":
            messagebox.showinfo(APP, "PTT en VOX : rien à tester ici, utilisez « Tester la sortie ».")
            return
        if self.tx_busy:
            return
        try:
            rig = self._rig_open() if radio.rig_entry(cfg["rig"])["kind"] != "none" else None
            p = radio.Ptt(cfg, rig)
            p.tx()
            self.after(1000, p.close)
            self.log(f"PTT {cfg['ptt']} : émission 1 s.")
        except Exception as e:
            self.log_exc("PTT", e)
            messagebox.showerror(APP, f"PTT impossible :\n{e}")

    def check_rig(self):
        cfg = self._ptt_settings()
        if radio.rig_entry(cfg["rig"])["kind"] == "none":
            messagebox.showinfo(APP, "Aucun poste choisi (pas de CAT) : Réglages → Poste radio.")
            return
        try:
            r = self._rig_open()
            txt, ok = self._rig_status(r)
        except Exception as e:
            self.log_exc("Vérification du poste", e)
            messagebox.showerror(APP, str(e))
            return
        if ok is False and not (cfg["ptt"] == "CAT" and cfg.get("tx_audio") == "rear"):
            ok = None                                # DATA pas indispensable avec ces réglages
            txt = txt.split(" — ")[0] + "."
        self.log(txt)
        (messagebox.showwarning if ok is False else messagebox.showinfo)(APP, txt)

    # ------------------------------------------------------------- réception
    def _new_engine(self):
        call = self.mycall() or "NOCALL"
        eng = engine.RxEngine(call, self.v_folder.get(),
                              on_image=lambda *a: self.ui(self._got_image, *a),
                              on_status=lambda st: self.ui(self._rx_status, st),
                              on_ident=lambda *a: self.ui(self._got_ident, *a))
        eng.on_hybrid = lambda h, m: self.ui(self._hybrid_announce, eng, h, m)
        eng.qrm = bool(self.conf.get("qrm_filter", True))
        eng.on_control = lambda *a: self.ui(self._on_control, *a)
        eng.on_drm_bsr = lambda b, call, snr: self.ui(self._drm_bsr_heard, b, call, snr)
        eng.on_drm_hybrid = lambda h: self.ui(self._drm_hybrid_announce, eng, h)
        return eng

    def _full_call(self, call):
        """Les trames radio portent 8 caractères d'indicatif : « PA0041SWL » arrive en « PA0041SW ».
        S'il n'y a qu'une station en ligne (ou entendue) dont l'indicatif complet commence ainsi,
        on reprend son indicatif complet."""
        c = str(call or "").strip().upper()
        if len(c) != 8:
            return call
        found = {str(d.get("call") or "").upper() for d in self.online.values()}
        found |= {str(k).upper() for k in getattr(self, "heard", {}) or {}}
        longer = {f for f in found if len(f) > 8 and f.startswith(c)}
        return longer.pop() if len(longer) == 1 else call

    def _on_control(self, kind, iid, call, need, snr):
        """BSR (NACK), ACK ou présence (QRV) entendu (chaque trame est émise 2 fois :
        on dédoublonne)."""
        call = self._full_call(call)
        key, now = (kind, iid, call), time.time()
        if now - self.ctl_seen.get(key, 0) < 8:
            return
        self.ctl_seen[key] = now
        if kind == "QRV":
            loc = need or ""
            self._heard(call, snr, "Présence (QRV)", loc)
            self.station_event(call, "Présence (QRV)", "DATAC0", snr, loc)
            self.log(f"{call} est à l'écoute avec HFImage" + (f" ({loc})" if loc else "") + ".")
            return
        mine = self.sent_images.get(iid) or iid in self.my_ids
        if kind == "ACK":
            rep, aloc = need if isinstance(need, tuple) else (need, "")
            self._heard(call, snr, "ACK : image reçue", aloc)
            self.station_event(call, "ACK : image reçue" if mine else "ACK (autre QSO)", "DATAC0", snr,
                               f"image {iid:04X}" + ("" if rep is None else f", report {rep:+d} dB"))
            self._rxok_add(call, rep, iid)
            if iid in self.sent_msgs:
                self._msg_ack(iid, call, rep, "radio")
            elif mine:
                self.log(f"{call} confirme la réception de l'image"
                         + ("." if rep is None else f" (report {rep:+d} dB)."))
            return
        self._heard(call, snr, "BSR")
        self.station_event(call, f"BSR : {need} symboles" if mine else "BSR (autre QSO)", "DATAC0", snr,
                           f"image {iid:04X}")
        if not self.sent_images.get(iid):
            return
        self.log(f"BSR de {call} : il manque des symboles ({need} demandés).")
        p = self.pending_fix.setdefault(iid, {"need": 0, "calls": set(), "t": time.time(), "rounds": 0})
        p["need"] = max(p["need"], need)
        p["calls"].add(call)
        self._set_fix_text(f"FIX ({p['need']} symboles)")

    def _drm_bsr_heard(self, bsr, call, snr):
        """BSR reçu en mode EasyPal (d'EasyPal, de QSSTV ou de HFImage)."""
        n = hamdrm.bsr_check(bsr) if self.drm_last_tx is not None else -1
        self._heard(call, snr, "BSR EasyPal")
        if n < 0:
            self.station_event(call, "BSR EasyPal (autre QSO)", engine.DRM_MODE, snr, "")
            return
        p = self.drm_pending_bsr
        if p is None or p["bsr"] != bsr:
            self.drm_pending_bsr = p = {"bsr": bsr, "need": n, "calls": set(), "t": time.time(),
                                        "rounds": (p or {}).get("rounds", 0)}
        p["calls"].add(call)
        self.station_event(call, f"BSR EasyPal : {n} segments", engine.DRM_MODE, snr, "")
        self.log(f"BSR EasyPal de {call} : {n} segments demandés.")
        self._set_fix_text(f"FIX ({n} segments)")

    def _do_drm_fix(self, quiet=False):
        p, tx = self.drm_pending_bsr, self.drm_last_tx
        if not p or tx is None:
            return False
        if self.transmit(complement=True, tx=tx, quiet=quiet):
            p["rounds"] += 1
            self.drm_pending_bsr = None
            self._set_fix_text("FIX")
            self.station_event(", ".join(sorted(p["calls"])), f"FIX EasyPal envoyé : {p['need']} segments",
                               engine.DRM_MODE, None, "")
            return True
        return False

    def _fix_due(self):
        """FIX automatique : quelques secondes après le premier BSR (pour regrouper
        les demandes de plusieurs stations), on envoie le maximum demandé."""
        now = time.time()
        p = self.drm_pending_bsr
        if (p and now - p["t"] >= 5 and not self.tx_busy and self.v_fix_auto.get()
                and p["rounds"] < 5):
            self._do_drm_fix(quiet=True)
        for iid, p in list(self.pending_fix.items()):
            if p["need"] <= 0 or now - p["t"] < 5 or self.tx_busy:
                continue
            if not self.v_fix_auto.get() or p["rounds"] >= 5:
                continue
            self._do_fix(iid, quiet=True)

    def _do_fix(self, iid, quiet=False):
        p = self.pending_fix.get(iid)
        tx = self.sent_images.get(iid)
        if not tx or not p or p["need"] <= 0:
            return False
        need = p["need"]
        if self.transmit(complement=True, extra=need, tx=tx, quiet=quiet):
            p["rounds"] += 1
            p["need"] = 0
            self._set_fix_text("FIX")
            self.station_event(", ".join(sorted(p["calls"])), f"FIX envoyé : {need} symboles",
                               tx.mode, None, f"image {iid:04X}")
            return True
        return False

    def send_fix(self):
        """Bouton FIX : répond aux BSR en attente, sinon complément standard."""
        if self.drm_pending_bsr and self._do_drm_fix():
            return
        for iid, p in self.pending_fix.items():
            if p["need"] > 0 and self._do_fix(iid):
                return
        if self.tx and not isinstance(self.tx, HybridJob):
            self.transmit(complement=True)

    def _bsr_check(self):
        """Réception : image incomplète alors que l'émetteur a fini -> BSR ;
        image complète -> ACK. On attend 2 s de silence, plus un délai aléatoire
        pour que plusieurs stations ne répondent pas en même temps."""
        eng = self.rx_engine
        if eng is None or self.rx_stream is None or self.tx_busy:
            return
        now = time.time()
        inc = eng.drm_incomplete()
        if inc:
            got, K, call = inc
            key = (K, call, round(eng.drm_t))
            if self._drm_hint != key:
                self._drm_hint = key
                self.log(f"Image EasyPal de {call} incomplète ({got}/{K} segments) : "
                         "cliquez sur BSR pour demander les segments manquants.")
        for iid, got, K, end, age, mode, call in eng.incomplete():
            st = self.bsr_state.setdefault(iid, {"end": 0, "n": 0, "at": None})
            finished = (end > st["end"] and age > 1.5) or (age > 30 and st["n"] == 0 and got > 0)
            if not finished:
                continue
            if self.v_bsr_auto.get() and st["n"] < 3:
                if st["at"] is None:
                    st["at"] = now + random.uniform(0.5, 4.0)
                if now >= st["at"]:
                    st["end"], st["n"], st["at"] = end, st["n"] + 1, None
                    self.send_control(eng.rcv.nack(iid), f"BSR à {call} ({got}/{K} symboles)")
                    self.station_event(call, f"BSR envoyé : {got}/{K}", mode, None, f"image {iid:04X}")
                    return
            elif st["n"] == 0 and st["end"] != end:
                st["end"] = end
                self.bsr_target = iid
                self.log(f"Image de {call} incomplète ({got}/{K}) : cliquez sur BSR pour demander la suite.")
        for iid, info in list(self.ack_pending.items()):
            act = eng.activity.get(iid, {"end": 0, "t": 0})
            # l'émetteur a fini quand sa trame d'identification de fin (HDR) est arrivée
            # APRÈS que l'image s'est complétée ; à défaut, 8 s sans aucune trame
            # (plus long qu'une trame, même en DATAC4)
            if now < info.get("wait_until", 0):
                continue
            if (act["end"] > info.get("end_at", 0) and now - act["t"] > 1.5) or now - act["t"] > 8:
                if info.get("at") is None:
                    info["at"] = now + random.uniform(0.5, 4.0)
                if now >= info["at"]:
                    del self.ack_pending[iid]
                    self.send_control(eng.rcv.ack(iid, self.snr_by_id.get(iid)), f"ACK à {info['call']}")
                    return

    def send_bsr_manual(self):
        eng = self.rx_engine
        if eng is None:
            messagebox.showinfo(APP, "Aucune image en cours de réception.")
            return
        inc = eng.incomplete()
        drm = eng.drm_incomplete(wait=0)
        if drm and (not inc or min(r[4] for r in inc) > time.time() - eng.drm_t):
            got, K, call = drm                 # la plus récente est une image EasyPal
            self._start_job({"kind": "drm_bsr", "params": self._drm_params(),
                             "what": f"BSR EasyPal à {call} ({got}/{K} segments)"})
            self.station_event(call, f"BSR EasyPal envoyé : {got}/{K}", engine.DRM_MODE, None, "")
            return
        if not inc:
            messagebox.showinfo(APP, "Aucune image incomplète.")
            return
        iid, got, K, end, age, mode, call = max(inc, key=lambda r: -r[4])
        if self.send_control(eng.rcv.nack(iid), f"BSR à {call} ({got}/{K} symboles)"):
            self.station_event(call, f"BSR envoyé : {got}/{K}", mode, None, f"image {iid:04X}")

    def _drm_hybrid_announce(self, eng, h):
        """Annonce hybride EasyPal / QSSTV : l'image est à télécharger par FTP."""
        key = (h["call"], h["name"])
        if key in self._drm_hyb_seen:
            return
        self._drm_hyb_seen.add(key)
        where = easypal_hybrid.public_label(h, h["name"])
        self._heard(h["call"], h.get("snr"), "Annonce hybride EasyPal", hyb=True)
        self.station_event(h["call"], "Annonce hybride EasyPal", engine.DRM_MODE, h.get("snr"), h["name"])
        self.log(f"Annonce hybride EasyPal de {h['call']} : {where}")
        if not self.v_hauto.get():
            self.log("Téléchargement automatique désactivé (Réglages).")
            return

        def run():
            try:
                data = easypal_hybrid.download(h, h["name"], log=lambda m: self.ui(self.log, m))
                hyb = {"id": zlib.crc32(data + b"hamdrm") & 0xFFFF, "call": h["call"], "crc": zlib.crc32(data),
                       "fmt": protocol.detect_format(data), "url": where, "snr": h.get("snr")}
                eng.save_hybrid(hyb, data, engine.DRM_MODE)
            except Exception as e:
                self.ui(self.log_exc, "Téléchargement hybride EasyPal", e)

        threading.Thread(target=run, daemon=True).start()

    def _flash_announce(self, eng, fl, mode):
        """Hybride éclair : la trame radio porte l'empreinte de l'image ; le lien arrive par
        Internet (serveur des stations en ligne). L'image doit avoir exactement cette empreinte."""
        snr = eng.last.get("snr")
        self.log(f"Annonce hybride éclair ({mode}) : empreinte {fl['key']}, {fl['size']} octets")
        if not self.v_hauto.get():
            self.log("Téléchargement automatique désactivé (Réglages).")
            return
        if self.net is None:
            self.log("Hybride éclair : activez « Stations en ligne » (Réglages) pour recevoir le lien.")
            return
        net = self.net

        def run():
            try:
                rec = None
                for _ in range(60):                      # le lien arrive en principe avant la trame
                    rec = net.get_flash(fl["key"])
                    if rec is not None:
                        break
                    time.sleep(0.5)
                if rec is None:
                    raise RuntimeError("lien non reçu par Internet dans les 30 s")
                if rec["size"] != fl["size"]:
                    raise RuntimeError("le lien reçu par Internet ne correspond pas à l'annonce radio")
                self.ui(self._heard, rec["call"], snr, "Annonce hybride éclair")
                self.ui(self._rx_call, rec["call"])
                self.ui(self.log, f"Hybride éclair de {rec['call']} : {rec['url']}")
                data = hybrid.download_retry(rec["url"], fl["size"], rec["crc"],
                                             log=lambda m: self.ui(self.log, m))
                if protocol.flash_key(data) != fl["key"]:
                    raise RuntimeError("image refusée : son empreinte n'est pas celle annoncée par radio")
                hyb = {"id": fl["id"], "call": rec["call"], "crc": rec["crc"], "fmt": fl["fmt"],
                       "url": rec["url"], "size": fl["size"]}
                eng.save_hybrid(hyb, data, mode)
            except Exception as e:
                self.ui(self.log_exc, "Hybride éclair", e)

        threading.Thread(target=run, daemon=True).start()

    def _hybrid_announce(self, eng, hyb, mode):
        if hyb.get("call"):
            hyb["call"] = self._full_call(hyb["call"])
        if hyb.get("flash"):
            return self._flash_announce(eng, hyb, mode)
        self._heard(hyb.get("call"), eng.last.get("snr"), "Annonce hybride")
        self.log(f"Annonce hybride de {hyb['call']} ({mode}) : {hyb['url']} "
                 f"({hyb['size']} octets)")
        if not self.v_hauto.get():
            self.log("Téléchargement automatique désactivé (Réglages).")
            return

        def run():
            try:
                data = hybrid.download_retry(hyb["url"], hyb["size"], hyb["crc"],
                                             log=lambda m: self.ui(self.log, m))
                eng.save_hybrid(hyb, data, mode)
            except Exception as e:
                self.ui(self.log_exc, "Téléchargement hybride", e)

        threading.Thread(target=run, daemon=True).start()

    def toggle_listen(self, quiet=False):
        if self.rx_stream:
            self.rx_stream.stop()
            self.rx_stream.close()
            self.rx_stream = None
            self.audio_q.put(None)
            self._set_text(self.btn_listen, "Écoute")
            self._btn_on("ecoute", False)
            self.v_state.set("Réception arrêtée")
            if not quiet:
                self.log("Réception arrêtée.")
            return
        if not self.v_in.get():
            if not quiet:
                messagebox.showinfo(APP, "Choisissez l'entrée audio dans l'onglet Réglages.")
            return
        if self.rx_engine is None:
            self.rx_engine = self._new_engine()
        ds = audio.Downsampler()
        wf_rows = RowMaker()

        def cb(indata, frames, t, status):
            self.audio_q.put(indata[:, 0].copy())

        S = sd()
        dev0 = self._dev_index(self.v_in.get(), output=False)
        errors, rs = [], None
        for k, dev in enumerate([dev0] + audio.same_device_other_apis(S, dev0, output=False)):
            try:
                fs, ch = audio.pick_rate(S, dev, output=False)
                rs = audio.LinearResampler(fs, audio.FS_CARD)
                self.rx_stream = S.InputStream(device=dev, channels=ch, samplerate=fs,
                                               dtype="float32", blocksize=fs // 10, callback=cb)
                self.rx_stream.start()
                self.log(f"Entrée : {audio.device_label(S, dev)}, {fs} Hz, {ch} voie(s)")
                if k > 0:
                    self.v_in.set(f"{dev}: {audio.device_label(S, dev)}")
                    self.log("L'entrée choisie ne s'ouvrait pas : autre interface utilisée "
                             "(réglage mis à jour).")
                    self.save_conf(quiet=True)
                break
            except Exception as e:
                self.rx_stream = None
                errors.append(f"{audio.device_label(S, dev)} : {e}")
                self.log_exc(f"Entrée {audio.device_label(S, dev)}", e)
        if self.rx_stream is None:
            if quiet:
                self.log("Entrée audio impossible : " + "; ".join(errors))
                return
            messagebox.showerror(APP, "Entrée audio impossible :\n- " + "\n- ".join(errors))
            return

        def worker():
            while True:
                x = self.audio_q.get()
                if x is None:
                    break
                lvl = float(np.sqrt(np.mean(x ** 2)))
                self.rx_dbfs = 20 * np.log10(max(lvl, 1e-6)) + 3.0   # crête d'un sinus = RMS + 3 dB
                x48 = rs.process(x)
                y = ds.process(x48)
                self.ring.append(y)
                self.ring_len += len(y)
                while self.ring_len > RING_S * 8000:
                    self.ring_len -= len(self.ring.pop(0))
                w = self.rec_wav
                if w is not None:
                    try:
                        w.writeframes(y.astype(np.int16).tobytes())
                    except Exception:
                        pass
                rows = wf_rows.rows_from(y)
                if rows:
                    self.ui(self.wf.add_rows, rows)
                self.rx_engine.process(y)
                try:
                    self.rx_engine.process48(x48)          # mode EasyPal (HamDRM)
                except Exception as e:
                    self.ui(self.log_exc, "Réception EasyPal", e)

        threading.Thread(target=worker, daemon=True).start()
        self._set_text(self.btn_listen, "Écoute ON")
        self._btn_on("ecoute", True)
        self.v_state.set("RÉCEPTION")
        if not quiet:
            self.log("Écoute démarrée (DATAC1X / DATAC1 / DATAC3 / DATAC4 + BSR/ACK en DATAC0"
                     + (" + EasyPal)." if hamdrm.AVAILABLE else ")."))

    def analyze_wav(self, path=None):
        """Diagnostic d'une réception enregistrée (niveau, QRM, trames, SNR, mode conseillé)."""
        if path is None:
            last = getattr(self, "rec_path", None)
            path = filedialog.askopenfilename(
                filetypes=[("WAV", "*.wav"), ("Tous", "*.*")],
                initialdir=os.path.dirname(last) if last else self.v_folder.get())
        if path:
            import anadlg
            anadlg.AnalyzerWindow(self, path)

    def decode_wav(self, p=None, analyze=True):
        """Fichiers → Décoder et analyser un fichier WAV : les images du fichier arrivent comme en
        réception, et la fenêtre d'analyse (niveau, QRM, trames, SNR, mode conseillé) s'ouvre."""
        if p is None:
            last = getattr(self, "rec_path", None)
            p = filedialog.askopenfilename(filetypes=[("WAV", "*.wav"), ("Tous", "*.*")],
                                           initialdir=os.path.dirname(last) if last else self.v_folder.get())
        if not p:
            return
        if analyze:
            self.analyze_wav(p)
        self.log(f"Décodage de {os.path.basename(p)}…")
        eng = self._new_engine()
        eng.on_image = lambda *a: self.ui(self._got_image, *a, True)      # fichier : mode d'émission gardé
        eng.on_status = lambda st: self.ui(self._rx_status, dict(st, from_file=True))

        def run():
            try:
                x = engine.read_wav_8k(p)
                rm = RowMaker()
                step = 8000
                for i in range(0, len(x), step):
                    rows = rm.rows_from(x[i:i + step])
                    if rows:
                        self.ui(self.wf.add_rows, rows)
                    eng.process(x[i:i + step])
                eng.process(np.zeros(8000 * 3, np.int16))   # vide les démodulateurs
                if hamdrm.AVAILABLE:                         # puis le mode EasyPal, à 48 kHz
                    engine.drm_claim(eng)
                    try:
                        x48 = engine.read_wav_48k(p)
                        x48 = np.concatenate([x48, np.zeros(48000 * 3, np.float32)])
                        for i in range(0, len(x48), 4800):
                            eng.process48(x48[i:i + 4800])
                    finally:
                        engine.drm_release(eng)
                n = eng.rcv.total + eng.drm_files
                h = len(eng.hyb_seen)
                self.ui(self.log, f"Fichier traité : {n} image(s) reçue(s), {eng.last['frames']} trames valides."
                        + (f" {eng.drm_files} en mode EasyPal." if eng.drm_files else "")
                        + (f" {h} annonce(s) hybride(s)." if h else ""))
            except Exception as e:
                self.ui(self.log, f"Erreur de décodage : {e}")

        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------- indicatif du panneau
    def _rx_call(self, call, t=None, guess=False):
        """Indicatif de la station reçue dans le panneau : la réception la plus récente gagne
        (une ancienne image DATAC n'écrase plus une annonce hybride ou une image EasyPal).
        guess : indicatif déduit des stations en ligne (affiché avec « ? »)."""
        t = time.time() if t is None else t
        cur = self.__dict__.setdefault("_pcall", (0.0, None, False))
        if t < cur[0] or (t == cur[0] and guess and not cur[2] and cur[1]):
            return
        self._pcall = (t, call, guess)
        self.panel.set_call(f"{call} ?" if guess and call else call)

    def _guess_tx_call(self):
        """Station en ligne actuellement en émission sur notre fréquence (à 3 kHz près),
        s'il n'y en a qu'une -> indicatif, sinon None."""
        mine = self.mycall()
        cands = set()
        for d in self.online.values():
            if d.get("state") != "TX" or time.time() - float(d.get("seen") or d.get("t") or 0) > 300:
                continue
            call = str(d.get("call") or "").upper()
            if not call or call == mine:
                continue
            f = d.get("freq")
            if self.rig_freq and f:
                try:
                    if abs(int(f) - int(self.rig_freq)) > 3000:
                        continue
                except (TypeError, ValueError):
                    continue
            cands.add(call)
        return cands.pop() if len(cands) == 1 else None

    def _rx_status(self, st):
        if st["mode"] != engine.DRM_MODE:            # EasyPal : bande exacte posée par le panneau
            self.wf.mark_mode(st["mode"])
        if st.get("call") and st["mode"] != "DATAC0":
            self._rx_call(st["call"])
        prog = st.get("progress")
        txt = f"Mode {st['mode']}  —  SNR {st['snr']:.1f} dB\nTrames valides : {st['frames']}"
        if st.get("call"):
            txt += f"\nDe : {st['call']}"
        self.v_rxstat.set(txt)
        if prog:
            got, K = prog
            if st["mode"] not in ("DATAC0", engine.DRM_MODE) and not st.get("from_file"):
                self._rx_tab_auto(("datac", st.get("id")))
                # dès le début de l'image : l'émission passe sur le mode reçu (réponse, BSR…),
                # une fois par image (un choix fait à la main ensuite est gardé)
                if getattr(self, "_datac_followed", None) != st.get("id"):
                    self._datac_followed = st.get("id")
                    self._follow_mode({"call": st.get("call")}, None, False)
            self.pb_rx.configure(value=100 * min(got, K) / K)
            self.v_rxstat.set(txt + f"\nImage en cours : {min(got, K)} / {K} symboles "
                                    f"({100 * min(got, K) // K} %)")

    def _rx_tab_auto(self, key):
        """Une image commence à arriver alors que l'onglet Émission est affiché : on passe
        sur l'onglet Réception pour la voir (une seule fois par image : si l'opérateur
        revient sur l'onglet Émission, on l'y laisse)."""
        seen = self.__dict__.setdefault("_rx_tab_seen", set())
        if key in seen:
            return
        seen.add(key)
        if len(seen) > 200:
            seen.clear()
            seen.add(key)
        try:
            if not self.tx_busy and self._tab_shown("tx"):
                self.show_tab("rx", focus=False)
        except tk.TclError:
            pass

    def _got_image(self, hdr, path, png, mode, from_file=False):
        if hdr.get("call"):
            hdr["call"] = self._full_call(hdr["call"])
        self.pb_rx.configure(value=100)
        who = hdr["call"] if hdr["call"] != "?" else "(indicatif à venir)"
        if hdr.get("text"):
            self._show_message(hdr.get("call"), hdr["text"])
            snr0 = self.rx_engine.last.get("snr") if self.rx_engine else None
            img = None if hdr.get("fmt") in ("txt", "file") else (png if png and os.path.exists(png) else path)
            self._msg_popup(dict(id=hdr.get("id"), call=hdr.get("call"), text=hdr["text"], mode=mode, snr=snr0,
                                 utc=time.strftime("%H:%M", time.gmtime()), local=time.strftime("%H:%M"),
                                 image=img))
            self._translate_msg(hdr.get("id"), hdr["text"])
        kind = "Aperçu reçu" if hdr.get("preview") else ("Texte reçu" if hdr.get("fmt") == "txt" else
                                                         ("Fichier reçu" if hdr.get("fmt") == "file" else "Image reçue"))
        if hdr.get("fmt") == "file":
            self._show_message(hdr.get("call"), tr("Fichier reçu :") + f" {hdr.get('filename', '?')} "
                               f"({_fmt_size(hdr.get('size', 0))}) — " + tr("double-clic dans l'historique pour l'ouvrir"))
        drm = mode.startswith(engine.DRM_MODE)          # « EasyPal » ou « EasyPal-HYB »
        snr = hdr.get("snr") if drm else (self.rx_engine.last.get("snr") if self.rx_engine else None)
        if snr is not None:
            self.snr_by_id[hdr["id"]] = snr
        self.station_event(hdr.get("call"), kind + (" (hybride)" if hdr.get("hybrid") else ""), mode, snr,
                           f"{hdr['size']} octets")
        self._heard(hdr.get("call"), snr, kind, hdr.get("loc"), hyb=bool(hdr.get("hybrid")))
        if not hdr.get("preview"):
            # message texte seul : accusé de réception aussi (sans changer la liste Rx Ok de l'image)
            self._net_confirm(hdr["id"], hdr.get("call"), show=hdr.get("fmt") != "txt")
        if not hdr.get("preview") and self.v_ack_auto.get() and self.rx_stream is not None and not drm:
            # (EasyPal ne connaît pas l'ACK de HFImage : rien n'est émis en mode EasyPal)
            act = self.rx_engine.activity.get(hdr["id"], {}) if self.rx_engine else {}
            self.ack_pending[hdr["id"]] = {"call": hdr.get("call"), "end_at": act.get("end", 0)}
            if hdr.get("hybrid"):
                # l'annonce hybride est répétée 3 fois (~11 s) : on attend qu'elle soit finie
                self.ack_pending[hdr["id"]]["wait_until"] = time.time() + 12
        if not hdr.get("preview") and not from_file:
            self._follow_mode(hdr, path, drm)
        if mode == engine.DRM_MODE:
            mode = f"EasyPal {hdr.get('drm', '')}".strip()
        self.log(f"{kind} {who} ({mode}, {hdr['size']} octets) : {os.path.basename(path)}")
        if hdr.get("preview"):
            mode = mode + " aperçu"
        if png:
            im, anim = self._show_rx(path, png)
            self._panel_thumb(im, hdr.get("call"))
            self._set_text(self.lb_rx_info, f"{os.path.basename(path)}   —   {hdr['call']}   —   {mode}   —   "
                                           f"{im.width}×{im.height}   —   {hdr['size'] / 1000:.1f} K" + anim)
            if not self.tx_busy:
                self.show_tab("rx", focus=False)
            if not hdr.get("preview") and os.sep + "relecture" + os.sep not in path:
                self._gallery_add("rx", hdr.get("call"), mode, path, png, hdr.get("size"), snr)
                self._web_queue("rx", png, hdr.get("call"), mode, hdr.get("id"))
        self.hist.insert(0, (hdr, path, png, mode))
        self.lst.insert(0, f"{time.strftime('%H:%M')}  {hdr['call']:8s} {mode}  {hdr['size']} o")

    def _follow_mode(self, hdr, path, drm):
        """Image ou message reçu dans l'autre famille de modes (EasyPal / HFImage) :
        l'émission passe sur ce mode, pour répondre à la station dans le mode qu'elle écoute.
        EasyPal : on reprend aussi le mode A/B/E, la largeur et la QAM reçus (pas en hybride,
        dont l'annonce est toujours en E/QAM4). HFImage : mode « Auto »."""
        if not self.v_follow.get() or self.tx_busy or self.rx_stream is None:
            return
        if path and os.sep + "relecture" + os.sep in path:
            return                                   # décodage d'un fichier WAV : pas de changement
        cur = self.v_mode.get()
        if drm:
            changes = []
            if cur != engine.DRM_MODE:
                self.v_mode.set(engine.DRM_MODE)
                changes.append("EasyPal")
            ms = str(hdr.get("drm") or "").split("/")
            if not hdr.get("hybrid") and len(ms) >= 4:
                want = {"drm_mode": ms[0], "drm_bw": {"2.2": DRM_BWS[0], "2.4": DRM_BWS[1]}.get(ms[1]),
                        "drm_qam": f"QAM{ms[3]}"}
                allowed = {"drm_mode": DRM_MODES, "drm_bw": DRM_BWS, "drm_qam": DRM_QAMS}
                for k, val in want.items():
                    if val in allowed[k] and self.v_drm[k].get() != val:
                        self.v_drm[k].set(val)
                        self.conf[k] = val
                        changes.append(val)
                if changes:
                    self._save_conf_file()
            if not changes:
                return
            v = self.v_drm
            what = "EasyPal" if changes == ["EasyPal"] else \
                f"EasyPal {v['drm_mode'].get()} / {v['drm_bw'].get()} / {v['drm_qam'].get()}"
        else:
            if cur != engine.DRM_MODE:
                return                               # déjà en HFImage : réglage de l'utilisateur gardé
            self.v_mode.set("Auto")
            what = "Auto (HFImage)"
        if cur != self.v_mode.get():
            self._mode_changed()
        else:
            self.prepare()
        self.log(tr("Émission passée sur le mode reçu :") + f" {what} ({hdr.get('call') or '?'})")

    def _thumb_from_gallery(self):
        """Au démarrage : la vignette du panneau montre la dernière image reçue (galerie)."""
        try:
            for e in list(self.gal_store.items if self.gal_store else []):
                if e.get("dir") != "rx" or e.get("mode", "").endswith("aperçu"):
                    continue
                src = self._gallery_src(e)
                if src and os.path.exists(src):
                    with imgfmt.open_upright(src) as im:
                        im.load()
                        self._panel_thumb(im.copy(), e.get("call"))
                    return
        except Exception as ex:
            self._journal(f"Vignette du panneau : {ex}\n")

    def _distance_to(self, call):
        """Distance (km) jusqu'à la station, d'après les locators ; None si inconnue."""
        here = protocol.locator_to_latlon(self.v_loc.get().strip())
        loc = self.known_loc.get(call, "")
        if not loc:
            d = next((x for x in self.online.values() if x.get("call") == call), None)
            loc = (d or {}).get("loc", "")
        there = protocol.locator_to_latlon(loc)
        if not (here and there):
            return None
        import stationmap
        return stationmap.distance_km(here, there)

    def show_sites(self):
        """Fenêtre « Sites des stations » (remplace Digi-Sites, qui n'est plus entretenu)."""
        w = getattr(self, "sites_win", None)
        if w is not None and w.alive():
            w.lift()
            w.refresh(force=True)
            return
        self.sites_win = sites.SitesWindow(self)

    def _my_site(self):
        """Adresse de notre image1 (Site web / Digi-Sites), annoncée dans la présence ; "" sinon."""
        if not self.conf.get("web_on") or not self.conf.get("web_url"):
            return ""
        return websync.digisites_url(self._web_cfg())

    def _panel_thumb(self, im, call):
        """Vignette du panneau : dernière image reçue, avec indicatif, prénom et distance."""
        try:
            c = self._station_call(call) if call else ""
            parts = [self._label(c)] if c and c != "?" else []
            dist = self._distance_to(c) if c else None
            if dist is not None:
                parts.append(f"{dist:.0f} km")
            self.panel.set_thumb(im.convert("RGB"), "\n".join(parts))      # une ligne chacun
        except Exception as e:
            self._journal(f"Vignette du panneau : {e}\n")

    def _show_rx(self, path, png):
        """Affiche une image reçue ; un GIF animé est joué en boucle.
        -> (première image, texte en plus pour la barre d'info)."""
        im = imgfmt.open_upright(png)            # photo de téléphone « couchée » : remise droite
        if path and path.lower().endswith(".gif") and os.path.exists(path):
            try:
                frames, durs = imgfmt.gif_frames(path)
                if len(frames) > 1:
                    self.lb_rx.set_animation(frames, durs)
                    return im, tr(f"   —   GIF animé, {len(frames)} images")
            except Exception as e:
                self.log(f"GIF illisible : {e}")
        self._show(self.lb_rx, "rx", im)
        return im, ""

    def _show_message(self, call, text):
        self.msgbox.configure(state="normal")
        self.msgbox.insert("1.0", f"[{time.strftime('%H:%M')}] {call or '?'} : {text}\n")
        self.msgbox.configure(state="disabled")
        self.log(f"Message de {call or '?'} : {text[:80]}")

    # ------------------------------------------------------------- messages envoyés : accusés de réception
    def _msg_sent(self, iid, text, mode, with_image=False):
        self._last_sent_text = text           # « Répondre » peut remplacer ce texte sans demander
        self.sent_msgs[iid] = {"text": text, "t": time.time(), "mode": mode, "acks": {}, "image": with_image}
        for k in list(self.sent_msgs)[:-50]:
            del self.sent_msgs[k]
        self._msg_sent_refresh()

    def _msg_ack(self, iid, call, rep, via):
        m = self.sent_msgs.get(iid)
        call = (call or "").strip().upper()
        if not m or not call or call == "?" or call == self.mycall():
            return
        first = call not in m["acks"]
        old = m["acks"].get(call)
        m["acks"][call] = (rep if rep is not None else (old[0] if old else None), time.time(),
                           via if not old or old[2] == via else old[2] + " + " + via)
        self._msg_sent_refresh()
        if not first:
            return
        short = m["text"] if len(m["text"]) <= 40 else m["text"][:38] + "…"
        rs = "" if rep is None else f" ({rep:+d} dB)"
        line = tr("✓ {0} a bien reçu votre message").replace("{0}", call) + f" « {short} »{rs}"
        self.log(line)
        self.msgbox.configure(state="normal")
        self.msgbox.insert("1.0", f"[{time.strftime('%H:%M')}] {line}\n", "ack")
        self.msgbox.tag_configure("ack", foreground="#1c7f1c")
        self.msgbox.configure(state="disabled")
        self.station_event(call, "Message reçu par le correspondant", "", None,
                           f"« {short} »" + ("" if rep is None else f", report {rep:+d} dB") + f" — {via}")

    def _msg_status(self, m):
        if m["acks"]:
            return ", ".join(f"✓ {c}" + ("" if r is None else f" ({r:+d} dB)") + f" {time.strftime('%H:%M', time.localtime(t))}"
                             for c, (r, t, v) in sorted(m["acks"].items(), key=lambda kv: kv[1][1]))
        if time.time() - m["t"] > 180:
            return tr("pas d'accusé de réception")
        return tr("en attente de l'accusé…")

    def _msg_sent_refresh(self):
        tv = getattr(self, "tv_sent", None)
        if tv is None:
            return
        tv.delete(*tv.get_children())
        for iid, m in reversed(list(self.sent_msgs.items())):
            txt = m["text"].replace("\n", " ")
            tv.insert("", "end", values=(clocktz.fmt("%H:%M", m["t"], suffix=False),
                                         (tr("[image] ") if m.get("image") else "") + txt, self._msg_status(m)),
                      tags=("ok" if m["acks"] else ("none" if time.time() - m["t"] > 180 else "wait"),))
        tv.tag_configure("ok", foreground="#1c7f1c")
        tv.tag_configure("none", foreground="#b00000")
        tv.tag_configure("wait", foreground="#b06000")

    def _translate_msg(self, iid, text):
        """Traduit un message reçu dans la langue du programme (en tâche de fond, par Internet).
        Le message d'origine reste affiché ; la traduction s'ajoute quand elle arrive."""
        if not self.conf.get("msg_translate", True):
            return
        target = i18n.get_lang()
        translate.translate_async(text, target,
                                  lambda res: res and self.ui(self._show_translation, iid, text, target, res))

    def _show_translation(self, iid, text, target, res):
        out, src = res
        pair = f"{(src or '?').upper()} → {target.upper()}"
        self.msgbox.configure(state="normal")
        self.msgbox.insert("1.0", "   ↳ " + tr("traduction") + f" ({pair}) : {out}\n", "trad")
        self.msgbox.tag_configure("trad", foreground="#1f4fa8")
        self.msgbox.configure(state="disabled")
        self.log(tr("Traduction du message") + f" ({pair}) : {out[:80]}")
        if getattr(self, "msgwin", None) is not None and self.msgwin.winfo_exists():
            self.msgwin.set_translation(iid, text, out, pair)

    def _msg_popup(self, item):
        """Fenêtre « Message reçu » (ouverte automatiquement si l'option est cochée)."""
        if getattr(self, "msgwin", None) is None or not self.msgwin.winfo_exists():
            self.msgwin = msgwin.MessageWindow(self)
        self.msgwin.add(item)

    def show_messages(self):
        if getattr(self, "msgwin", None) is None or not self.msgwin.winfo_exists():
            self.msgwin = msgwin.MessageWindow(self)
        self.msgwin.show()
        self.msgwin.deiconify()
        self.msgwin.lift()

    def _got_ident(self, info, path, png):
        if info.get("call"):
            info["call"] = self._full_call(info["call"])
        """L'indicatif est arrivé (trame d'identification de fin) : mise à jour."""
        if info["id"] in self.ack_pending:
            self.ack_pending[info["id"]]["call"] = info["call"]
        self._heard(info.get("call"), self.snr_by_id.get(info["id"]), "Image reçue", info.get("loc"))
        if not info.get("preview"):
            self._net_confirm(info["id"], info.get("call"), show=info.get("fmt") != "txt")
        if info["id"] in self.snr_by_id and info.get("call") not in (None, "?"):
            self.snr_by_call[info["call"]] = self.snr_by_id[info["id"]]
        if info.get("text"):
            if getattr(self, "msgwin", None) is not None:
                self.msgwin.set_call(info["id"], info.get("call"))
                if info.get("fmt") not in ("txt", "file") and (png or path):
                    self.msgwin.set_image(info["id"], png if png and os.path.exists(png) else path)
            self.msgbox.configure(state="normal")
            self.msgbox.insert("1.0", tr(f"   ↳ message ci-dessous envoyé par {info['call']}") + "\n")
            self.msgbox.configure(state="disabled")
        for i, (h, p, pg, mode) in enumerate(self.hist):
            if h["id"] == info["id"]:
                if self.gal_store is not None and p:
                    self.gal_store.update_file(p, path, png, info.get("call"))
                    self.gal.refresh()
                self.hist[i] = (info, path, png, mode)
                self.lst.delete(i)
                self.lst.insert(i, f"{time.strftime('%H:%M')}  {info['call']:8s} {mode}  {info['size']} o")
                if i == 0:
                    cur = self._orig.get(str(self.lb_rx_info), "")
                    self._set_text(self.lb_rx_info, cur.replace("   —   ?   —", f"   —   {info['call']}   —")
                                   if "   —   ?   —" in cur else f"{info['call']} — {mode}")
                self.log(f"Identification : image envoyée par {info['call']}")
                self.station_event(info["call"], "Identification de fin", mode.split()[0], None,
                                   f"{info['size']} octets")
                break

    def _hist_select(self, _e):
        sel = self.lst.curselection()
        if not sel:
            return
        hdr, path, png, mode = self.hist[sel[0]]
        if png and os.path.exists(png):
            im, anim = self._show_rx(path, png)
            self._set_text(self.lb_rx_info, f"{hdr['call']} — {mode} — {im.width}×{im.height}" + anim)

    def toggle_record(self):
        if self.rec_wav is not None:
            w, self.rec_wav = self.rec_wav, None
            w.close()
            self._set_text(self.btn_rec, "● Enregistrer RX")
            self._btn_on("wave", False)
            self._wav_refresh()
            self.log(f"Enregistrement arrêté : {self.rec_path}")
            return
        if self.rx_stream is None:
            messagebox.showinfo(APP, "Lancez d'abord l'écoute : l'enregistrement prend le son reçu.")
            return
        d = wavtext.wav_dir(DEFAULT_OUT)
        self.rec_path = os.path.join(d, time.strftime("RX_%Y%m%d_%H%M%S.wav"))
        w = wave.open(self.rec_path, "wb")
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        self.rec_wav = w
        self._set_text(self.btn_rec, "■ Arrêter l'enregistrement")
        self._btn_on("wave", True)
        self.log(f"Enregistrement du son reçu (8 kHz) : {self.rec_path}")

    def replay_rx(self):
        """Redécode les 15 dernières minutes reçues (ex. après un changement de réglage)."""
        if not self.ring:
            messagebox.showinfo(APP, "Rien en mémoire : la relecture porte sur ce qui a été écouté.")
            return
        x = np.concatenate(self.ring)
        self.log(f"Relecture de {_fmt_s(len(x) / 8000)} de réception…")
        eng = self._new_engine()
        eng.outdir = os.path.join(self.v_folder.get(), "relecture")
        os.makedirs(eng.outdir, exist_ok=True)
        eng.on_control = lambda *a: None

        def run():
            for i in range(0, len(x), 8000):
                eng.process(x[i:i + 8000])
            eng.process(np.zeros(8000 * 3, np.int16))
            if hamdrm.AVAILABLE:          # mode EasyPal : le son gardé (8 kHz) suffit, il tient sous 3 kHz
                engine.drm_claim(eng)
                try:
                    for i in range(0, len(x), 8000):
                        eng.process48(audio.upsample(x[i:i + 8000]))
                    eng.process48(np.zeros(48000 * 3, np.float32))
                finally:
                    engine.drm_release(eng)
            self.ui(self.log, f"Relecture terminée : {eng.rcv.total + eng.drm_files} élément(s) décodé(s) "
                              f"(dossier « relecture »).")

        threading.Thread(target=run, daemon=True).start()

    def qsl_dialog(self):
        win = tk.Toplevel(self)
        win.title("Carte QSL")
        win.transient(self)
        fields = {}
        now = clocktz.fmt("%Y-%m-%d %H:%M", suffix=False)
        last = ""
        for iid in self.tree.get_children():          # dernière station identifiée
            c = self.tree.item(iid, "values")[1]
            if c and c != "?" and c != self.mycall():
                last = c
                break
        freq = audio.format_freq(self.rig_freq, True) if self.rig_freq else self.conf.get("qsl_freq", "14.233 MHz")

        def report_for(call):
            snr = self.snr_by_call.get(call.strip().upper())
            return f"SNR {snr:+.0f} dB" if snr is not None else ""

        for i, (key, lab, val) in enumerate((("to", "Indicatif du correspondant", last),
                                             ("utc", clocktz.label(tr("Date / heure")), now),
                                             ("freq", "Fréquence", freq),
                                             ("report", "Report", report_for(last)),
                                             ("msg", "Message", "TNX QSO, 73 !"))):
            ttk.Label(win, text=lab).grid(row=i, column=0, sticky="w", padx=8, pady=3)
            v = tk.StringVar(value=val)
            ttk.Entry(win, textvariable=v, width=32).grid(row=i, column=1, padx=8, pady=3)
            fields[key] = v
        auto = {"report": fields["report"].get()}

        def to_changed(*_):
            # le report suit l'indicatif tant qu'on ne l'a pas modifié à la main
            if fields["report"].get() == auto["report"]:
                auto["report"] = report_for(fields["to"].get())
                fields["report"].set(auto["report"])

        fields["to"].trace_add("write", to_changed)
        bg = {"img": self.src_img}
        lab_bg = ttk.Label(win, text="Fond : image ouverte" if self.src_img is not None else "Fond : dégradé")
        lab_bg.grid(row=5, column=0, columnspan=2, sticky="w", padx=8)

        # ---- style : police, couleurs, taille de l'indicatif, bandeaux (gardé pour la prochaine fois)
        style = dict(qsl.DEFAULT_STYLE, **(self.conf.get("qsl_style") or {}))
        sf = ttk.LabelFrame(win, text="Style de la carte", padding=6)
        sf.grid(row=6, column=0, columnspan=2, sticky="we", padx=8, pady=(6, 0))
        v_font = tk.StringVar(value=style["font"])
        ttk.Label(sf, text="Police").grid(row=0, column=0, sticky="w")
        cbf = ttk.Combobox(sf, textvariable=v_font, values=list(qsl.FONTS), state="readonly", width=18)
        cbf.grid(row=0, column=1, columnspan=3, sticky="w", padx=4, pady=2)
        swatches = {}

        def pick_color(key, label):
            from tkinter import colorchooser
            c = colorchooser.askcolor(color=style[key], parent=win, title=tr(label))
            if c and c[1]:
                style[key] = c[1]
                swatches[key].configure(bg=c[1])
                refresh()

        for i, (key, label) in enumerate((("call", "Indicatif"), ("text", "Texte"),
                                          ("accent", "Locator / correspondant"), ("band", "Bandeaux"))):
            r, c = 1 + i // 2, (i % 2) * 2
            b = tk.Button(sf, text="    ", bg=style[key], relief="ridge", width=3,
                          command=lambda k=key, l=label: pick_color(k, l))
            b.grid(row=r, column=c, sticky="w", padx=(0, 4), pady=2)
            swatches[key] = b
            ttk.Label(sf, text=label).grid(row=r, column=c + 1, sticky="w", padx=(0, 10))
        v_size = tk.IntVar(value=int(style["call_size"]))
        v_alpha = tk.IntVar(value=int(style["band_alpha"]))
        ttk.Label(sf, text="Taille de l'indicatif").grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Scale(sf, from_=60, to=130, variable=v_size, command=lambda v: refresh()).grid(
            row=3, column=2, columnspan=2, sticky="we", pady=(4, 0))
        ttk.Label(sf, text="Opacité des bandeaux").grid(row=4, column=0, columnspan=2, sticky="w")
        ttk.Scale(sf, from_=0, to=100, variable=v_alpha, command=lambda v: refresh()).grid(
            row=4, column=2, columnspan=2, sticky="we")
        # hauteur des bandeaux (demande de RK1AT)
        v_hh = tk.IntVar(value=int(style.get("head_h", 100)))
        v_bh = tk.IntVar(value=int(style.get("band_h", 100)))
        ttk.Label(sf, text="Hauteur du bandeau du haut").grid(row=5, column=0, columnspan=2, sticky="w")
        ttk.Scale(sf, from_=qsl.BAND_MIN, to=qsl.BAND_MAX, variable=v_hh, command=lambda v: refresh()).grid(
            row=5, column=2, columnspan=2, sticky="we")
        ttk.Label(sf, text="Hauteur du bandeau du bas").grid(row=6, column=0, columnspan=2, sticky="w")
        ttk.Scale(sf, from_=qsl.BAND_MIN, to=qsl.BAND_MAX, variable=v_bh, command=lambda v: refresh()).grid(
            row=6, column=2, columnspan=2, sticky="we")

        def reset_style():
            style.update(qsl.DEFAULT_STYLE)
            v_font.set(style["font"]); v_size.set(style["call_size"]); v_alpha.set(style["band_alpha"])
            v_hh.set(style["head_h"]); v_bh.set(style["band_h"])
            for k, b in swatches.items():
                b.configure(bg=style[k])
            refresh()

        ttk.Button(sf, text="Style d'origine", command=reset_style).grid(row=7, column=0, columnspan=4,
                                                                        sticky="w", pady=(6, 0))
        # ---- aperçu en direct
        pv = tk.Canvas(win, width=480, height=300, bg="#000", highlightthickness=0)
        pv.grid(row=0, column=2, rowspan=8, padx=8, pady=8, sticky="n")
        prev = {"job": None, "ph": None}

        def current_style():
            style.update(font=v_font.get(), call_size=int(v_size.get()), band_alpha=int(v_alpha.get()),
                         head_h=int(v_hh.get()), band_h=int(v_bh.get()))
            return dict(style)

        def build():
            return qsl.make_card(bg["img"], self.mycall() or "NOCALL", self.v_loc.get().strip(),
                                 fields["to"].get(), fields["freq"].get(), fields["report"].get(),
                                 fields["msg"].get(), fields["utc"].get(), style=current_style())

        def draw():
            prev["job"] = None
            if not win.winfo_exists():
                return
            im = build().resize((480, 300), Image.LANCZOS)
            prev["ph"] = ImageTk.PhotoImage(im)
            pv.delete("all")
            pv.create_image(0, 0, image=prev["ph"], anchor="nw")

        def refresh(*_):
            if prev["job"] is not None:
                win.after_cancel(prev["job"])
            prev["job"] = win.after(150, draw)

        cbf.bind("<<ComboboxSelected>>", refresh)
        for v in fields.values():
            v.trace_add("write", refresh)

        def pick():
            p = filedialog.askopenfilename(parent=win, filetypes=[("Images", "*.jpg *.jpeg *.png *.svg *.bmp *.webp *.avif")])
            if p:
                try:
                    bg["img"] = imgfmt.load_source(p)[0]
                except Exception as e:
                    messagebox.showerror(APP, f"Image illisible : {e}")
                    return
                self._set_text(lab_bg, f"Fond : {os.path.basename(p)}")
                refresh()

        def make():
            self.conf["qsl_freq"] = fields["freq"].get()
            card = build()
            self.conf["qsl_style"] = dict(style)          # gardé pour la prochaine carte
            try:
                with open(CONF_PATH, "w", encoding="utf-8") as f:
                    json.dump(self.conf, f, indent=1)
            except Exception:
                pass
            self.src_img = card
            self.src_raw = self.src_kind = self.src_anim = None
            self._show(self.lb_src, "src", card)
            self._set_text(self.lb_src_info, f"Carte QSL pour {fields['to'].get() or '—'}")
            win.destroy()
            self.prepare()

        bf = ttk.Frame(win)
        bf.grid(row=7, column=0, columnspan=2, pady=8)
        ttk.Button(bf, text="Choisir un fond…", command=pick).pack(side="left", padx=4)
        ttk.Button(bf, text="Créer la carte", command=make).pack(side="left", padx=4)
        self._translate_ui(win)
        refresh()

    def _open_full(self):
        """Ouvre l'image sélectionnée (ou la dernière) dans la visionneuse Windows."""
        sel = self.lst.curselection()
        i = sel[0] if sel else 0
        if not self.hist:
            return
        hdr, path, png, mode = self.hist[i]
        target = png if png and os.path.exists(png) else path
        if path and path.lower().endswith(".gif") and os.path.exists(path):
            target = path                              # la visionneuse joue l'animation
        if not target or not os.path.exists(target):
            return
        target = imgfmt.viewable(target)               # AVIF / JPEG 2000 : copie PNG temporaire
        if sys.platform.startswith("win"):
            os.startfile(target)
        else:
            subprocess.Popen(["xdg-open", target])

    # ------------------------------------------------------------- galerie
    def _gallery_open(self):
        """(Ré)ouvre la galerie du dossier des images reçues."""
        folder = self.v_folder.get() or DEFAULT_OUT
        if self.gal_store is not None and self.gal_store.folder == folder:
            return
        try:
            self.gal_store = gallery.GalleryStore(folder)
            self.gal.set_store(self.gal_store)
        except Exception as e:
            self.log_exc("Galerie", e)

    def _gallery_add(self, direction, call, mode, path, png, size, snr=None):
        if self.gal_store is None:
            return
        e = {"t": time.time(), "dir": direction, "call": call or "?", "mode": mode,
             "file": path, "png": png, "size": size or 0}
        if snr is not None:
            e["snr"] = round(float(snr), 1)
        self.gal_store.add(e)
        self.gal.refresh()

    def _sentkeep_changed(self):
        lab = self.v_sentkeep.get()
        self.conf["sent_keep"] = next((v for x, v in SENT_KEEP.items() if tr(x) == lab or x == lab), 0)
        self._save_conf_file()
        self.log(tr("Images envoyées gardées (dossier « envoyees »)") + f" : {lab}")
        self._prune_sent()

    def _prune_sent(self):
        """Dossier « envoyees » : ne garde que les N dernières images envoyées (réglage), en effaçant
        les autres fichiers de ce dossier seulement (images reçues et autres dossiers jamais touchés)."""
        keep = int(self.conf.get("sent_keep", 0) or 0)
        if keep <= 0 or self.gal_store is None:
            return
        norm = lambda p: os.path.normcase(os.path.realpath(p))
        root = norm(os.path.join(self.gal_store.folder, gallery.SENT_DIR))
        tx = [e for e in list(self.gal_store.items) if e.get("dir") == "tx"]
        kept = set()
        for e in tx[:keep]:
            kept |= {norm(p) for p in (e.get("file"), e.get("png")) if p}
        for e in tx[keep:]:
            self.gal_store.remove(e)
        gone = 0
        for top, dirs, files in os.walk(root, topdown=False):
            for n in files:
                p = norm(os.path.join(top, n))
                if p in kept or not p.startswith(root + os.sep) or n.startswith("."):
                    continue
                try:
                    os.remove(p)
                    gone += 1
                except OSError:
                    pass
            if top != root:
                try:
                    os.rmdir(top)                      # dossier du jour devenu vide
                except OSError:
                    pass
        if gone:
            self._journal(f"Dossier envoyees : {gone} ancien(s) fichier(s) effacé(s) (gardées : {keep}).\n")
            try:
                self.gal.refresh()
            except Exception:
                pass

    def _gallery_sent(self, job, mode):
        """Image émise : une copie va dans « envoyees » pour la galerie « Dernières envoyées »."""
        try:
            tx = job["tx"]
            data = tx.data
            if job["kind"] == "image":
                _text, img = protocol.unpack_text(data)
                if not img:
                    return                                     # message texte seul
                data = img
            fmt = protocol.detect_format(data)
            if fmt in ("hft", "txt", "file", "bin"):
                return
            call = self.mycall().replace("/", "-") or "NOCALL"
            mode_n = (mode or "") + ("-HYB" if job["kind"] == "hybrid" and "HYB" not in (mode or "") else "")
            crc = zlib.crc32(data)
            # même image déjà envoyée : pas de nouvelle copie, elle remonte en tête de la galerie
            dup = next((e for e in list(self.gal_store.items) if e.get("dir") == "tx" and e.get("crc") == crc
                        and e.get("size") == len(data) and os.path.exists(e.get("file") or "")), None)
            if dup is not None:
                dup.update(t=time.time(), mode=mode_n)
                self.gal_store.add(dup)
                self.gal.refresh()
                path, png = dup.get("file"), dup.get("png")
            else:
                d = os.path.join(self.gal_store.folder, gallery.SENT_DIR, time.strftime("%Y-%m-%d"))
                os.makedirs(d, exist_ok=True)
                stem = os.path.join(d, f"{time.strftime('%Y%m%d_%H%M%S')}_{mode_n}_{call}")
                import glob
                base, k = stem, 2
                # même seconde : autre nom (le suffixe ne touche qu'au nom du fichier, jamais au dossier,
                # qui peut contenir lui-même un « ~ » sous Windows : C:\Users\RUNNER~1\…)
                while glob.glob(glob.escape(base) + ".*"):
                    base = f"{stem}_{k}"
                    k += 1
                path, png = imgfmt.save_received(base, fmt, data)
                self._gallery_add("tx", call, mode_n, path, png, len(data))
                if self.gal_store.items and self.gal_store.items[0].get("file") == path:
                    self.gal_store.items[0]["crc"] = crc
                    self.gal_store.save()
            self._prune_sent()
            self._web_queue("tx", png or path, call, mode_n)
        except Exception as e:
            self.log_exc("Galerie (image envoyée)", e)

    # ------------------------------------------------------------- site web / Digi-Sites
    def _web_cfg(self):
        c = self._hyb_cfg()                        # même serveur FTP que le mode hybride
        c.update(dir=self.conf.get("web_dir", "") or "", url=self.conf.get("web_url", ""),
                 count=int(self.conf.get("web_count", 20)),
                 call=self.mycall() or "NOCALL")
        return c

    def _web_recent(self):
        """Dernières images de la galerie à remettre en ligne : ([(chemin, légende)] reçues,
        [(chemin, légende)] émises), de la plus récente à la plus ancienne."""
        rx, tx = [], []
        if self.gal_store is None:
            return rx, tx
        skip = {c.strip().upper() for c in str(self.conf.get("web_block", "")).replace(";", ",").split(",")}
        for e in list(self.gal_store.items):
            src = self._gallery_src(e)
            if not src or not os.path.exists(src):
                continue
            mode = str(e.get("mode") or "")
            if " aperçu" in mode:
                continue
            when = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(e.get("t") or 0))
            call = str(e.get("call") or "?")
            if e.get("dir") == "rx" and call.upper() not in skip:
                rx.append((src, "  ".join([call, when, mode.split()[0] if mode else ""]).strip()))
            elif e.get("dir") == "tx" and self.conf.get("web_tx", True):
                tx.append((src, "  ".join([tr("émise par") + " " + call, when,
                                           mode.split()[0] if mode else ""]).strip()))
        return rx, tx

    def _web_caption(self, call, mode):
        band = audio.band_of(self.rig_freq) if self.rig_freq else ""
        # heure UTC, comme EasyPal : la même pour toutes les stations, quel que soit leur pays
        parts = [call or "?", time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), (mode or "").split()[0]]
        if band:
            parts.append(band)
        return "  ".join(parts)

    def _web_queue(self, kind, path, call, mode, iid=None):
        if not self.conf.get("web_on") or not path or not os.path.exists(path):
            return
        if kind == "tx" and not self.conf.get("web_tx", True):
            return
        if kind == "rx" and iid is not None and iid in self.my_ids:
            return                                  # notre propre image, entendue en retour
        skip = {c.strip().upper() for c in str(self.conf.get("web_block", "")).replace(";", ",").split(",")}
        if kind == "rx" and (call or "").upper() in skip:
            return
        if not self._hyb_cfg()["host"]:
            self.log("Site web : serveur FTP non réglé (Réglages → Mode hybride).")
            return
        self.web.add(self._web_cfg(), kind, path, self._web_caption(call if kind == "rx" else
                                                                     tr("émise par") + " " + call, mode))

    def web_dialog(self):
        w = getattr(self, "_web_win", None)
        if w is not None and w.winfo_exists():
            w.lift()
            return
        w = self._web_win = tk.Toplevel(self)
        w.title("Site web / Digi-Sites")
        w.transient(self)
        w.resizable(False, False)
        f = ttk.Frame(w, padding=12)
        f.pack(fill="both", expand=True)
        v_on = tk.BooleanVar(value=bool(self.conf.get("web_on")))
        v_tx = tk.BooleanVar(value=bool(self.conf.get("web_tx", True)))
        v_dir = tk.StringVar(value=self.conf.get("web_dir", ""))
        v_url = tk.StringVar(value=self.conf.get("web_url", ""))
        v_n = tk.StringVar(value=str(self.conf.get("web_count", 20)))
        v_block = tk.StringVar(value=self.conf.get("web_block", ""))
        ttk.Label(f, text="Comme EasyPal : chaque image reçue est mise en ligne sur votre site sous le nom\n"
                          "image1, sans extension (les précédentes glissent : image2, image3…), avec indicatif,\n"
                          "date, mode et bande. Digi-Sites lit image1 à la racine du site (dossier vide).\n"
                          "Vos images émises vont dans TX1.jpg … TX5.jpg.",
                  justify="left").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(f, text="Mettre en ligne les images reçues", variable=v_on).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Checkbutton(f, text="Mettre aussi en ligne mes images émises (TX1 … TX5)", variable=v_tx).grid(
            row=2, column=0, columnspan=2, sticky="w")
        rows = [("Dossier sur le serveur", ttk.Entry(f, textvariable=v_dir, width=30)),
                ("Lien public de ce dossier", ttk.Entry(f, textvariable=v_url, width=40)),
                ("Nombre d'images reçues gardées", ttk.Combobox(f, textvariable=v_n, values=["10", "20", "30", "50"],
                                                                width=5, state="readonly")),
                ("Ne pas mettre en ligne (indicatifs)", ttk.Entry(f, textvariable=v_block, width=30))]
        for i, (lab, wd) in enumerate(rows):
            ttk.Label(f, text=lab).grid(row=3 + i, column=0, sticky="w", pady=2)
            wd.grid(row=3 + i, column=1, sticky="w", padx=6, pady=2)
        lb = ttk.Label(f, text="", foreground="#1c6f1c", wraplength=520, justify="left")
        lb.grid(row=8, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Label(f, text="Serveur FTP, identifiant et mot de passe : ceux du mode hybride (Réglages).\n"
                          "Dossier vide = racine du site (comme EasyPal).\n"
                          "Ex. qsl.net : dossier vide, lien https://www.qsl.net/f4gop\n"
                          "Ex. : dossier « dsstv », lien http://monsite.free.fr/dsstv",
                  foreground="#555", justify="left").grid(row=9, column=0, columnspan=2, sticky="w", pady=(6, 0))

        def store():
            d = v_dir.get().strip()
            if "://" in d or d.lower().startswith("www."):
                # une adresse web collée dans « Dossier » : c'est le lien public, le dossier est la racine
                if not v_url.get().strip():
                    u = d if "://" in d else "https://" + d
                    if u.rsplit("/", 1)[-1].lower().startswith(("image", "tx", "hfimage")):
                        u = u.rsplit("/", 1)[0]
                    v_url.set(u)
                d = ""
                v_dir.set("")
                messagebox.showinfo(APP, "« Dossier sur le serveur » est le dossier FTP (ex. dsstv), pas une adresse "
                                         "web. L'adresse a été placée dans « Lien public » et le dossier mis à la "
                                         "racine du site : vérifiez avant d'envoyer.", parent=w)
            self.conf.update(web_on=bool(v_on.get()), web_tx=bool(v_tx.get()),
                             web_dir=d.strip("/"), web_url=v_url.get().strip(),
                             web_count=int(v_n.get() or 20), web_block=v_block.get().strip())
            self._save_conf_file()
            u = websync.page_url(self._web_cfg())
            d = websync.digisites_url(self._web_cfg())
            lb.configure(text=(tr("Adresse à donner à Digi-Sites :") + f" {d}\n" + tr("Page de vos images :")
                               + f" {u}") if u else "")

        def send_page():
            store()
            if not v_url.get().strip():
                messagebox.showerror(APP, "Renseignez le lien public du dossier (adresse web où l'on voit les images).",
                                     parent=w)
                return
            if not self._hyb_cfg()["host"]:
                messagebox.showerror(APP, "Réglez d'abord le serveur FTP (Réglages → Mode hybride).", parent=w)
                return
            # la page ET les dernières images (après un changement de dossier, Digi-Sites trouve
            # tout de suite image1, sans attendre la prochaine image reçue)
            rx, tx = self._web_recent()
            self.web.resync(self._web_cfg(), rx, tx)
            lb.configure(text=tr("Envoi de la page en cours… (résultat dans le journal)"))

        b = ttk.Frame(f)
        b.grid(row=10, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(b, text="Envoyer la page maintenant", command=send_page).pack(side="left")
        ttk.Button(b, text="Enregistrer", command=lambda: (store(), self.log("Site web : réglages enregistrés."))
                   ).pack(side="left", padx=6)
        ttk.Button(b, text="Fermer", command=lambda: (store(), w.destroy())).pack(side="left")
        store()
        self._translate_ui(w)

    def _gallery_src(self, e):
        p, png = e.get("file"), e.get("png")
        return png if png and os.path.exists(png) else p

    def gallery_show(self, e):
        src = self._gallery_src(e)
        if not src or not os.path.exists(src):
            return
        try:
            im, anim = self._show_rx(e.get("file"), src)
        except Exception as ex:
            self.log_exc("Galerie", ex)
            return
        who = e.get("call") if e.get("dir") == "rx" else tr("envoyée")
        self._set_text(self.lb_rx_info, f"{os.path.basename(e.get('file') or '')}   —   {who}   —   "
                                       f"{e.get('mode', '')}   —   {im.width}×{im.height}" + anim)
        self.show_tab("rx")

    def gallery_full(self, e):
        p = e.get("file")
        if not (p and os.path.exists(p) and (p.lower().endswith(".gif") or p.lower().endswith(".jpg"))):
            p = self._gallery_src(e)
        if p and os.path.exists(p):
            self._open_path(imgfmt.viewable(p))

    def gallery_to_tx(self, e):
        p = e.get("file")
        if p and p.lower().endswith((".avif", ".webp")) and e.get("png") and os.path.exists(e["png"]):
            p = e["png"]
        if p and os.path.exists(p):
            self.load_image(p)
            self.show_tab("tx")

    def copy_image(self, src):
        """Image (PIL) ou fichier -> presse-papiers, pour la coller dans Teams, un e-mail…"""
        import clip
        try:
            im = src if isinstance(src, Image.Image) else clip.load(src)
            anim = False
            if isinstance(src, str) and src.lower().endswith(".gif"):
                with open(src, "rb") as f:
                    anim = imgfmt.is_animated_gif(f.read())
            clip.copy_image(im)
        except Exception as e:
            self.log_exc("Copie de l'image", e)
            messagebox.showerror(APP, tr("Copie de l'image impossible :") + f"\n{tr(str(e))}")
            return False
        self.log(tr("Image copiée : collez-la avec Ctrl+V (Teams, e-mail…).") + f" ({im.width}×{im.height})"
                 + (" — " + tr("GIF animé copié comme image fixe.") if anim else ""))
        return True

    def gallery_copy(self, e):
        p = e.get("file")
        src = p if p and os.path.exists(p) else self._gallery_src(e)
        if src and os.path.exists(src):
            try:
                return self.copy_image(src)
            except Exception:
                pass
        src = self._gallery_src(e)                     # fichier illisible : son aperçu PNG
        if src and os.path.exists(src):
            return self.copy_image(src)
        return False

    def _rx_menu(self, ev):
        """Clic droit sur la grande image de l'onglet RX."""
        v = self.lb_rx
        m = tk.Menu(self, tearoff=0)
        img = v.frames[0] if v.frames else v.pil
        m.add_command(label=tr("Copier l'image"), command=lambda: self.copy_image(img),
                      state="normal" if img is not None else "disabled")
        if v.zoom > 1.0:
            m.add_command(label=tr("Revenir à l'image entière"), command=v.reset_zoom)
        try:
            m.tk_popup(ev.x_root, ev.y_root)
        finally:
            m.grab_release()

    def gallery_folder(self, e):
        p = e.get("file")
        if not p:
            return
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(p)])
        else:
            self._open_path(os.path.dirname(p))

    def open_path(self, p):
        os.makedirs(p, exist_ok=True)
        self._open_path(p)

    def open_folder(self):
        folder = self.v_folder.get()
        os.makedirs(folder, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    # ------------------------------------------------------------ simulation
    def simulate(self):
        if not self.tx:
            messagebox.showinfo(APP, "Ouvrez d'abord une image dans l'onglet Émission.")
            return
        import loopback
        tx = self.tx
        snr, fading = float(self.v_snr.get()), self.v_fading.get()
        self.v_sim.set("Simulation en cours…")

        def run():
            r = loopback.run(tx.data, tx.fmt, tx.mode, snr, fading, tx.overhead, verbose=False)
            if r.get("ok"):
                txt = (f"Image reçue intacte en {r['t_s']:.0f} s de temps d'antenne "
                       f"({r['rounds']} passage{'s' if r['rounds'] > 1 else ''})\n"
                       + (f"SNR estimé par le modem : {r['snr_est']:.1f} dB" if r.get("snr_est") is not None else ""))
            else:
                txt = (f"Échec après {r['rounds']} passages ({r['t_s']:.0f} s).\n"
                       f"Essayez un mode plus robuste ou une image plus petite.")
            self.ui(self.v_sim.set, f"{tx.mode}, SNR {snr:+.0f} dB, canal {fading}\n{txt}")

        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------ mise à jour automatique
    def _update_cleanup(self):
        try:
            updater.cleanup()
        except Exception:
            pass

    def update_check(self, quiet=False):
        """Cherche une version plus récente sur GitHub (en tâche de fond)."""
        if quiet and self.conf.get("update_check", True):
            # nouvelle vérification dans 3 h (programme laissé ouvert toute la journée)
            if getattr(self, "_upd_job", None):
                try:
                    self.after_cancel(self._upd_job)
                except tk.TclError:
                    pass
            self._upd_job = self.after(3 * 3600 * 1000, lambda: self.update_check(quiet=True))

        def run():
            try:
                info = updater.check()
            except Exception as e:
                if not quiet:
                    self.ui(messagebox.showinfo, APP, tr("Impossible de vérifier les mises à jour :") + f"\n{tr(str(e))}")
                else:
                    self.ui(self.log, f"Mise à jour : vérification sur GitHub impossible ({e})")
                return
            self.ui(self._update_found, info, quiet)
        threading.Thread(target=run, daemon=True).start()

    def _update_found(self, info, quiet):
        if info.get("pending") and updater.newer(info["version"], VERSION):
            # version Windows 7 : fabriquée quelques minutes après la version normale
            self.log(f"Nouvelle version {info['version']} : l'exe Windows 7 n'est pas encore prêt, "
                     "nouvel essai plus tard.")
            if not quiet:
                messagebox.showinfo(APP, f"La version {info['version']} est en préparation pour Windows 7.\n"
                                         "Réessayez dans une quinzaine de minutes.")
            return
        if updater.newer(info["version"], VERSION):
            self.upd_info = info
            self._update_banner(tr(f"Nouvelle version {info['version']} disponible — cliquez ici pour mettre à jour "
                                   f"(version actuelle : {VERSION})"))
            self.log(f"Nouvelle version {info['version']} disponible sur GitHub.")
        elif not quiet:
            messagebox.showinfo(APP, f"Vous avez la dernière version ({VERSION}).")

    def _update_banner(self, text, color="#ff9f1a"):
        for w in (self.upd_bar, self.upd_lbl, self.upd_close):
            w.configure(bg=color)
        self.upd_lbl.configure(text=text)
        if not self.upd_bar.winfo_ismapped():
            self.upd_bar.pack(side="top", fill="x", before=self._main_pane)

    def _update_click(self):
        info = self.upd_info
        if info is None or self.upd_busy:
            return
        notes = info.get("notes") or ""
        if len(notes) > 900:
            notes = notes[:900] + "…"
        if not updater.frozen() or not info.get("url"):
            # lancé depuis les sources (ou pas d'exe joint) : on ouvre la page de la version
            import webbrowser
            webbrowser.open(info.get("page") or updater.PAGE_URL)
            return
        if self.tx_busy:
            messagebox.showinfo(APP, "Attendez la fin de l'émission pour mettre à jour.")
            return
        size = f" ({info['size'] / 1e6:.0f} Mo)" if info.get("size") else ""
        if not messagebox.askyesno(APP, f"Mettre à jour HFImage {VERSION} → {info['version']}{size} ?\n\n"
                                        f"{notes}\n\nLe programme redémarrera tout seul."):
            return
        self.upd_busy = True
        self._update_banner(tr("Téléchargement de la mise à jour… 0 %"), "#ffd166")

        def prog(f):
            self.ui(self.upd_lbl.configure, {"text": tr(f"Téléchargement de la mise à jour… {int(f * 100)} %")})

        def run():
            try:
                path = updater.download(info, prog)
            except Exception as e:
                self.ui(self._update_failed, e)
                return
            self.ui(self._update_install, path)
        threading.Thread(target=run, daemon=True).start()

    def _update_failed(self, e):
        self.upd_busy = False
        self.log_exc("Mise à jour", e)
        self._update_banner(tr(f"Mise à jour impossible : {e} — cliquez pour réessayer"), "#ff6b6b")

    def _update_install(self, path):
        self._update_banner(tr("Mise à jour téléchargée et vérifiée — redémarrage…"), "#7ed957")
        self.update_idletasks()
        try:
            started = updater.install(path)
        except Exception as e:
            self._update_failed(e)
            return
        if started:
            self.log("Mise à jour installée, redémarrage.")
            self.after(500, self._quit)
        else:
            self.upd_busy = False

    def _zoom_main(self):
        try:
            self.state("zoomed")                  # Windows : plein écran (fenêtre agrandie)
        except tk.TclError:
            try:
                self.attributes("-zoomed", True)
            except tk.TclError:
                pass

    # zones réglables : (volet, côté mesuré) ; « first » = taille de la 1re zone,
    # « last » = taille de la dernière (gardée même si la fenêtre change de taille)
    _LAYOUT = {"main": "first", "left": "last", "right": "last", "rx": "last", "rxside": "first",
               "stlists": "last"}

    def _pane_len(self, p):
        return p.winfo_width() if str(p.cget("orient")) == "horizontal" else p.winfo_height()

    def _save_layout(self):
        """Taille de la fenêtre et des zones, pour la prochaine ouverture."""
        try:
            zoomed = self.state() == "zoomed"
            if not zoomed:
                self.conf["win_geom"] = self.geometry()
            self.conf["win_zoomed"] = zoomed
            lay = {}
            for k, side in self._LAYOUT.items():
                p = self.panes.get(k)
                if p is None or len(p.panes()) < 2:
                    continue
                x, y = p.sash_coord(0)
                pos = x if str(p.cget("orient")) == "horizontal" else y
                lay[k] = pos if side == "first" else self._pane_len(p) - pos
            self.conf["layout"] = lay
            self.conf["detached"] = self.dock.saved()
            self.conf.pop("panes", None)
            with open(CONF_PATH, "w", encoding="utf-8") as f:
                json.dump(self.conf, f, indent=1)
        except Exception:
            pass

    def _restore_layout(self):
        for k, size in (self.conf.get("layout") or {}).items():
            p = self.panes.get(k)
            if p is None or self._LAYOUT.get(k) is None:
                continue
            try:
                n = self._pane_len(p)
                pos = int(size) if self._LAYOUT[k] == "first" else n - int(size)
                pos = max(40, min(n - 40, pos))
                if str(p.cget("orient")) == "horizontal":
                    p.sash_place(0, pos, 0)
                else:
                    p.sash_place(0, 0, pos)
            except (tk.TclError, ValueError, TypeError):
                pass

    def reset_layout(self):
        """Revient aux tailles d'origine (colonne de gauche, listes, journal, historique)."""
        try:
            self.state("normal")
        except tk.TclError:
            pass
        self.dock.attach_all()
        self.v_show_hist.set(True)
        self.v_show_msgs.set(True)
        self._rx_side_apply(save=True)
        self.geometry("1320x880")
        self.conf["layout"] = {"main": 268, "left": 170, "right": 70, "rx": 250, "stlists": 110}
        self.update_idletasks()
        self.after(150, self._restore_layout)
        self.after(400, lambda: self.panes["rxside"].sash_place(
            0, 0, self.panes["rxside"].winfo_height() // 2))

    def _linux_menu(self):
        """Linux, programme téléchargé (un seul fichier) : entrée « HFImage F4GOP » dans le menu
        des applications (Mint, Ubuntu…), mise à jour si le fichier a été déplacé."""
        if sys.platform.startswith("win") or not getattr(sys, "frozen", False) or PROFILE:
            return
        try:
            linux_menu_entry([sys.executable], "HFImage F4GOP", "hfimage-f4gop")
        except Exception as e:
            self._journal(f"Entrée du menu des applications : {e}\n")

    def _set_icon(self):
        """Icône du programme (fenêtre, barre des tâches, toutes les fenêtres filles)."""
        here = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        try:
            ico = os.path.join(here, "hfimage.ico")
            if sys.platform.startswith("win") and os.path.exists(ico):
                self.iconbitmap(default=ico)
            imgs = [tk.PhotoImage(file=os.path.join(here, n)) for n in ("icon64.png", "icon32.png", "icon256.png")
                    if os.path.exists(os.path.join(here, n))]
            if imgs:
                self._icons = imgs                       # gardées en mémoire
                self.iconphoto(True, *imgs)
        except Exception:
            pass

    def open_manual(self, name="HFImage_mode_emploi.pdf"):
        """Ouvre le mode d'emploi PDF (copié dans Documents\\HFImage pour rester ouvrable)."""
        here = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        src = os.path.join(here, name)
        if not os.path.exists(src):
            messagebox.showerror(APP, "Mode d'emploi introuvable.")
            return
        try:
            os.makedirs(DEFAULT_OUT, exist_ok=True)
            dst = os.path.join(DEFAULT_OUT, name)
            if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src):
                shutil.copyfile(src, dst)
        except OSError:
            dst = src
        self._open_path(dst)

    def _quit(self):
        self._closing = True
        self._save_layout()
        self.net_stop()
        self.stop_tx.set()
        try:
            self._rig_close()
        except Exception:
            pass
        if self.rx_stream:
            self.toggle_listen()
        self.destroy()


def selftest(report_path, hyb_test=None):
    """Autotest sans interface : chaîne complète (AVIF -> fontaine -> modem ->
    48 kHz -> bruit -> démodulation) dans les 3 modes. Résultat écrit dans un fichier.
    Usage : HFImage_F4GOP.exe --selftest rapport.txt [ftp://id:mdp@serveur/dossier lien_public]"""
    import urllib.parse
    import channel
    lines = [f"{APP} {VERSION} — autotest {time.strftime('%Y-%m-%d %H:%M:%S')}"]
    ok_all = True
    img = Image.new("RGB", (320, 240))
    px = img.load()
    for y in range(240):
        for x in range(320):
            px[x, y] = (x * 255 // 320, y * 255 // 240, (x * y) % 256)
    for mode, kb, snr in (("DATAC1X", 9000, 12), ("DATAC1", 6000, 8), ("DATAC3", 3000, 2), ("DATAC4", 1500, -2)):
        try:
            data, q, _ = engine.compress(img, 320, kb, "avif")
            tx = engine.Transmission(data, "avif", "F4GOP", mode, 0.1)
            a = channel.apply(tx.audio(), 8000, snr, "none", seed=1)
            card = (audio.upsample(a) * 0.7 * 32767).astype(np.int16)
            got = []
            rx = engine.RxEngine("TEST", os.path.join(os.path.expanduser("~"), "HFImage_selftest"),
                                 on_image=lambda h, p, png, m: got.append(open(p, "rb").read()))
            ds = audio.Downsampler()
            for i in range(0, len(card), 4800):
                rx.process(ds.process(card[i:i + 4800].astype(np.float32) / 32768.0))
            ok = bool(got) and got[0] == data
            ok_all &= ok
            lines.append(f"{mode}: {len(data)} octets, SNR {snr:+d} dB -> {'OK' if ok else 'ÉCHEC'}")
        except Exception as e:
            ok_all = False
            lines.append(f"{mode}: ERREUR {e!r}")
    # mode EasyPal (HamDRM, hamdrm.dll) : émission puis réception d'un fichier
    try:
        ok = hamdrm.selftest(lines.append)
        ok_all &= ok
    except Exception as e:
        ok_all = False
        lines.append(f"HamDRM (EasyPal): ERREUR {e!r}")
    # formats : SVG (rendu resvg + compression) et JPEG
    try:
        svg = (b'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">'
               b'<rect width="200" height="100" fill="#1d3557"/><circle cx="150" cy="50" r="30" fill="#ffd166"/></svg>')
        im = imgfmt.render_svg(svg, 400)
        pk = imgfmt.svg_pack(svg)
        if imgfmt.SVG_OK:
            px = im.getpixel((300, 100))
            ok = im.size == (400, 200) and px[0] > 200 and protocol.detect_format(pk) == "svg"
        else:                                     # version Windows 7 : pas de moteur SVG
            ok = protocol.detect_format(pk) == "svg"
            lines.append("SVG : affichage non disponible (version Windows 7)")
        jpg = engine.compress(im, 200, 3000, "jpeg")[0]
        ok &= protocol.detect_format(jpg) == "jpeg"
        ok_all &= ok
        lines.append(f"SVG / JPEG : rendu {im.size[0]}×{im.size[1]}, SVG {len(pk)} octets, JPEG {len(jpg)} octets "
                     f"-> {'OK' if ok else 'ÉCHEC'}")
    except Exception as e:
        ok_all = False
        lines.append(f"SVG / JPEG : ERREUR {e!r}")
    # présence Internet : le serveur est-il joignable d'ici ? (diagnostic, n'échoue pas le test)
    try:
        import paho.mqtt.client as mqtt
        conf = load_conf()
        host, port = conf.get("net_host") or presence.DEFAULT_HOST, int(conf.get("net_port") or 1883)
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"hfimage-test-{os.getpid()}")
        t0 = time.time()
        c.connect(host, port, keepalive=10)
        c.disconnect()
        lines.append(f"Internet (présence) : {host}:{port} joignable ({(time.time() - t0) * 1000:.0f} ms)")
    except Exception as e:
        lines.append(f"Internet (présence) : {host}:{port} injoignable ({e}) — essayez le port 8883 ou 8000")
    # carte des stations : données Natural Earth présentes et rendu
    try:
        me = {"call": "F4GOP", "pos": protocol.locator_to_latlon("IN98QR")}
        st = [{"call": "DL6MKM", "pos": protocol.locator_to_latlon("JO62"), "ok": True}]
        im = stationmap.render(stationmap.View(*stationmap.VIEWS["Europe"], 400, 260), st, me)
        n = len(stationmap.load()["countries"])
        ok = n > 200 and im.size == (400, 260)
        ok_all &= ok
        lines.append(f"Carte : {n} pays, {len(stationmap.load()['cities'])} villes -> {'OK' if ok else 'ÉCHEC'}")
    except Exception as e:
        ok_all = False
        lines.append(f"Carte : ERREUR {e!r}")
    # inventaire audio / COM : utile pour le diagnostic à distance
    try:
        import sounddevice as S
        lines.append(f"PortAudio : {S.get_portaudio_version()[1]}")
        for i, d in enumerate(S.query_devices()):
            lines.append(f"  {i:2d} {S.query_hostapis(d['hostapi'])['name']:20s} in {d['max_input_channels']} "
                         f"out {d['max_output_channels']} {d['default_samplerate']:.0f} Hz  {d['name']}")
    except Exception as e:
        lines.append(f"Audio : ERREUR {e!r}")
    lines.append("Ports COM : " + (", ".join(f"{p} ({d})" for p, d in audio.ports_list()) or "aucun"))
    try:
        lines.append(f"Poste radio : {len(radio.rig_keys())} entrées (Hamlib {radio.HAMLIB_VERSION}), "
                     f"rigctld : {radio.find_rigctld() or 'non installé'}")
        if not sys.platform.startswith("win"):
            lines.append(f"Système : {platform.platform()} — OmniRig : sans objet (Windows seulement)")
        else:
            try:
                import comtypes.client  # noqa: F401  (OmniRig)
                lines.append("OmniRig : module COM présent")
            except Exception as e:
                lines.append(f"OmniRig : module COM absent ({e})")
    except Exception as e:
        lines.append(f"Poste radio : ERREUR {e}")
    if hyb_test:
        try:
            u = urllib.parse.urlparse(hyb_test[0])
            cfg = {"host": u.hostname, "port": u.port or 21, "user": urllib.parse.unquote(u.username or ""),
                   "password": urllib.parse.unquote(u.password or ""), "dir": u.path.strip("/"),
                   "tls": u.scheme == "ftps", "url": hyb_test[1]}
            url, base = hybrid.test_server(cfg)
            lines.append(f"Hybride : serveur OK ({url})" + ("" if base.rstrip("/") == cfg["url"].rstrip("/")
                                                              else f" — lien public à corriger : {base}"))
        except Exception as e:
            ok_all = False
            lines.append(f"Hybride : ÉCHEC {e}")
    lines.append("RÉSULTAT : " + ("OK" if ok_all else "ÉCHEC"))
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return 0 if ok_all else 1


def audiotest(report_path, name):
    """Joue 1,5 s de tonalité 1 kHz (faible niveau) sur chaque interface Windows
    du périphérique dont le nom contient `name`, et vérifie que le son est
    réellement joué. ATTENTION : sans PTT, mais si le DATA VOX du poste est
    actif, le poste passera en émission 1,5 s par interface.
    Usage : HFImage_F4GOP.exe --audiotest rapport.txt "USB Audio CODEC" """
    import sounddevice as S
    lines = [f"{APP} {VERSION} — test des sorties « {name} » {time.strftime('%Y-%m-%d %H:%M:%S')}"]
    sig = audio.tone(1.5, 1000.0, amp=0.1)
    found = ok_any = False
    for i, d in enumerate(S.query_devices()):
        if d["max_output_channels"] == 0 or name.lower() not in d["name"].lower():
            continue
        found = True
        lab = audio.device_label(S, i)
        t0 = time.time()
        try:
            audio.play(S, i, sig)
            ok_any = True
            lines.append(f"  OK      {lab}  ({time.time() - t0:.1f} s)")
        except Exception as e:
            lines.append(f"  ÉCHEC   {lab}  : {e}")
        time.sleep(0.5)
    if not found:
        lines.append("  aucune sortie ne contient ce nom")
    lines.append("RÉSULTAT : " + ("OK" if ok_any else "ÉCHEC"))
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return 0 if ok_any else 1


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--audiotest":
        sys.exit(audiotest(sys.argv[2], sys.argv[3]))
    if len(sys.argv) >= 3 and sys.argv[1] == "--selftest":
        sys.exit(selftest(sys.argv[2], sys.argv[3:5] if len(sys.argv) >= 5 else None))
    App().mainloop()
