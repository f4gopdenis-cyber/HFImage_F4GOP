"""Fenêtre « Poste radio » (comme l'onglet Radio de WSJT-X) : poste, CAT, PTT, mode, tests."""
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import audio
import radio
from i18n import tr

BAUDS = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]


class RadioDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Poste radio")
        self.transient(app)
        self.resizable(False, False)
        cfg = dict(app.radio_cfg)
        self.all_keys = radio.rig_keys()
        self.v = {k: tk.StringVar(value=str(cfg.get(k, radio.DEFAULTS[k]))) for k in radio.DEFAULTS}
        self.v_rig = tk.StringVar(value=tr(radio.rig_label(cfg["rig"])))
        self.v_filter = tk.StringVar()
        self.testing = False

        top = ttk.Frame(self, padding=10)
        top.pack(fill="both", expand=True)
        L = ttk.Frame(top)
        L.grid(row=0, column=0, sticky="n")
        R = ttk.Frame(top)
        R.grid(row=0, column=1, sticky="n", padx=(12, 0))

        # ---- poste
        g = ttk.LabelFrame(L, text="Poste", padding=8)
        g.pack(fill="x")
        ttk.Label(g, text="Rechercher").grid(row=0, column=0, sticky="w")
        ef = ttk.Entry(g, textvariable=self.v_filter, width=18)
        ef.grid(row=0, column=1, sticky="w", padx=4, pady=2)
        self.cb_rig = ttk.Combobox(g, textvariable=self.v_rig, width=34, state="readonly", height=24)
        self.cb_rig.grid(row=1, column=0, columnspan=2, sticky="w", pady=2)
        self._fill_rigs()
        self.v_filter.trace_add("write", lambda *a: self._fill_rigs())
        self.cb_rig.bind("<<ComboboxSelected>>", lambda e: self._update())
        ttk.Label(g, text="Interrogation (s)").grid(row=2, column=0, sticky="w")
        ttk.Spinbox(g, from_=1, to=99, textvariable=self.v["poll"], width=5).grid(row=2, column=1, sticky="w",
                                                                                   padx=4, pady=2)
        self.lb_hamlib = ttk.Label(g, text="", foreground="#555", wraplength=300, justify="left")
        self.lb_hamlib.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.bt_hamlib = ttk.Button(g, text="Installer Hamlib", command=self._install_hamlib)
        self.bt_hamlib.grid(row=4, column=0, columnspan=2, sticky="w")
        self.pb = ttk.Progressbar(g, length=200, maximum=100)

        # ---- liaison CAT
        c = ttk.LabelFrame(L, text="Liaison CAT", padding=8)
        c.pack(fill="x", pady=(8, 0))
        self.cat_frame = c
        ttk.Label(c, text="Port série").grid(row=0, column=0, sticky="w")
        ports = [p for p, _ in audio.ports_list()]
        self.cb_port = ttk.Combobox(c, textvariable=self.v["port"], values=ports, width=12)
        self.cb_port.grid(row=0, column=1, sticky="w", padx=4, pady=2)
        ttk.Label(c, text="Serveur réseau").grid(row=1, column=0, sticky="w")
        self.e_host = ttk.Entry(c, textvariable=self.v["host"], width=20)
        self.e_host.grid(row=1, column=1, sticky="w", padx=4, pady=2)
        sp = ttk.LabelFrame(c, text="Paramètres du port série", padding=6)
        sp.grid(row=2, column=0, columnspan=2, sticky="we", pady=(4, 0))
        self.serial_frame = sp
        ttk.Label(sp, text="Vitesse (bauds)").grid(row=0, column=0, sticky="w")
        ttk.Combobox(sp, textvariable=self.v["baud"], values=BAUDS, width=9).grid(row=0, column=1, columnspan=3,
                                                                                  sticky="w", pady=2)
        self._radios(sp, 1, "Bits de données", "data_bits", [("Défaut", "default"), ("7", "7"), ("8", "8")])
        self._radios(sp, 2, "Bits de stop", "stop_bits", [("Défaut", "default"), ("1", "1"), ("2", "2")])
        ttk.Label(sp, text="Contrôle de flux").grid(row=3, column=0, sticky="nw")
        hf = ttk.Frame(sp)
        hf.grid(row=3, column=1, columnspan=3, sticky="w")
        for i, (t, val) in enumerate([("Défaut", "default"), ("Aucun", "none"), ("XON/XOFF", "xonxoff"),
                                      ("Matériel (RTS/CTS)", "hardware")]):
            ttk.Radiobutton(hf, text=t, value=val, variable=self.v["handshake"],
                            command=self._update).grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 6))
        ttk.Label(sp, text="Forcer les lignes").grid(row=4, column=0, sticky="w")
        lf = ttk.Frame(sp)
        lf.grid(row=4, column=1, columnspan=3, sticky="w")
        self.line_cbs = {}
        self._line_names = {"": "—", "high": tr("Haut"), "low": tr("Bas")}
        for i, line in enumerate(("dtr", "rts")):
            ttk.Label(lf, text=line.upper()).pack(side="left", padx=(0 if i == 0 else 8, 2))
            vv = tk.StringVar(value=self._line_names.get(self.v[line].get(), "—"))
            cb = ttk.Combobox(lf, textvariable=vv, values=list(self._line_names.values()), width=6,
                              state="readonly")
            cb.pack(side="left")
            cb.bind("<<ComboboxSelected>>",
                    lambda e, l=line, vv=vv: self.v[l].set(
                        next(k for k, n in self._line_names.items() if n == vv.get())))
            self.line_cbs[line] = cb

        # ---- commandes personnalisées (comme EasyPal)
        cc = ttk.LabelFrame(L, text="Commandes personnalisées", padding=8)
        self.custom_frame = cc
        for i, (key, lab) in enumerate((("cmd_init1", "Départ 1"), ("cmd_init2", "Départ 2"),
                                        ("cmd_ptt_on", "PTT marche"), ("cmd_ptt_off", "PTT arrêt"),
                                        ("cmd_exit1", "Sortie 1"), ("cmd_exit2", "Sortie 2"))):
            ttk.Label(cc, text=lab).grid(row=i, column=0, sticky="w")
            ttk.Entry(cc, textvariable=self.v[key], width=30).grid(row=i, column=1, sticky="w", padx=4, pady=1)
        df = ttk.Frame(cc)
        df.grid(row=6, column=0, columnspan=2, sticky="w", pady=(2, 0))
        ttk.Label(df, text="Délai entre deux commandes (ms)").pack(side="left")
        ttk.Spinbox(df, from_=0, to=2000, increment=50, textvariable=self.v["cmd_delay"], width=6).pack(
            side="left", padx=4)
        wf = ttk.Frame(cc)
        wf.grid(row=7, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Label(wf, text="Départ / Sortie :").pack(anchor="w")
        ttk.Radiobutton(wf, text="à chaque émission (comme EasyPal)", value="tx",
                        variable=self.v["cmd_when"]).pack(anchor="w")
        ttk.Radiobutton(wf, text="au lancement et à la fermeture du programme", value="open",
                        variable=self.v["cmd_when"]).pack(anchor="w")
        ttk.Label(cc, text="Hexadécimal (Icom CI-V : FEFE5EE01C0001FD) ou texte (Kenwood : TX1;).\n"
                           "Départ avant PTT marche, Sortie après PTT arrêt.\n"
                           "Les réglages d'EasyPal (\\$…\\) se collent tels quels. Choisissez PTT « CAT ».",
                  foreground="#555", justify="left").grid(row=8, column=0, columnspan=2, sticky="w", pady=(4, 0))

        # ---- PTT
        p = ttk.LabelFrame(R, text="Méthode PTT", padding=8)
        p.pack(fill="x")
        pf = ttk.Frame(p)
        pf.grid(row=0, column=0, columnspan=2, sticky="w")
        for i, (t, val) in enumerate([("VOX", "VOX"), ("DTR", "DTR"), ("CAT", "CAT"), ("RTS", "RTS")]):
            ttk.Radiobutton(pf, text=t, value=val, variable=self.v["ptt"], command=self._update).grid(
                row=i // 2, column=i % 2, sticky="w", padx=(0, 16))
        ttk.Label(p, text="Port").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.ptt_names = {"": tr("Même port que le CAT")}
        self.v_pttport = tk.StringVar(value=self.v["ptt_port"].get() or self.ptt_names[""])
        self.cb_pttport = ttk.Combobox(p, textvariable=self.v_pttport, values=[self.ptt_names[""]] + ports,
                                       width=20)
        self.cb_pttport.grid(row=1, column=1, sticky="w", padx=4, pady=(4, 0))
        ttk.Label(p, text="DTR / RTS : interface PTT à côté du poste\n(sur un autre port COM, ou celui du CAT).",
                  foreground="#555", justify="left").grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))

        a = ttk.LabelFrame(R, text="Source audio en émission", padding=8)
        a.pack(fill="x", pady=(8, 0))
        self.audio_frame = a
        ttk.Radiobutton(a, text="Arrière / Data (audio USB, ACC)", value="rear",
                        variable=self.v["tx_audio"]).pack(anchor="w")
        ttk.Radiobutton(a, text="Avant / Micro", value="front", variable=self.v["tx_audio"]).pack(anchor="w")

        m = ttk.LabelFrame(R, text="Mode", padding=8)
        m.pack(fill="x", pady=(8, 0))
        self.mode_frame = m
        mf = ttk.Frame(m)
        mf.pack(anchor="w")
        for t, val in [("Aucun", "none"), ("USB", "usb"), ("Data / Pkt", "data")]:
            ttk.Radiobutton(mf, text=t, value=val, variable=self.v["set_mode"]).pack(side="left", padx=(0, 10))
        ttk.Label(m, text="Mis par CAT avant chaque émission (« Aucun » : on ne touche pas au poste).",
                  foreground="#555", wraplength=280, justify="left").pack(anchor="w", pady=(4, 0))

        t = ttk.Frame(R)
        t.pack(fill="x", pady=(10, 0))
        self.bt_cat = tk.Button(t, text="Tester le CAT", width=14, command=self.test_cat)
        self.bt_cat.pack(side="left")
        self.bt_ptt = tk.Button(t, text="Tester le PTT", width=14, command=self.test_ptt)
        self.bt_ptt.pack(side="left", padx=6)
        self._btn_bg = self.bt_cat.cget("background")
        self.lb_test = ttk.Label(R, text="", wraplength=300, justify="left")
        self.lb_test.pack(anchor="w", pady=(6, 0))

        b = ttk.Frame(self, padding=(10, 0, 10, 10))
        b.pack(fill="x")
        ttk.Button(b, text="Annuler", command=self.destroy).pack(side="right")
        ttk.Button(b, text="OK", command=self.ok).pack(side="right", padx=6)

        self._update()
        app._translate_ui(self)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    # ------------------------------------------------------------------ outils
    def _radios(self, parent, row, label, key, items):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")
        for i, (t, val) in enumerate(items):
            ttk.Radiobutton(parent, text=t, value=val, variable=self.v[key]).grid(row=row, column=1 + i,
                                                                                  sticky="w", padx=(0, 6))

    def _fill_rigs(self):
        f = self.v_filter.get().strip().lower()
        self._labels = {}
        vals = []
        for k in self.all_keys:
            lab = tr(radio.rig_label(k))
            if f and f not in lab.lower() and not k.startswith(("none", "kenwood")):
                continue
            self._labels[lab] = k
            vals.append(lab)
        self.cb_rig["values"] = vals

    def _rig_key(self):
        lab = self.v_rig.get()
        if lab in getattr(self, "_labels", {}):
            return self._labels[lab]
        for k in self.all_keys:
            if tr(radio.rig_label(k)) == lab:
                return k
        return "none"

    def cfg(self):
        c = {k: v.get() for k, v in self.v.items()}
        c["rig"] = self._rig_key()
        try:
            c["baud"] = int(c["baud"])
        except ValueError:
            c["baud"] = 9600
        try:
            c["poll"] = max(1, int(c["poll"]))
        except ValueError:
            c["poll"] = 1
        try:
            c["cmd_delay"] = max(0, min(2000, int(float(c["cmd_delay"]))))
        except ValueError:
            c["cmd_delay"] = 200
        for k in radio.CUSTOM_KEYS:
            c[k] = c[k].strip()
        pp = self.v_pttport.get().strip()
        c["ptt_port"] = "" if pp in ("", self.ptt_names[""]) else pp
        c["port"] = c["port"].strip()
        c["host"] = c["host"].strip()
        return c

    @staticmethod
    def _state(frame, on):
        for w in frame.winfo_children():
            if isinstance(w, (ttk.Frame, ttk.LabelFrame)):
                RadioDialog._state(w, on)
            try:
                if isinstance(w, ttk.Combobox):
                    w.configure(state=("readonly" if w.cget("values") and w in RadioDialog._ro else "normal")
                                if on else "disabled")
                else:
                    w.configure(state="normal" if on else "disabled")
            except tk.TclError:
                pass

    _ro = set()

    def _update(self):
        if not self.testing:
            for b in (self.bt_cat, self.bt_ptt):
                b.configure(background=self._btn_bg, activebackground=self._btn_bg)
        c = self.cfg()
        kind = radio.rig_entry(c["rig"])["kind"]
        serial_on = kind in ("kenwood", "hamlib", "custom")
        if kind == "custom":
            self.custom_frame.pack(fill="x", pady=(8, 0))
        else:
            self.custom_frame.pack_forget()
        RadioDialog._ro = set(self.line_cbs.values())
        self._state(self.serial_frame, serial_on)
        self.cb_port.configure(state="normal" if serial_on else "disabled")
        net = {"flrig": "127.0.0.1:12345", "netrigctl": "127.0.0.1:4532", "tci": "127.0.0.1:40001"}
        self.e_host.configure(state="normal" if kind in net else "disabled")
        if kind in net and (not self.v["host"].get() or self.v["host"].get() in net.values()):
            self.v["host"].set(net[kind])
        if kind not in net and self.v["host"].get() in net.values():
            self.v["host"].set("")
        self._state(self.mode_frame, kind != "none")
        # source audio : sert au PTT CAT (TX1; / TX0;) et au contrôle du mode DATA (dès que le CAT est relié)
        self._state(self.audio_frame, c["ptt"] == "CAT" or kind != "none")
        self.cb_pttport.configure(state="normal" if c["ptt"] in ("DTR", "RTS") else "disabled")
        if kind == "hamlib":
            exe = radio.find_rigctld()
            if exe:
                own = exe.startswith(radio.hamlib_dir())
                self.lb_hamlib.configure(text=tr("Hamlib trouvé :") + " " +
                                         (f"Hamlib {radio.HAMLIB_VERSION} (HFImage)" if own else exe))
                self.bt_hamlib.grid_remove()
            else:
                self.lb_hamlib.configure(text=tr("Ce poste passe par Hamlib, qui n'est pas encore installé "
                                                 "(téléchargement unique de 3 Mo depuis GitHub)."))
                self.bt_hamlib.grid()
        else:
            self.lb_hamlib.configure(text=tr({"none": "Pas de liaison CAT : fréquence non lue, PTT par VOX ou "
                                                       "DTR / RTS d'une interface.",
                                              "kenwood": "Kenwood en direct : rien à installer.",
                                              "omnirig": "OmniRig doit être installé et réglé (bouton "
                                                         "« Setup » d'OmniRig).",
                                              "flrig": "FLRig doit être lancé (serveur XML-RPC, port 12345 "
                                                       "par défaut).",
                                              "netrigctl": "Un serveur rigctld doit tourner (port 4532 par "
                                                           "défaut).",
                                              "custom": "Commandes écrites à la main, comme dans EasyPal : "
                                                        "la fréquence du poste n'est pas lue.",
                                              "tci": "ExpertSDR doit être lancé avec TCI activé (Options → TCI, "
                                                     "port 40001). Le son passe par les câbles audio virtuels "
                                                     "(VAC) d'ExpertSDR. Choisissez PTT « CAT »."}.get(kind, "")))
            self.bt_hamlib.grid_remove()

    # ------------------------------------------------------------------ Hamlib
    def _install_hamlib(self):
        self.bt_hamlib.configure(state="disabled")
        self.pb.grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))

        def run():
            try:
                d = radio.install_hamlib(lambda f: self.app.ui(self.pb.configure, {"value": f * 100}))
                self.app.ui(self.app.log, f"Hamlib {radio.HAMLIB_VERSION} installé dans {d}")
                self.app.ui(self._hamlib_done, None)
            except Exception as e:
                self.app.ui(self.app.log_exc, "Installation de Hamlib", e)
                self.app.ui(self._hamlib_done, e)
        threading.Thread(target=run, daemon=True).start()

    def _hamlib_done(self, err):
        if not self.winfo_exists():
            return
        self.pb.grid_remove()
        self.bt_hamlib.configure(state="normal")
        if err:
            messagebox.showerror("HFImage", tr("Installation de Hamlib impossible :") + f"\n{err}", parent=self)
        self._update()

    # ------------------------------------------------------------------ tests
    def _show(self, btn, ok, text):
        if not self.winfo_exists():
            return
        btn.configure(background="#7fd47f" if ok else "#ff8f8f", activebackground="#9fe09f" if ok else "#ffaaaa")
        self.lb_test.configure(text=text, foreground="#1c6f1c" if ok else "#b00000")
        self.testing = False

    def test_cat(self):
        if self.testing:
            return
        c = self.cfg()
        if radio.rig_entry(c["rig"])["kind"] == "none":
            self._show(self.bt_cat, False, tr("Aucun poste choisi : rien à tester."))
            return
        self.testing = True
        self.bt_cat.configure(background=self._btn_bg)
        self.lb_test.configure(text=tr("Test en cours…"), foreground="#555")

        def run():
            try:
                with self.app.rig_hold():
                    r = radio.make_rig(c)
                    try:
                        f, m = r.freq(), r.mode()
                        if getattr(r, "per_tx", False):      # commandes perso « à chaque émission »
                            r.before_tx()
                            r.after_tx()
                    finally:
                        r.close()
                if not getattr(r, "reads_freq", True):
                    txt = tr("Port ouvert : commandes de départ et de sortie envoyées.") + f" ({r.port})"
                    self.app.ui(self.app.log, "Test CAT : " + txt)
                    self.app.ui(self._show, self.bt_cat, True, txt)
                    return
                txt = f"{r.model} : {audio.format_freq(f) + ' kHz' if f else '?'} {m or ''}"
                self.app.ui(self.app.log, "Test CAT : " + txt)
                self.app.ui(self._show, self.bt_cat, bool(f), txt)
            except Exception as e:
                self.app.ui(self.app.log_exc, "Test CAT", e)
                self.app.ui(self._show, self.bt_cat, False, str(e))
        threading.Thread(target=run, daemon=True).start()

    def test_ptt(self):
        if self.testing or self.app.tx_busy:
            return
        c = self.cfg()
        if c["ptt"] == "VOX":
            self._show(self.bt_ptt, True, tr("PTT en VOX : rien à commander, le poste passe en émission avec le son."))
            return
        self.testing = True
        self.bt_ptt.configure(background=self._btn_bg)
        self.lb_test.configure(text=tr("Émission 1,5 s…"), foreground="#555")

        def run():
            p = r = None
            try:
                with self.app.rig_hold():
                    if c["ptt"] == "CAT" or (c["ptt"] in ("DTR", "RTS") and not c["ptt_port"]):
                        r = radio.make_rig(c)
                    p = radio.Ptt(c, r)
                    p.tx()
                    time.sleep(1.5)
                    p.rx()
                    p.close()
                    p = None
                    if r is not None:
                        r.close()
                        r = None
                self.app.ui(self.app.log, f"Test PTT {c['ptt']} : émission 1,5 s.")
                self.app.ui(self._show, self.bt_ptt, True, tr("PTT : émission de 1,5 s commandée."))
            except Exception as e:
                for x in (p, r):
                    try:
                        if x is not None:
                            x.close()
                    except Exception:
                        pass
                self.app.ui(self.app.log_exc, "Test PTT", e)
                self.app.ui(self._show, self.bt_ptt, False, str(e))
        threading.Thread(target=run, daemon=True).start()

    def ok(self):
        c = self.cfg()
        kind = radio.rig_entry(c["rig"])["kind"]
        if kind in ("kenwood", "hamlib", "custom") and not c["port"]:
            messagebox.showerror("HFImage", tr("Choisissez le port série du poste."), parent=self)
            return
        if c["ptt"] == "CAT" and kind == "none":
            messagebox.showerror("HFImage", tr("PTT par CAT : choisissez d'abord le poste."), parent=self)
            return
        if kind == "custom" and c["ptt"] == "CAT" and not (c["cmd_ptt_on"] and c["cmd_ptt_off"]):
            messagebox.showerror("HFImage", tr("PTT par CAT : remplissez « PTT marche » et « PTT arrêt »."),
                                 parent=self)
            return
        for k in radio.CUSTOM_KEYS:
            try:
                radio.parse_cmd(c[k])
            except ValueError as e:
                messagebox.showerror("HFImage", f"{k} : {e}", parent=self)
                return
        if c["ptt"] in ("DTR", "RTS") and not (c["ptt_port"] or c["port"]):
            messagebox.showerror("HFImage", tr("PTT par DTR / RTS : choisissez le port de l'interface."),
                                 parent=self)
            return
        self.app.set_radio(c)
        self.destroy()
