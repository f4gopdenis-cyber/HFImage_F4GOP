#!/usr/bin/env python3
"""HFImage F4GOP — émission / réception d'images numériques en HF.

Onglets : Émission, Réception, Simulation, Réglages.
"""
import io
import json
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
import traceback
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

import numpy as np
from PIL import Image, ImageTk

import audio
import engine
import hybrid
import i18n
import imgfmt
import presence
import gallery
import radio
import radiodlg
import contextlib
import stationmap
import theme
import updater
from i18n import tr
import protocol
import qsl
import shutil
import wavtext
from panel import LED_AMBER, LED_GREEN, LED_OFF, LED_RED, ImageView, StatusPanel
from waterfall import RowMaker, Waterfall
from modem import MODE_BPS, MODE_BW, MODE_FPB
import random
import wave

APP = "HFImage F4GOP"
VERSION = "0.21"
CONF_PATH = os.path.join(os.path.expanduser("~"), ".hfimage.json")
DEFAULT_OUT = os.path.join(os.path.expanduser("~"), "Documents", "HFImage")
DEFAULTS = {
    "callsign": "F4GOP", "mode": "DATAC1X", "width": "auto", "seconds": 120, "fmt": "avif",
    "overhead": 10, "out_dev": "", "in_dev": "", "level": 50,
    "ptt": "VOX", "cat_port": "", "cat_baud": 115200, "cat_cmd": "TX1;",
    "folder": DEFAULT_OUT,
    "hyb_on": False, "hyb_host": "", "hyb_port": 21, "hyb_user": "", "hyb_pass": "",
    "hyb_dir": "hfimage", "hyb_tls": False, "hyb_url": "", "hyb_auto": True,
    "hyb_width": 640, "hyb_kb": 60, "gif_kb": 2000,
    "net_on": True, "net_host": presence.DEFAULT_HOST, "net_port": presence.DEFAULT_PORT,
    "update_check": True,
    "theme": "Vert EasyPal", "theme_color": "#3a8ee6", "font_family": "(par défaut)", "font_size": "Normale",
    "locator": "", "bsr_auto": True, "fix_auto": True, "ack_auto": True, "listen_after": True,
    "cwid": False, "cat_freq": True, "lang": "",
    "wav_volume": 5, "wft_font": "Arial", "wft_neg": False, "wft_text": "",
}
TX_MODES = ["DATAC1X", "DATAC1", "DATAC3", "DATAC4"]
DATA_ACTIONS = {"ask": "Demander", "switch": "Passer en USB-DATA automatiquement",
                "send": "Émettre sans rien dire"}
HEARD_KEEP_S = 2 * 3600     # stations entendues gardées 2 h dans la liste
RING_S = 15 * 60          # Relire RX : 15 dernières minutes gardées en mémoire
PTT_METHODS = ["VOX", "CAT", "RTS", "DTR"]
# taille d'image proposée quand on change de mode
# durée d'émission proposée quand on change de mode (s)
MODE_SEC = {"DATAC1X": 120, "DATAC1": 120, "DATAC3": 120, "DATAC4": 180}
# « original » : le fichier ouvert part tel quel (JPG, PNG, GIF, AVIF, WEBP, SVG compressé)
FORMATS_TX = ["avif", "webp", "jpg", "original"]
ORIGINAL_KINDS = ("jpeg", "png", "gif", "avif", "webp", "svg")
WIDTHS = ["auto", 160, 240, 320, 480, 640, 800, 1024, 1280, 1600, 1920, "originale"]
HYB_WIDTHS = [480, 640, 800, 1024, 1280, 1600, 1920, 2560, "originale"]
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


def load_conf():
    c = dict(DEFAULTS)
    try:
        with open(CONF_PATH, encoding="utf-8") as f:
            saved = json.load(f)
        c.update(saved)
        if "ptt" not in saved:                       # réglages de la v0.3
            c["ptt"] = "CAT" if saved.get("cat_on") else "VOX"
        if saved.get("conf_v", 0) < 10:
            # v0.10 : nouveau mode rapide DATAC1X et 2 min par défaut (images nettes)
            if saved.get("mode", "DATAC1") == "DATAC1" and int(saved.get("seconds", 60)) == 60:
                c["mode"], c["seconds"] = "DATAC1X", 120
            if c.get("fmt") == "jpeg":
                c["fmt"] = "jpg"
        if c.get("fmt") not in FORMATS_TX:
            c["fmt"] = {"jpeg": "jpg"}.get(c.get("fmt"), "avif")
    except Exception:
        pass
    return c


def _fmt_s(sec):
    sec = int(round(sec))
    if sec < 60:
        return f"{sec} s"
    if sec < 3600:
        return f"{sec // 60} min {sec % 60:02d} s"
    return f"{sec // 3600} h {sec % 3600 // 60:02d} min"


class HybridJob:
    """Image prête pour le mode hybride ; `announce` existe après le dépôt FTP."""

    def __init__(self, data, fmt, call):
        self.data, self.fmt, self.call = data, fmt, call
        self.mode = "DATAC3"
        self.announce = None


def sd():
    import sounddevice
    return sounddevice


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP} {VERSION}")
        self.conf = load_conf()
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
        self.net = None             # client de présence Internet
        self.net_ok = False
        self.rxok_sent = set()      # images dont on a déjà confirmé la réception par Internet
        self.pending_fix = {}       # id -> BSR reçus en attente de FIX
        self.bsr_state = {}         # id -> BSR envoyés (réception)
        self.ack_pending = {}       # id -> ACK à envoyer quand l'émetteur aura fini
        self.bsr_target = None
        self.ctl_seen = {}
        self.rig = None
        self.rig_freq = self.rig_mode = None
        self.radio_cfg = radio.from_conf(self.conf)     # poste, CAT, PTT (fenêtre « Poste radio »)
        self.rig_lock = threading.RLock()
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
        self.after(400, self._restore_layout)
        self.after(1500, self._restore_layout)     # une 2e fois, une fois tout affiché
        self.protocol("WM_DELETE_WINDOW", self._quit)
        self.journal_devices()
        self.log(f"{APP} {VERSION} prêt. Images reçues : {self.conf['folder']}")

    # ------------------------------------------------------------------ UI
    def _build(self):
        self.configure(bg=GREEN)
        self.v_call = tk.StringVar(value=self.conf["callsign"])
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
        self.panel = StatusPanel(left)
        self.panel.pack(fill="x")
        self._button_grid(left)
        lpw = tk.PanedWindow(left, orient="vertical", **pw)
        lpw.pack(fill="both", expand=True, pady=(4, 0))
        self.panes["left"] = lpw
        self.wf = Waterfall(lpw, height=200)
        lpw.add(self.wf, minsize=90, stretch="always")
        sbox = tk.Frame(lpw, bg=GREEN)
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
        self.logbox = tk.Text(rpw, height=4, state="disabled", wrap="word", bg="#f4fff4")
        rpw.add(self.logbox, minsize=40, stretch="never", height=70)
        bar = tk.Frame(right, bg=GREEN_DARK)
        bar.pack(fill="x", pady=(2, 0))
        tk.Label(bar, textvariable=self.v_state, bg=GREEN_DARK, fg="white",
                 font=("TkDefaultFont", 9, "bold")).pack(side="left", padx=6)
        self.lb_clock = tk.Label(bar, text="", bg=GREEN_DARK, fg="white")
        self.lb_clock.pack(side="right", padx=6)
        self.lb_freq = tk.Label(bar, text="", bg=GREEN_DARK, fg="#ffe066", font=("TkDefaultFont", 9, "bold"))
        self.lb_freq.pack(side="right", padx=12)

        self._tab_conf()            # fenêtres Réglages et Texte (cachées)
        self._build_text_window()
        self._build_wav_window()
        self._build_wft_window()
        self._menus()
        self._translate_ui()

    # ------------------------------------------------------------------ apparence
    def _apply_look(self, save=True):
        """Thème de couleurs et police choisis dans les Réglages (appliqués tout de suite)."""
        th = self._theme_names.get(self.v_theme.get(), self.v_theme.get()) if hasattr(self, "v_theme") \
            else self.conf.get("theme", "Vert EasyPal")
        fam = self.v_font.get() if hasattr(self, "v_font") else self.conf.get("font_family")
        size = self._size_names.get(self.v_fsize.get(), "Normale") if hasattr(self, "v_fsize") \
            else self.conf.get("font_size", "Normale")
        self.look.set(theme=th if th in theme.THEMES or th == "Personnalisée" else "Vert EasyPal",
                      custom=self.conf.get("theme_color"), family=fam,
                      scale=theme.FONT_SIZES.get(size, 1.0))
        self.conf.update(theme=th, font_family=fam, font_size=size)
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

    def _set_title(self):
        self.title(f"{APP} {VERSION} — {self.v_call.get().strip().upper() or 'NOCALL'}")

    # ---------------------------------------------------------------- menus
    def _menus(self):
        m = tk.Menu(self)
        r = tk.Menu(m, tearoff=0)
        r.add_command(label="Réglages…", command=self.show_settings)
        r.add_separator()
        r.add_command(label="Tester la sortie audio (1 kHz)", command=self.test_audio)
        r.add_command(label="Poste radio…", command=self.radio_dialog)
        r.add_command(label="Vérifier le poste (CAT)", command=self.check_rig)
        r.add_command(label="Tester le PTT (1 s)", command=self.test_ptt)
        r.add_separator()
        r.add_command(label="Enregistrer les réglages", command=self.save_conf)
        r.add_command(label="Ouvrir le journal", command=self.open_journal)
        r.add_separator()
        r.add_command(label="Disposition d'origine des fenêtres", command=self.reset_layout)
        m.add_cascade(label="Réglages", menu=r)
        h = tk.Menu(m, tearoff=0)
        h.add_checkbutton(label="Mode hybride", variable=self.v_hyb, command=self._toggle_hyb_ui)
        h.add_command(label="Tester le serveur", command=self.test_hybrid)
        h.add_checkbutton(label="Télécharger automatiquement", variable=self.v_hauto)
        h.add_command(label="Réglages du serveur…", command=self.show_settings)
        m.add_cascade(label="Hybride", menu=h)
        a = tk.Menu(m, tearoff=0)
        a.add_command(label="Émettre", command=self.transmit)
        a.add_command(label="FIX / Compléter", command=self.send_fix)
        a.add_command(label="Arrêter l'émission", command=lambda: self.stop_tx.set())
        a.add_separator()
        a.add_command(label="BSR (demander la suite)", command=self.send_bsr_manual)
        a.add_command(label="Écoute marche / arrêt", command=self.toggle_listen)
        a.add_separator()
        a.add_command(label="Accord (10 s)", command=self.send_tune)
        a.add_command(label="ID morse", command=self.send_cwid)
        a.add_command(label="Envoi texte…", command=self.show_text)
        a.add_command(label="Texte waterfall…", command=self.show_wft)
        a.add_separator()
        a.add_command(label="Signaler ma présence (QRV)", command=self.send_qrv)
        a.add_command(label="Carte des stations…", command=self.show_map)
        m.add_cascade(label="Action", menu=a)
        i = tk.Menu(m, tearoff=0)
        i.add_command(label="Ouvrir une image…", command=self.open_image)
        i.add_command(label="Carte QSL…", command=self.qsl_dialog)
        i.add_separator()
        i.add_command(label="Image reçue en plein format", command=self._open_full)
        i.add_command(label="Dossier des images reçues", command=self.open_folder)
        i.add_command(label="Galerie des dernières images", command=lambda: self.nb.select(self.gal))
        m.add_cascade(label="Images", menu=i)
        f = tk.Menu(m, tearoff=0)
        f.add_command(label="Enregistrer l'émission en WAV…", command=self.save_wav)
        f.add_command(label="Décoder un fichier WAV…", command=self.decode_wav)
        f.add_command(label="Relire RX (15 dernières min)", command=self.replay_rx)
        f.add_command(label="Fichiers WAV (begin / end)…", command=self.show_wav)
        f.add_command(label="Enregistrement WAVE marche / arrêt", command=self.toggle_record)
        f.add_separator()
        f.add_command(label="Journal des stations (CSV)",
                      command=lambda: self._open_path(os.path.join(DEFAULT_OUT, "stations.csv")))
        m.add_cascade(label="Fichiers", menu=f)
        e = tk.Menu(m, tearoff=0)
        e.add_command(label="Historique des images", command=self._clear_hist)
        e.add_command(label="Messages reçus", command=lambda: self._clear_text(self.msgbox))
        e.add_command(label="Journal des stations", command=lambda: self.tree.delete(*self.tree.get_children()))
        e.add_command(label="Waterfall", command=lambda: self.wf.clear())
        e.add_command(label="Journal à l'écran", command=lambda: self._clear_text(self.logbox))
        m.add_cascade(label="Effacer", menu=e)
        n = tk.Menu(m, tearoff=0)
        n.add_command(label="Rechercher une mise à jour", command=lambda: self.update_check(quiet=False))
        n.add_command(label="Page du programme sur GitHub",
                      command=lambda: __import__("webbrowser").open(f"https://github.com/{updater.REPO}"))
        n.add_separator()
        n.add_command(label="À propos…", command=self._about)
        m.add_cascade(label="Infos", menu=n)
        self.config(menu=m)

    def _about(self):
        messagebox.showinfo(APP, f"{APP} {VERSION}\n\nImages numériques en HF : modem OFDM codec2 "
                                 "(DATAC1X / DATAC1 / DATAC3 / DATAC4, BSR/ACK en DATAC0), code fontaine, "
                                 "mode hybride par Internet.\n\nAutotests :\n"
                                 "  HFImage_F4GOP.exe --selftest rapport.txt\n"
                                 "  HFImage_F4GOP.exe --audiotest test.txt \"USB Audio CODEC\"")

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
        g = tk.Frame(parent, bg=GREEN)
        g.pack(fill="x", pady=(6, 0))
        self.gbtn = {}
        spec = [
            ("tx", "ÉMISSION", self._btn_emission), ("relire", "Relire RX", self.replay_rx),
            ("fix", "FIX", self.send_fix), ("bsr", "BSR", self.send_bsr_manual),
            ("accord", "Accord", self.send_tune), ("id", "ID", self.send_cwid),
            ("texte", "Envoi Texte", self.show_text), ("wave", "WAVE", self.show_wav),
            ("ecoute", "Écoute", self.toggle_listen), ("txtinc", "Txt inclus", self._toggle_txtinc),
            ("log", "Log Station", lambda: self.nb.select(self.tab_stations)), ("qsl", "IMG/QSL", self.qsl_dialog),
            ("image", "Image…", self.open_image), ("hyb", "Hybride", self._toggle_hyb_btn),
            ("reglages", "Réglages", self.show_settings), ("dossier", "Dossier", self.open_folder),
        ]
        for k, (key, text, cmd) in enumerate(spec):
            b = tk.Button(g, text=text, command=cmd, bg="white", activebackground="#e6ffe6",
                          relief="raised", bd=1, font=("TkDefaultFont", 8), padx=1, pady=1)
            b.grid(row=k // 4, column=k % 4, sticky="nsew", padx=1, pady=1)
            self.gbtn[key] = b
        for c in range(4):
            g.columnconfigure(c, weight=1, uniform="b")
        # compatibilité avec le reste du code
        self.btn_listen = self.gbtn["ecoute"]
        self.btn_bsr = self.gbtn["bsr"]


    def _btn_on(self, key, on):
        self.gbtn[key].configure(bg=BTN_ON if on else "white", relief="sunken" if on else "raised")

    def _btn_emission(self):
        if self.tx_busy:
            self.stop_tx.set()
        else:
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

    def _toggle_hyb_ui(self):
        self._btn_on("hyb", self.v_hyb.get())
        self.prepare()

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
        t = tk.Frame(nb, bg="black")
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
        h1 = tk.Frame(side, bg=GREEN)
        side.add(h1, minsize=60, stretch="always")
        tk.Label(h1, text="Historique", bg=GREEN, font=("TkDefaultFont", 9, "bold")).pack(anchor="w", padx=4)
        self.lst = tk.Listbox(h1, height=12)
        self.lst.pack(fill="both", expand=True, padx=4)
        h2 = tk.Frame(side, bg=GREEN)
        side.add(h2, minsize=60, stretch="always")
        tk.Label(h2, text="Messages reçus", bg=GREEN, font=("TkDefaultFont", 9, "bold")).pack(anchor="w", padx=4,
                                                                                              pady=(6, 0))
        self.msgbox = tk.Text(h2, height=8, wrap="word", state="disabled")
        self.msgbox.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.lst.bind("<<ListboxSelect>>", self._hist_select)
        self.lst.bind("<Double-Button-1>", lambda e: self._open_full())
        self.lb_rx.bind("<Double-Button-1>", lambda e: self._open_full())
        self.v_rxstat = tk.StringVar(value="")
        self.v_level = tk.DoubleVar(value=0)
        self.hist = []

    def _tab_tx(self, nb):
        t = tk.Frame(nb, bg="black")
        nb.add(t, text="  TX  ")
        tb = ttk.Frame(t, padding=(6, 4))
        tb.pack(fill="x", side="top")
        self.v_mode = tk.StringVar(value=self.conf["mode"])
        self.v_width = tk.StringVar(value=str(self.conf.get("width", "auto")))
        self.v_sec = tk.IntVar(value=int(self.conf.get("seconds", 60)))
        self.v_fmt = tk.StringVar(value=self.conf["fmt"])
        self.v_over = tk.IntVar(value=self.conf["overhead"])
        r1 = ttk.Frame(tb)
        r1.pack(fill="x")
        ttk.Button(r1, text="Ouvrir une image…", command=self.open_image).pack(side="left", padx=(0, 10))
        widgets = [
            ("Mode", ttk.Combobox(r1, textvariable=self.v_mode, values=TX_MODES, width=8, state="readonly")),
            ("Durée max (s)", ttk.Spinbox(r1, textvariable=self.v_sec, from_=15, to=3600, increment=30, width=6)),
            ("Largeur", ttk.Combobox(r1, textvariable=self.v_width, values=WIDTHS, width=8)),
            ("Format", ttk.Combobox(r1, textvariable=self.v_fmt, values=FORMATS_TX, width=8, state="readonly")),
            ("Redondance %", ttk.Spinbox(r1, textvariable=self.v_over, from_=0, to=200, increment=10, width=4)),
        ]
        for lab, w in widgets:
            ttk.Label(r1, text=lab).pack(side="left", padx=(6, 2))
            w.pack(side="left")
        ttk.Button(r1, text="Recalculer", command=self.prepare).pack(side="left", padx=(10, 0))
        self._radio_widgets = [w for lab, w in widgets if lab != "Format"]
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
                        command=self._toggle_hyb_ui).pack(side="left", padx=12)
        ttk.Checkbutton(r2, text="Texte inclus", variable=self.v_txtinc,
                        command=lambda: (self._btn_on("txtinc", self.v_txtinc.get()), self.prepare())).pack(side="left")
        ttk.Checkbutton(r2, text="ID morse en fin d'émission", variable=self.v_cwid).pack(side="left", padx=12)

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
        ttk.Button(bt, text="▶ Émettre", command=self.transmit).pack(side="left")
        self.btn_comp = ttk.Button(bt, text="+ Compléter", command=lambda: self.transmit(complement=True))
        self.btn_comp.pack(side="left", padx=4)
        ttk.Button(bt, text="■ Arrêter", command=lambda: self.stop_tx.set()).pack(side="left")
        ttk.Button(bt, text="WAV…", command=self.save_wav).pack(side="left", padx=(4, 0))
        info = tk.Frame(t, bg=GREEN)
        info.pack(fill="x", side="bottom")
        self.lb_src_info = tk.Label(info, text="", bg=GREEN, anchor="w", font=("TkDefaultFont", 8))
        self.lb_src_info.pack(side="left", padx=6)
        self.lb_cmp_info = tk.Label(info, text="", bg=GREEN, anchor="w", font=("TkDefaultFont", 9, "bold"))
        self.lb_cmp_info.pack(side="left", padx=12)
        self.lb_cmp = ImageView(t, placeholder="Ouvrez une image (bouton « Image… » ou menu Images)")
        self.lb_cmp.pack(fill="both", expand=True)
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
        self.txt_msg = tk.Text(f, height=8, width=56, wrap="word")
        self.txt_msg.pack(fill="both", expand=True, pady=(2, 6))
        b = ttk.Frame(f)
        b.pack(fill="x")
        ttk.Checkbutton(b, text="Inclure ce texte avec l'image", variable=self.v_txtinc,
                        command=lambda: (self._btn_on("txtinc", self.v_txtinc.get()), self.prepare())).pack(side="left")
        ttk.Button(b, text="Fermer", command=lambda: (w.withdraw(), self.prepare())).pack(side="right")
        ttk.Button(b, text="Envoyer le texte seul", command=lambda: (w.withdraw(), self.send_text())).pack(
            side="right", padx=6)

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
        w.title(f"{APP} — Texte waterfall")
        w.withdraw()
        w.transient(self)
        w.protocol("WM_DELETE_WINDOW", w.withdraw)
        f = ttk.LabelFrame(w, text="Texte Waterfall", padding=8)
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
        b = ttk.Frame(f)
        b.pack(fill="x", pady=(8, 0))
        for i, (txt, cmd) in enumerate((("Émission", self.wft_send), ("Sauve", self.wft_save),
                                        ("Effacer texte", lambda: (self.txt_wft.delete("1.0", "end"),
                                                                   self._wft_preview())),
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

    def _wft_bitmap(self):
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
        name = simpledialog.askstring(APP, tr("Nom du fichier :"), initialvalue="texte_waterfall.wav",
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
        self.win_conf.deiconify()
        self.win_conf.lift()

    def _tab_stations(self, nb):
        t = ttk.Frame(nb, padding=10)
        nb.add(t, text="  Stations  ")
        self.tab_stations = t
        opt = ttk.LabelFrame(t, text="BSR / FIX (demandes de compléments)", padding=6)
        opt.pack(fill="x")
        self.v_bsr_auto = tk.BooleanVar(value=self.conf.get("bsr_auto", True))
        self.v_fix_auto = tk.BooleanVar(value=self.conf.get("fix_auto", True))
        self.v_ack_auto = tk.BooleanVar(value=self.conf.get("ack_auto", True))
        self.v_listen_after = tk.BooleanVar(value=self.conf.get("listen_after", True))
        for i, (txt, v) in enumerate((
                ("En réception : envoyer un BSR automatiquement si l'image est incomplète", self.v_bsr_auto),
                ("En réception : envoyer un accusé (ACK) quand l'image est complète", self.v_ack_auto),
                ("En émission : répondre automatiquement aux BSR par un FIX", self.v_fix_auto),
                ("Écouter après chaque émission (pour recevoir BSR et ACK)", self.v_listen_after))):
            ttk.Checkbutton(opt, text=txt, variable=v).grid(row=i, column=0, sticky="w")
        ttk.Label(opt, text="BSR et ACK partent en DATAC0 (~2 s) quand l'émetteur a fini ; "
                            "un FIX n'envoie que des symboles nouveaux, utiles à toutes les stations.",
                  foreground="#555").grid(row=4, column=0, sticky="w", pady=(4, 0))
        cols = ("heure", "call", "evt", "mode", "snr", "detail")
        self.tree = ttk.Treeview(t, columns=cols, show="headings", height=14)
        for c, title, w in zip(cols, ("Heure UTC", "Indicatif", "Événement", "Mode", "SNR", "Détail"),
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
        box = tk.Frame(parent, bg=GREEN, bd=2, relief="groove")
        box.pack(fill="both", expand=True)
        head = tk.Frame(box, bg=GREEN)
        head.pack(fill="x")
        self.lb_heard = tk.Label(head, text="", bg=GREEN, fg=FG_DARK, anchor="w",
                                 font=("TkDefaultFont", 9, "bold"))
        self.lb_heard.pack(side="left", padx=(4, 0))
        self.lb_rxok = tk.Label(head, text="", bg=GREEN, fg=FG_DARK, anchor="e",
                                font=("TkDefaultFont", 9, "bold"))
        self.lb_rxok.pack(side="right", padx=(0, 4))
        body = tk.Frame(box, bg=GREEN)
        body.pack(fill="both", expand=True, padx=2, pady=(0, 2))
        mono = ("Consolas", 9) if sys.platform.startswith("win") else ("TkFixedFont", 9)
        self.lst_heard = tk.Listbox(body, height=7, width=15, font=mono, activestyle="none",
                                    bg="white", fg="#062e06", selectbackground="#2f9e2f")
        self.lst_heard.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(body, orient="vertical", command=self.lst_heard.yview)
        sb.pack(side="left", fill="y")
        self.lst_heard.configure(yscrollcommand=sb.set)
        self.lst_rxok = tk.Listbox(body, height=7, width=14, font=mono, activestyle="none",
                                   bg="white", fg="#062e06", selectbackground="#2f9e2f")
        self.lst_rxok.pack(side="left", fill="both", padx=(2, 0))
        self.lst_heard.bind("<Double-Button-1>", lambda e: self._heard_detail())
        self.lst_rxok.bind("<Double-Button-1>", lambda e: self._heard_detail(self.lst_rxok))
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Carte des stations…", command=self.show_map)
        menu.add_command(label="Signaler ma présence (QRV)", command=self.send_qrv)
        menu.add_command(label="Vider la liste des stations", command=self._heard_clear)
        for w in (self.lst_heard, self.lst_rxok, self.lb_heard):
            w.bind("<Button-3>", lambda e, m=menu: m.tk_popup(e.x_root, e.y_root))
        self._heard_names, self._rxok_names = [], []
        self._heard_refresh()

    # ------------------------------------------------- présence par Internet (comme EasyPal)
    def net_start(self):
        self.net_stop()
        call = self.v_call.get().strip().upper()
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
        try:
            self.net.start(call, {"loc": self.v_loc.get().strip(), "freq": self.rig_freq,
                                  "mode": self.rig_mode, "state": "RX", "ver": VERSION, "app": "HFImage"})
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

    def _net_station(self, key, d):
        if d is None:
            if self.online.pop(key, None) is not None:
                self._heard_refresh()
            return
        new = key not in self.online
        self.online[key] = dict(d, seen=time.time())
        if d.get("loc"):
            self._remember_loc(str(d["call"]).upper(), d["loc"])
        if new:
            fr = f" — {audio.format_freq(d['freq'], True)}" if d.get("freq") else ""
            self.log(f"En ligne : {d['call']}" + (f" ({d['loc']})" if d.get("loc") else "") + fr)
        self._net_status()
        self._heard_refresh()

    def _net_rxok(self, d):
        call = str(d.get("from", "")).upper()
        iid = d.get("id")
        if d.get("loc"):
            self._remember_loc(call, d["loc"])
        rep = d.get("report")
        rep = int(rep) if isinstance(rep, (int, float)) else None
        mine = iid in self.my_ids or iid in self.sent_images
        first = call not in self.rxok_by_id.get(iid, {})
        # gardé pour toutes les images : si on reçoit (ou a reçu) la même, on verra ces reports
        self._rxok_add(call, rep, iid)
        if mine:
            if first:
                self.log(f"{call} confirme la réception de l'image par Internet"
                         + ("." if rep is None else f" (report {rep:+d} dB)."))
                self.station_event(call, "Rx Ok (Internet)", "", None,
                                   "" if rep is None else f"report {rep:+d} dB")

    def _net_confirm(self, iid, call):
        """Image bien reçue : elle s'affiche dans Rx Ok avec notre report, et on prévient
        l'émetteur (et les autres stations) par Internet."""
        snr = self.snr_by_id.get(iid)
        if iid not in self.my_ids:
            self._rxok_show(iid)
            self._rxok_add(self.v_call.get().strip().upper(), None if snr is None else int(round(snr)), iid)
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
        mycall = self.v_call.get().strip().upper() or "NOCALL"
        myloc = self.v_loc.get().strip()
        me = {"call": mycall, "loc": myloc, "pos": protocol.locator_to_latlon(myloc), "info": tr("votre station")}
        out = []
        on = {str(d["call"]).upper(): d for d in self.online.values()}
        for c in sorted(set(self.heard) | set(self.rxok) | set(on)):
            h = self.heard.get(c, {})
            loc = (on.get(c) or {}).get("loc") or h.get("loc") or self.known_loc.get(c, "")
            info = []
            if c in on:
                d = on[c]
                info.append(tr("en ligne") + (f", {audio.format_freq(d['freq'], True)}" if d.get("freq") else ""))
            if c in self.rxok:
                rep, t = self.rxok[c]
                info.append(tr("a reçu votre image") + ("" if rep is None else f" (report {rep:+d} dB)")
                            + time.strftime(" %H:%M UTC", time.gmtime(t)))
            elif h.get("t"):
                info.append(tr("entendue à {0} UTC").replace("{0}", time.strftime("%H:%M", time.gmtime(h["t"]))))
            if h.get("snr") is not None:
                info.append(f"SNR {h['snr']:+.0f} dB")
            if h.get("freq") and c not in on:
                info.append(audio.format_freq(h["freq"], True))
            # trait depuis notre station seulement vers ceux qui ont reçu NOTRE image
            ok = c in self.rxok and self.rxok_ctx in self.my_ids
            out.append({"call": c, "loc": loc, "pos": protocol.locator_to_latlon(loc), "ok": ok,
                        "info": "   —   ".join(info)})
        return me, out

    def show_map(self, call=None):
        if self.map_win is None or not self.map_win.alive():
            self.map_win = stationmap.MapWindow(self, self._map_data, tr=tr, lang=i18n.get_lang,
                                                on_paste=self._map_to_tx)
            self.look.apply(self.map_win.win)
            self.map_win.win.update_idletasks()
            self.map_win.set_view("*" if (self.rxok or self.heard) else "Europe")
        else:
            self.map_win.win.deiconify()
            self.map_win.win.lift()
        if call:
            self.map_win.win.update_idletasks()
            self.map_win.focus(call)

    def _map_to_tx(self, img):
        """« Coller l'image dans la fenêtre TX » (comme EasyPal) : la carte devient l'image à émettre."""
        self.src_img = img.convert("RGB")
        self.src_raw = self.src_kind = self.src_anim = None
        self.tx = None
        self._show(self.lb_src, "src", self.src_img)
        self._set_text(self.lb_src_info, f"Carte des stations — {img.width}×{img.height}")
        self.nb.select(1)
        self.prepare()
        self.log("Carte des stations placée dans la fenêtre TX.")

    @staticmethod
    def _mhz(hz):
        return f"{hz / 1e6:.3f}".replace(".", ",") if hz else "—"

    def _heard(self, call, snr=None, what="", loc=None):
        """Une station utilisant HFImage a été entendue (image, annonce, BSR, ACK, QRV)."""
        call = (call or "").strip().upper()
        if not call or call == "?" or call == self.v_call.get().strip().upper():
            return
        h = self.heard.setdefault(call, {"loc": ""})
        h.update(t=time.time(), freq=self.rig_freq, what=what)
        if snr is not None:
            h["snr"] = snr
        if loc:
            h["loc"] = loc
            self._remember_loc(call, loc)
        self._heard_refresh()

    def _rxok_add(self, call, report, iid=None):
        """Une station a bien reçu l'image iid (sans iid : l'image affichée)."""
        call = (call or "").strip().upper()
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
        self.lst_heard.delete(0, "end")
        for c in self._heard_names:
            if c in on:
                d = on[c]
                mark = "*" if d.get("state") == "TX" else " "        # * = en émission
                self.lst_heard.insert("end", f"{c:<8}{mark}{self._mhz(d.get('freq'))}")
                self.lst_heard.itemconfigure("end", fg=self._c("#c01818" if d.get("state") == "TX" else "#062e06"))
            else:
                h = self.heard[c]
                self.lst_heard.insert("end", f"{c:<8} {self._mhz(h.get('freq'))}")
                # entendue par radio seulement (pas en ligne) : en gris-vert
                self.lst_heard.itemconfigure("end", fg=self._c("#4a7a4a" if now - h["t"] < 1800 else "#8a9a8a"))
        self._rxok_names = sorted(self.rxok)
        self.lst_rxok.delete(0, "end")
        for c in self._rxok_names:
            rep = self.rxok[c][0]
            self.lst_rxok.insert("end", f"{c:<7}{'' if rep is None else f'{rep:+d} dB':>7}")
        fr = f" - {self._mhz(self.rig_freq)}" if self.rig_freq else ""
        self._set_text(self.lb_heard, tr(f"Stations ({len(self._heard_names)})") + fr)
        self._net_status()
        self._set_text(self.lb_rxok, tr(f"Rx Ok ({len(self.rxok)})"))
        if self.map_win is not None and self.map_win.alive() and self.map_win._drag is None:
            self.map_win.redraw()

    def _heard_detail(self, lst=None):
        lst = lst or self.lst_heard
        sel = lst.curselection()
        names = self._heard_names if lst is self.lst_heard else self._rxok_names
        if not sel or sel[0] >= len(names):
            return
        c = names[sel[0]]
        h = self.heard.get(c, {})
        parts = [c]
        d = next((x for x in self.online.values() if str(x.get("call")).upper() == c), None)
        if d:
            parts.append(tr("en ligne") + (f", {audio.format_freq(d['freq'], True)}" if d.get("freq") else "")
                         + (f" {d['mode']}" if d.get("mode") else "")
                         + (" — " + tr("en émission") if d.get("state") == "TX" else ""))
        loc = h.get("loc") or self.known_loc.get(c)
        if loc:
            parts.append(loc)
        if h.get("t"):
            parts.append(tr("entendue à {0} UTC").replace("{0}", time.strftime("%H:%M", time.gmtime(h["t"]))))
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
        call = self.v_call.get().strip().upper()
        if not call:
            messagebox.showinfo(APP, "Indiquez d'abord votre indicatif (Réglages).")
            return
        if self.send_control(protocol.qrv_frame(call, self.v_loc.get()), "présence (QRV)"):
            self.station_event(call, "Présence (QRV) envoyée", "DATAC0")

    def station_event(self, call, evt, mode="", snr=None, detail=""):
        """Ajoute une ligne au journal des stations (écran + stations.csv)."""
        hh = time.strftime("%H:%M:%S", time.gmtime())
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
        t = ttk.Frame(nb, padding=10)
        nb.add(t, text="  Simulation  ")
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
        t = ttk.Frame(win, padding=10)
        t.pack(fill="both", expand=True)
        colL = ttk.Frame(t)
        colL.pack(side="left", fill="both", expand=True, padx=(0, 6))
        st = ttk.LabelFrame(colL, text="Station", padding=8)
        st.pack(fill="x", pady=(0, 10))
        ttk.Label(st, text="Indicatif").grid(row=0, column=0, sticky="w")
        ttk.Entry(st, textvariable=self.v_call, width=12).grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(st, text="Locator").grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Entry(st, textvariable=self.v_loc, width=8).grid(row=0, column=3, sticky="w", padx=6)
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
        ttk.Button(bf, text="Actualiser", command=self._fill_devices).pack(side="left")
        ttk.Button(bf, text="Tester la sortie (1 kHz)", command=self.test_audio).pack(side="left", padx=6)
        ttk.Label(g, text="Kenwood : « Haut-parleurs (USB Audio CODEC) » et\n"
                          "« Microphone (USB Audio CODEC) », de préférence en [MME].\n"
                          "Réglez le niveau pour que l'ALC ne bouge pas.",
                  foreground="#555", justify="left").grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))

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
        self.v_dataact = tk.StringVar(value=tr(DATA_ACTIONS.get(self.conf.get("data_action", "ask"), DATA_ACTIONS["ask"])))
        cbd = ttk.Combobox(da, textvariable=self.v_dataact, values=list(self._data_act_names), state="readonly", width=30)
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
        ttk.Button(h, text="Tester le serveur", command=self.test_hybrid).grid(
            row=10, column=0, sticky="w", pady=(6, 0))
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
        self.v_fsize = tk.StringVar(value=tr(self.conf.get("font_size", "Normale")))
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
                           "Port 1883 bloqué par un pare-feu ? Essayez 8883 (chiffré) ou 8000 (web).",
                  foreground="#555", justify="left").grid(row=3, column=0, columnspan=5, sticky="w", pady=(4, 0))

        d = ttk.LabelFrame(colR, text="Dossier des images reçues", padding=8)
        d.pack(fill="x", pady=10)
        self.v_folder = tk.StringVar(value=self.conf["folder"])
        ttk.Entry(d, textvariable=self.v_folder, width=40).pack(side="left")
        ttk.Button(d, text="…", width=3, command=self._pick_folder).pack(side="left", padx=4)

        bb = ttk.Frame(colR)
        bb.pack(fill="x")
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

    def log(self, msg):
        line = time.strftime("%H:%M:%S ") + tr(msg) + "\n"
        self.logbox.configure(state="normal")
        self.logbox.insert("end", line)
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
                 f"Windows : {sys.platform} {sys.version.split()[0]}"]
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
        if tx is not None and not isinstance(tx, HybridJob):
            self.panel.set_cell("Total", "TX", str(tx.sender.K))
            self.panel.set_cell("Segs OK", "TX", str(tx.sender.sent))
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
        if radio.cat_signature(old) != radio.cat_signature(cfg):
            self._rig_close()
            self._rig_kick.set()

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
            if self.rig is None or self.rig._sig != radio.cat_signature(cfg):
                if time.time() - last_err < 10 and not self._rig_kick.is_set():
                    self._rig_kick.wait(1)
                    continue
                try:
                    self._rig_open()
                    last_msg = ""
                except Exception as e:
                    last_err = time.time()
                    if str(e) != last_msg:
                        last_msg = str(e)
                        self.ui(self.log, f"Fréquence non lue : {e}")
                    continue
            r = self.rig
            if r is None:
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
                if self.rig is r and not self._rig_hold:
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

    def _clock(self):
        self.lb_clock.configure(text=time.strftime("%H:%M:%S UTC", time.gmtime()))
        # liste des stations : fréquence affichée et couleurs selon l'ancienneté
        fr = self.rig_freq
        if fr != getattr(self, "_heard_fr", None) or int(time.time()) % 30 == 0:
            self._heard_fr = fr
            self._heard_refresh()
        # présence Internet : republiée à chaque changement (fréquence, émission…) et chaque minute
        if self.net is not None:
            st = (fr, self.rig_mode, "TX" if self.tx_busy else "RX", self.v_loc.get().strip(),
                  self.v_call.get().strip().upper())
            now = time.time()
            if st != getattr(self, "_net_st", None) or now - getattr(self, "_net_t", 0) > 60:
                if st[4] and st[4] != self.net.call:
                    self.net_start()                         # indicatif changé : nouvelle présence
                else:
                    self._net_st, self._net_t = st, now
                    self.net.update(freq=fr, mode=self.rig_mode, state=st[2], loc=st[3])
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
                P.set_call(s["info"]["call"] if s["info"]["call"] != "?" else P.call.cget("text"))
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
        try:
            while True:
                fn, a = self.uiq.get_nowait()
                fn(*a)
        except queue.Empty:
            pass
        self.after(100, self._poll)

    API_ORDER = {"MME": 0, "Windows DirectSound": 1, "Windows WASAPI": 2}

    def _fill_devices(self):
        try:
            devs = sd().query_devices()
            hostapis = sd().query_hostapis()
        except Exception as e:
            self.log(f"Audio indisponible : {e}")
            devs, hostapis = [], []
        outs, ins = [], []
        for i, d in enumerate(devs):
            api = hostapis[d["hostapi"]]["name"]
            if api == "Windows WDM-KS":          # souvent muet ou exclusif : on l'écarte
                continue
            entry = (self.API_ORDER.get(api, 3), i, f"{i}: {d['name']} [{api}]")
            if d["max_output_channels"] > 0:
                outs.append(entry)
            if d["max_input_channels"] > 0:
                ins.append(entry)
        self.cb_out["values"] = [e[2] for e in sorted(outs)]
        self.cb_in["values"] = [e[2] for e in sorted(ins)]

    @staticmethod
    def _dev_index(s):
        """Retrouve le périphérique par son nom et son API (les numéros changent
        quand on branche/débranche un appareil USB), sinon par son numéro."""
        if not s:
            return None
        idx, _, label = s.partition(": ")
        try:
            hostapis = sd().query_hostapis()
            for i, d in enumerate(sd().query_devices()):
                if f"{d['name']} [{hostapis[d['hostapi']]['name']}]" == label:
                    return i
        except Exception:
            pass
        return int(idx)

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
                callsign=self.v_call.get().strip().upper(), mode=self.v_mode.get(),
                width=self.v_width.get(), seconds=int(self.v_sec.get()),
                fmt=self.v_fmt.get(), overhead=int(self.v_over.get()), conf_v=10,
                out_dev=self.v_out.get(), in_dev=self.v_in.get(), level=int(self.v_lvl.get()),
                radio=self.radio_cfg,
                folder=self.v_folder.get(),
                hyb_on=bool(self.v_hyb.get()), hyb_host=self.v_hhost.get().strip(),
                hyb_port=int(self.v_hport.get() or 21), hyb_user=self.v_huser.get().strip(),
                hyb_pass=hybrid.protect(self.v_hpass.get()), hyb_dir=self.v_hdir.get().strip(),
                hyb_tls=bool(self.v_htls.get()), hyb_url=self.v_hurl.get().strip(),
                hyb_auto=bool(self.v_hauto.get()), hyb_width=self.v_hwidth.get(),
                preview=bool(self.v_prev.get()), locator=self.v_loc.get().strip().upper(),
                bsr_auto=bool(self.v_bsr_auto.get()), fix_auto=bool(self.v_fix_auto.get()),
                ack_auto=bool(self.v_ack_auto.get()), listen_after=bool(self.v_listen_after.get()),
                cwid=bool(self.v_cwid.get()), lang=i18n.get_lang(),
                wav_volume=int(self.v_wavvol.get()), wft_font=self.v_wftfont.get(),
                wft_neg=bool(self.v_wftneg.get()), wft_text=self.txt_wft.get("1.0", "end").strip(),
                hyb_kb=float(self.v_hkb.get()), gif_kb=float(self.v_gifkb.get()),
                net_on=bool(self.v_net.get()), net_host=self.v_nethost.get().strip() or presence.DEFAULT_HOST,
                net_port=int(self.v_netport.get() or presence.DEFAULT_PORT))
            for k in ("cat_on", "ptt", "cat_port", "cat_baud", "cat_cmd", "cat_freq"):
                self.conf.pop(k, None)              # anciens réglages : repris dans « radio »
            with open(CONF_PATH, "w", encoding="utf-8") as f:
                json.dump(self.conf, f, indent=1)
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

    def test_hybrid(self):
        cfg = self._hyb_cfg()
        self.log(f"Test du serveur {cfg['host']}…")

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

    # -------------------------------------------------------------- émission
    def open_image(self):
        p = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.svg *.svgz *.bmp *.gif *.webp *.avif *.tif *.tiff"),
                                                  ("JPEG", "*.jpg *.jpeg"), ("SVG", "*.svg *.svgz"),
                                                  ("Tous", "*.*")])
        if not p:
            return
        self.load_image(p)

    def load_image(self, p):
        try:
            self.src_img, self.src_raw, self.src_kind = imgfmt.load_source(p)
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
        self.v_sec.set(MODE_SEC[self.v_mode.get()])
        self.prepare()

    def prepare(self):
        """Fait tenir l'image dans la durée demandée : calcule le budget en octets
        pour le mode et la redondance, puis la taille/qualité qui y entrent."""
        hyb = bool(self.v_hyb.get())
        for w in getattr(self, "_radio_widgets", []):     # sans objet en hybride
            w.configure(state="disabled" if hyb else
                        ("readonly" if isinstance(w, ttk.Combobox) and w is self._radio_widgets[0] else "normal"))
        if self.src_img is None or self.tx_busy:
            return
        if hyb:
            return self._prepare_hybrid()
        try:
            mode, width, fmt = self.v_mode.get(), self.v_width.get(), self._fmt()
            seconds = int(float(self.v_sec.get()))
            over = int(self.v_over.get()) / 100
        except (tk.TclError, ValueError):
            return
        if fmt == "original" and (self.src_raw is None or self.src_kind not in ORIGINAL_KINDS):
            fmt = "jpeg"                      # carte QSL, BMP, TIFF… : réencodé en JPEG
        pfmt = fmt if fmt in ("avif", "webp") else "avif"
        # aperçu rapide : seulement pour les émissions longues, pris sur la durée totale
        preview = None
        if self.v_prev.get() and seconds >= PREVIEW_MIN_S:
            w = {"DATAC1X": 200, "DATAC1": 160, "DATAC3": 128, "DATAC4": 96}[mode]
            preview = engine.compress(self.src_img, w, PREVIEW_BYTES[mode], pfmt)[0]
            seconds_main = seconds - engine.Transmission(preview, pfmt, "X", mode, 0.25).estimate_s() + 0.7
        else:
            seconds_main = seconds
        budget = engine.max_bytes_for(mode, seconds_main, over)
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            if fmt == "original":
                data, fmt = self._payload(fmt)
                q, size = None, (self.src_img.width, self.src_img.height)
            elif width == "auto":
                data, q, size = engine.compress_auto(self.src_img, budget, fmt)
            else:
                data, q, size = engine.compress(self.src_img, width, budget, fmt)
        finally:
            self.config(cursor="")
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
        call = self.v_call.get().strip().upper() or "NOCALL"
        text = self.txt_msg.get("1.0", "end").strip() if self.v_txtinc.get() else ""
        if text:
            data = protocol.pack_text(text, data)
        key = (data, fmt, call, mode, over, preview)
        if self.tx is None or getattr(self.tx, "key", None) != key:
            # nouvelle image ou nouveaux réglages ; sinon on garde l'émetteur pour que
            # « Compléter » et les réémissions envoient des symboles jamais émis
            self.tx = engine.Transmission(data, "hft" if text else fmt, call, mode, over, preview=preview)
            self.tx.key = key
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
        lines = [f"Mode {mode} (~{MODE_BPS[mode]} bit/s)",
                 f"{self.tx.sender.K} symboles de {self.tx.sender.T} octets",
                 f"Durée d'émission : {_fmt_s(est)}"]
        if preview:
            lines.append(f"Aperçu reçu après ~{self.tx.preview_s():.0f} s")
        if q is not None and q < 35:
            # combien de temps pour une qualité correcte à cette taille ?
            need = engine.bytes_for_quality(self.src_img, size[0], 45, fmt)
            t_need = seconds
            while engine.max_bytes_for(mode, t_need, over) < need and t_need < 7200:
                t_need += 15
            lines.append(f"Qualité faible (q{q}). Pour {size[0]} px en bonne qualité : "
                         f"~{_fmt_s(t_need)}, ou réduisez la largeur.")
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
        if anim and fmt != "original":
            self.v_fmt.set("original")         # un GIF animé part tel quel (animation gardée)
            fmt = "original"
        if fmt == "original" and (self.src_raw is None or self.src_kind not in ORIGINAL_KINDS):
            fmt = "jpeg"
        how = ""
        if anim:
            try:
                limit = int(float(self.v_gifkb.get()) * 1000)
            except (tk.TclError, ValueError):
                limit = 2_000_000
            ck = (id(self.src_raw), limit)
            if ck not in self._gif_cache:
                self.config(cursor="watch")
                self.update_idletasks()
                try:
                    self._gif_cache = {ck: imgfmt.gif_shrink(self.src_raw, limit)}
                finally:
                    self.config(cursor="")
            data, how = self._gif_cache[ck]
            fmt, q = "gif", None
            im0 = Image.open(io.BytesIO(data))
            size = im0.size
        elif fmt == "original":
            data, fmt = self._payload(fmt, hybrid=True)
            q, size = None, (self.src_img.width, self.src_img.height)
        else:
            data, q, size = engine.compress(self.src_img, width, int(kb * 1000), fmt)
        call = self.v_call.get().strip().upper() or "NOCALL"
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
        srv = self.v_hurl.get().strip() or "(lien public non réglé)"
        self.v_txinfo.set(f"Mode hybride\nImage déposée par FTP sur :\n{srv}\n"
                          f"Annonce radio : ~11 s (DATAC3)")
        self._update_comp()

    def _update_comp(self):
        if isinstance(self.tx, HybridJob):
            if self.tx.announce is not None:
                self._set_text(self.btn_comp, f"↻  Répéter l'annonce ({self.tx.announce.estimate_s():.0f} s)")
            else:
                self._set_text(self.btn_comp, "↻  Répéter l'annonce")
            return
        if self.tx:
            n = self.tx.complement_size()
            self._set_text(self.btn_comp, f"+  Compléter ({n} symboles, {self.tx.estimate_s(n):.0f} s)")

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
                   cwid=bool(self.v_cwid.get()), call=self.v_call.get().strip().upper() or "NOCALL")
        was_listening = self.rx_stream is not None
        if was_listening:
            self.toggle_listen(quiet=True)     # semi-duplex : on coupe la réception pendant l'émission
        job["relisten"] = was_listening or (bool(self.v_listen_after.get()) and bool(self.v_in.get())
                                            and job["kind"] in ("image", "text", "hybrid", "wav", "wftext"))
        self.tx_busy = True
        self.stop_tx.clear()
        self.v_state.set("ÉMISSION EN COURS")
        self._set_text(self.gbtn["tx"], "STOP")
        self.gbtn["tx"].configure(bg="#ff6b6b", activebackground="#ff8f8f")
        if job["kind"] in ("image", "text", "hybrid"):
            self.nb.select(1)
        threading.Thread(target=self._tx_thread, args=(job,), daemon=True).start()
        return True

    def transmit(self, complement=False, extra=None, tx=None, quiet=False):
        tx = tx or self.tx
        if not tx or self.tx_busy:
            if not tx and not quiet:
                messagebox.showinfo(APP, "Ouvrez d'abord une image.")
            return False
        job = {"kind": "image", "tx": tx, "complement": complement, "extra": extra}
        if isinstance(tx, HybridJob):
            job["kind"] = "hybrid"
            if complement and tx.announce is None:
                messagebox.showinfo(APP, "Rien à répéter : émettez d'abord l'image.")
                return False
            if not complement:
                cfg = self._hyb_cfg()
                if not cfg["host"] or not cfg["url"]:
                    messagebox.showinfo(APP, "Mode hybride : renseignez le serveur FTP et le lien "
                                             "public dans l'onglet Réglages.")
                    return False
                job["cfg"] = cfg
        else:
            self.sent_images[tx.image_id] = tx
            self.my_ids.add(tx.image_id)
        if not complement:
            # nouvelle image : nouvelle liste Rx Ok (l'id d'une annonce hybride est connu plus tard)
            self._rxok_reset(None if isinstance(tx, HybridJob) else tx.image_id)
        return self._start_job(job, quiet)

    def send_text(self):
        text = self.txt_msg.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo(APP, "Écrivez d'abord le texte à envoyer.")
            return
        call = self.v_call.get().strip().upper() or "NOCALL"
        mode = self.v_mode.get()
        tx = engine.Transmission(protocol.pack_text(text), "hft", call, mode, 0.25)
        self.sent_images[tx.image_id] = tx
        self.log(f"Texte : {len(text)} caractères, {mode}, ~{_fmt_s(tx.estimate_s())}")
        self._start_job({"kind": "text", "tx": tx, "complement": False, "extra": None})

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

    def _check_rig_before_tx(self, cfg):
        """Avant d'émettre : liaison CAT, mode du poste (réglage « Mode », ou contrôle du mode DATA)."""
        kind = radio.rig_entry(cfg["rig"])["kind"]
        if kind == "none":
            return True
        try:
            r = self._rig_open()
            if r is None:
                return True
            if cfg.get("set_mode") in ("usb", "data"):
                m = r.mode() or ""
                want_data = cfg["set_mode"] == "data"
                if (r.is_data(m) if want_data else m.upper() == "USB"):
                    return True
                msg, ok = r.set_mode(cfg["set_mode"])
                self.log(msg)
                if not ok:
                    return messagebox.askyesno(APP, msg + "\n\nÉmettre quand même ?")
                return True
            if cfg["ptt"] != "CAT" or cfg.get("tx_audio") != "rear":
                return True
            txt, ok = self._rig_status(r)
        except Exception as e:
            self.log_exc("Poste (CAT)", e)
            if cfg["ptt"] != "CAT":
                return True                          # PTT sans CAT : on émet quand même
            messagebox.showerror(APP, f"PTT par CAT impossible :\n{e}")
            return False
        self.log(txt)
        if ok is False:
            act = self.conf.get("data_action", "ask")
            if act not in ("switch", "send"):
                act, remember = self._ask_data_mode(txt)
                if remember and act in ("switch", "send"):
                    self.conf["data_action"] = act
                    if hasattr(self, "v_dataact"):
                        self.v_dataact.set(tr(DATA_ACTIONS[act]))
                    self._save_conf_file()
            if act == "cancel":
                return False
            if act == "switch":
                try:
                    msg, ok2 = r.set_mode("data")
                except Exception as e:
                    msg, ok2 = f"Passage en DATA impossible : {e}", False
                self.log(msg)
                if not ok2:
                    return messagebox.askyesno(APP, msg + "\n\nÉmettre quand même ?")
        return True

    def _ask_data_mode(self, txt):
        """Poste pas en DATA : passer en USB-DATA, émettre quand même ou annuler,
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

        first = ttk.Button(b, text="Passer en USB-DATA et émettre", command=lambda: done("switch"))
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
        tx = job["tx"]
        if kind == "hybrid":
            if not job["complement"]:
                cfg = job["cfg"]
                name = hybrid.remote_name(tx.call, imgfmt.ext_for(tx.fmt))
                self.ui(self.log, f"Hybride : dépôt de {len(tx.data)} octets sur {cfg['host']}…")
                hybrid.upload(cfg, name, tx.data,
                              progress=lambda f: self.ui(self.pb_tx.configure, {"value": 100 * f}))
                # on vérifie que l'image est bien lisible par le lien public AVANT d'émettre
                url, base = hybrid.verify_public(cfg, name, tx.data)
                if base.rstrip("/") != cfg["url"].rstrip("/"):
                    self.ui(self._fix_public_url, base)
                self.ui(self.log, f"Hybride : image en ligne et vérifiée : {url}")
                tx.announce = engine.HybridTransmission(tx.data, tx.fmt, tx.call, url)
                self.my_ids.add(tx.announce.image_id)
                self.ui(self._rxok_show, tx.announce.image_id)
            modem, frames, mode = tx.announce.modem, tx.announce.frames(), tx.announce.mode
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
        ptt = None
        try:
            make_chunks, dur, mode, what = self._job_audio(job)
            if mode:
                self.ui(self.wf.mark_mode, mode)
            self.ui(self.log, f"Émission {what} : {_fmt_s(dur)}")
            self.ui(self._panel_tx, job, mode)
            cfg = job["ptt"]
            if cfg["ptt"] != "VOX":
                rig = None
                if cfg["ptt"] == "CAT" or radio.rig_entry(cfg["rig"])["kind"] != "none":
                    try:
                        rig = self._rig_open()
                    except Exception:
                        if cfg["ptt"] == "CAT":
                            raise
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
                    ptt.close()
                except Exception:
                    pass
            self.ui(self._tx_done, job["relisten"])

    def _play_fallback(self, player, dev_label):
        """Joue sur la sortie choisie ; si elle échoue ou reste muette, essaie le
        même périphérique par les autres interfaces Windows (MME, WASAPI,
        DirectSound) et garde celle qui marche."""
        S = sd()
        dev = self._dev_index(dev_label)
        tried, errors = [dev] + audio.same_device_other_apis(S, dev, output=True), []
        for k, d in enumerate(tried):
            try:
                ok = player(S, d)
                if k > 0:
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
        self.gbtn["tx"].configure(bg="white", activebackground="#e6ffe6")
        self.pb_tx.configure(value=0)
        self.v_state.set("Réception arrêtée")
        self.log("Fin d'émission.")
        self.panel.set_cell("Position", "TX", tr("terminé"))
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
        call = self.v_call.get().strip().upper() or "NOCALL"
        eng = engine.RxEngine(call, self.v_folder.get(),
                              on_image=lambda *a: self.ui(self._got_image, *a),
                              on_status=lambda st: self.ui(self._rx_status, st),
                              on_ident=lambda *a: self.ui(self._got_ident, *a))
        eng.on_hybrid = lambda h, m: self.ui(self._hybrid_announce, eng, h, m)
        eng.on_control = lambda *a: self.ui(self._on_control, *a)
        return eng

    def _on_control(self, kind, iid, call, need, snr):
        """BSR (NACK), ACK ou présence (QRV) entendu (chaque trame est émise 2 fois :
        on dédoublonne)."""
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
            if mine:
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

    def _fix_due(self):
        """FIX automatique : quelques secondes après le premier BSR (pour regrouper
        les demandes de plusieurs stations), on envoie le maximum demandé."""
        now = time.time()
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
        if not inc:
            messagebox.showinfo(APP, "Aucune image incomplète.")
            return
        iid, got, K, end, age, mode, call = max(inc, key=lambda r: -r[4])
        if self.send_control(eng.rcv.nack(iid), f"BSR à {call} ({got}/{K} symboles)"):
            self.station_event(call, f"BSR envoyé : {got}/{K}", mode, None, f"image {iid:04X}")

    def _hybrid_announce(self, eng, hyb, mode):
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
        dev0 = self._dev_index(self.v_in.get())
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
                y = ds.process(rs.process(x))
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

        threading.Thread(target=worker, daemon=True).start()
        self._set_text(self.btn_listen, "Écoute ON")
        self._btn_on("ecoute", True)
        self.v_state.set("RÉCEPTION")
        if not quiet:
            self.log("Écoute démarrée (DATAC1X / DATAC1 / DATAC3 / DATAC4 + BSR/ACK en DATAC0).")

    def decode_wav(self):
        p = filedialog.askopenfilename(filetypes=[("WAV", "*.wav"), ("Tous", "*.*")])
        if not p:
            return
        self.log(f"Décodage de {os.path.basename(p)}…")
        eng = self._new_engine()

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
                n = len(eng.rcv.done)
                h = len(eng.hyb_seen)
                self.ui(self.log, f"Fichier traité : {n} image(s) reçue(s), {eng.last['frames']} trames valides."
                        + (f" {h} annonce(s) hybride(s)." if h else ""))
            except Exception as e:
                self.ui(self.log, f"Erreur de décodage : {e}")

        threading.Thread(target=run, daemon=True).start()

    def _rx_status(self, st):
        self.wf.mark_mode(st["mode"])
        if st.get("call") and st["mode"] != "DATAC0":
            self.panel.set_call(st["call"])
        prog = st.get("progress")
        txt = f"Mode {st['mode']}  —  SNR {st['snr']:.1f} dB\nTrames valides : {st['frames']}"
        if st.get("call"):
            txt += f"\nDe : {st['call']}"
        self.v_rxstat.set(txt)
        if prog:
            got, K = prog
            self.pb_rx.configure(value=100 * min(got, K) / K)
            self.v_rxstat.set(txt + f"\nImage en cours : {min(got, K)} / {K} symboles "
                                    f"({100 * min(got, K) // K} %)")

    def _got_image(self, hdr, path, png, mode):
        self.pb_rx.configure(value=100)
        who = hdr["call"] if hdr["call"] != "?" else "(indicatif à venir)"
        if hdr.get("text"):
            self._show_message(hdr.get("call"), hdr["text"])
        kind = "Aperçu reçu" if hdr.get("preview") else ("Texte reçu" if hdr.get("fmt") == "txt" else "Image reçue")
        snr = self.rx_engine.last.get("snr") if self.rx_engine else None
        if snr is not None:
            self.snr_by_id[hdr["id"]] = snr
        self.station_event(hdr.get("call"), kind + (" (hybride)" if hdr.get("hybrid") else ""), mode, snr,
                           f"{hdr['size']} octets")
        self._heard(hdr.get("call"), snr, kind, hdr.get("loc"))
        if not hdr.get("preview") and hdr.get("fmt") != "txt":
            self._net_confirm(hdr["id"], hdr.get("call"))
        if (not hdr.get("preview") and self.v_ack_auto.get() and self.rx_stream is not None
                and hdr.get("fmt") != "txt"):
            act = self.rx_engine.activity.get(hdr["id"], {}) if self.rx_engine else {}
            self.ack_pending[hdr["id"]] = {"call": hdr.get("call"), "end_at": act.get("end", 0)}
            if hdr.get("hybrid"):
                # l'annonce hybride est répétée 3 fois (~11 s) : on attend qu'elle soit finie
                self.ack_pending[hdr["id"]]["wait_until"] = time.time() + 12
        self.log(f"{kind} {who} ({mode}, {hdr['size']} octets) : {os.path.basename(path)}")
        if hdr.get("preview"):
            mode = mode + " aperçu"
        if png:
            im, anim = self._show_rx(path, png)
            self._set_text(self.lb_rx_info, f"{os.path.basename(path)}   —   {hdr['call']}   —   {mode}   —   "
                                           f"{im.width}×{im.height}   —   {hdr['size'] / 1000:.1f} K" + anim)
            if not self.tx_busy:
                self.nb.select(0)
            if not hdr.get("preview") and os.sep + "relecture" + os.sep not in path:
                self._gallery_add("rx", hdr.get("call"), mode, path, png, hdr.get("size"))
        self.hist.insert(0, (hdr, path, png, mode))
        self.lst.insert(0, f"{time.strftime('%H:%M')}  {hdr['call']:8s} {mode}  {hdr['size']} o")

    def _show_rx(self, path, png):
        """Affiche une image reçue ; un GIF animé est joué en boucle.
        -> (première image, texte en plus pour la barre d'info)."""
        im = Image.open(png)
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
        self.msgbox.insert("1.0", f"[{time.strftime('%H:%M', time.gmtime())} UTC] {call or '?'} : {text}\n")
        self.msgbox.configure(state="disabled")
        self.log(f"Message de {call or '?'} : {text[:80]}")

    def _got_ident(self, info, path, png):
        """L'indicatif est arrivé (trame d'identification de fin) : mise à jour."""
        if info["id"] in self.ack_pending:
            self.ack_pending[info["id"]]["call"] = info["call"]
        self._heard(info.get("call"), self.snr_by_id.get(info["id"]), "Image reçue", info.get("loc"))
        if not info.get("preview") and info.get("fmt") != "txt":
            self._net_confirm(info["id"], info.get("call"))
        if info["id"] in self.snr_by_id and info.get("call") not in (None, "?"):
            self.snr_by_call[info["call"]] = self.snr_by_id[info["id"]]
        if info.get("text"):
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
            self.ui(self.log, f"Relecture terminée : {len(eng.rcv.done)} élément(s) décodé(s) "
                              f"(dossier « relecture »).")

        threading.Thread(target=run, daemon=True).start()

    def qsl_dialog(self):
        win = tk.Toplevel(self)
        win.title("Carte QSL")
        win.transient(self)
        fields = {}
        now = time.strftime("%Y-%m-%d %H:%M", time.gmtime())
        last = ""
        for iid in self.tree.get_children():          # dernière station identifiée
            c = self.tree.item(iid, "values")[1]
            if c and c != "?" and c != self.v_call.get().strip().upper():
                last = c
                break
        freq = audio.format_freq(self.rig_freq, True) if self.rig_freq else self.conf.get("qsl_freq", "14.233 MHz")

        def report_for(call):
            snr = self.snr_by_call.get(call.strip().upper())
            return f"SNR {snr:+.0f} dB" if snr is not None else ""

        for i, (key, lab, val) in enumerate((("to", "Indicatif du correspondant", last),
                                             ("utc", "Date / heure UTC", now),
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

        def reset_style():
            style.update(qsl.DEFAULT_STYLE)
            v_font.set(style["font"]); v_size.set(style["call_size"]); v_alpha.set(style["band_alpha"])
            for k, b in swatches.items():
                b.configure(bg=style[k])
            refresh()

        ttk.Button(sf, text="Style d'origine", command=reset_style).grid(row=5, column=0, columnspan=4,
                                                                        sticky="w", pady=(6, 0))
        # ---- aperçu en direct
        pv = tk.Canvas(win, width=480, height=300, bg="#000", highlightthickness=0)
        pv.grid(row=0, column=2, rowspan=8, padx=8, pady=8, sticky="n")
        prev = {"job": None, "ph": None}

        def current_style():
            style.update(font=v_font.get(), call_size=int(v_size.get()), band_alpha=int(v_alpha.get()))
            return dict(style)

        def build():
            return qsl.make_card(bg["img"], self.v_call.get().strip() or "NOCALL", self.v_loc.get().strip(),
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

    def _gallery_add(self, direction, call, mode, path, png, size):
        if self.gal_store is None:
            return
        self.gal_store.add({"t": time.time(), "dir": direction, "call": call or "?", "mode": mode,
                            "file": path, "png": png, "size": size or 0})
        self.gal.refresh()

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
            if fmt in ("hft", "txt"):
                return
            d = os.path.join(self.gal_store.folder, gallery.SENT_DIR)
            os.makedirs(d, exist_ok=True)
            call = self.v_call.get().strip().upper().replace("/", "-") or "NOCALL"
            mode_n = (mode or "") + ("-HYB" if job["kind"] == "hybrid" and "HYB" not in (mode or "") else "")
            base = os.path.join(d, f"{time.strftime('%Y%m%d_%H%M%S')}_{mode_n}_{call}")
            path, png = imgfmt.save_received(base, fmt, data)
            self._gallery_add("tx", call, mode_n, path, png, len(data))
        except Exception as e:
            self.log_exc("Galerie (image envoyée)", e)

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
        self.nb.select(0)

    def gallery_full(self, e):
        p = e.get("file")
        if not (p and os.path.exists(p) and (p.lower().endswith(".gif") or p.lower().endswith(".jpg"))):
            p = self._gallery_src(e)
        if p and os.path.exists(p):
            self._open_path(p)

    def gallery_to_tx(self, e):
        p = e.get("file")
        if p and p.lower().endswith((".avif", ".webp")) and e.get("png") and os.path.exists(e["png"]):
            p = e["png"]
        if p and os.path.exists(p):
            self.load_image(p)
            self.nb.select(1)

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
        def run():
            try:
                info = updater.check()
            except Exception as e:
                if not quiet:
                    self.ui(messagebox.showinfo, APP, f"Impossible de vérifier les mises à jour :\n{e}")
                return
            self.ui(self._update_found, info, quiet)
        threading.Thread(target=run, daemon=True).start()

    def _update_found(self, info, quiet):
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
    _LAYOUT = {"main": "first", "left": "last", "right": "last", "rx": "last", "rxside": "first"}

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
        self.geometry("1320x880")
        self.conf["layout"] = {"main": 268, "left": 170, "right": 70, "rx": 250}
        self.update_idletasks()
        self.after(150, self._restore_layout)
        self.after(400, lambda: self.panes["rxside"].sash_place(
            0, 0, self.panes["rxside"].winfo_height() // 2))

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
    import io
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
    # formats : SVG (rendu resvg + compression) et JPEG
    try:
        svg = (b'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">'
               b'<rect width="200" height="100" fill="#1d3557"/><circle cx="150" cy="50" r="30" fill="#ffd166"/></svg>')
        im = imgfmt.render_svg(svg, 400)
        pk = imgfmt.svg_pack(svg)
        px = im.getpixel((300, 100))
        ok = im.size == (400, 200) and px[0] > 200 and protocol.detect_format(pk) == "svg"
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
