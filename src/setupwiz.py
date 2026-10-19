"""Assistant de premier démarrage : 3 étapes (indicatif et locator, carte son, poste radio).

S'ouvre tout seul au premier lancement (indicatif encore vide), et à la demande par
Réglages → Assistant de démarrage… Il ne fait que remplir les réglages habituels : tout
reste modifiable ensuite dans Réglages et dans la fenêtre Poste radio.
"""
import re
import tkinter as tk
from tkinter import messagebox, ttk

from i18n import tr

# indicatif radioamateur (F4GOP, F4GOP/P) ou identifiant d'écouteur (PA0041SWL, F-12345, 14VD274)
CALL_RE = re.compile(r"^(?=.*[0-9])[A-Z0-9][A-Z0-9/-]{2,11}$")
LOC_RE = re.compile(r"^[A-R]{2}[0-9]{2}([A-X]{2})?$", re.I)


class SetupWizard(tk.Toplevel):
    STEPS = 3

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title(tr("Assistant de démarrage"))
        self.transient(app)
        self.resizable(False, False)
        self.step = 0
        top = ttk.Frame(self, padding=(16, 12, 16, 4))
        top.pack(fill="x")
        self.lb_step = ttk.Label(top, text="", foreground="#666")
        self.lb_step.pack(anchor="w")
        self.lb_title = ttk.Label(top, text="", font=("TkDefaultFont", 13, "bold"))
        self.lb_title.pack(anchor="w", pady=(2, 0))
        self.body = ttk.Frame(self, padding=(16, 8, 16, 8), width=560, height=230)
        self.body.pack(fill="both", expand=True)
        self.body.pack_propagate(False)
        bot = ttk.Frame(self, padding=(16, 4, 16, 12))
        bot.pack(fill="x")
        self.bt_skip = ttk.Button(bot, text="Plus tard", command=self.close)
        self.bt_skip.pack(side="left")
        self.bt_next = ttk.Button(bot, text="Suivant ▶", command=self.next)
        self.bt_next.pack(side="right")
        self.bt_prev = ttk.Button(bot, text="◀ Précédent", command=self.prev)
        self.bt_prev.pack(side="right", padx=6)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.show()
        self.update_idletasks()
        try:
            x = app.winfo_rootx() + max(0, (app.winfo_width() - self.winfo_width()) // 2)
            y = app.winfo_rooty() + max(0, (app.winfo_height() - self.winfo_height()) // 3)
            self.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass
        self.lift()

    # ------------------------------------------------------------------ pages
    def _clear(self):
        for w in self.body.winfo_children():
            w.destroy()

    def _text(self, text):
        ttk.Label(self.body, text=tr(text), wraplength=520, justify="left").pack(anchor="w", pady=(0, 8))

    def show(self):
        self._clear()
        self.lb_step.configure(text=tr("Étape") + f" {self.step + 1} / {self.STEPS}")
        getattr(self, f"_page{self.step}")()
        self.bt_prev.state(["!disabled" if self.step else "disabled"])
        self.bt_next.configure(text=tr("Terminer") if self.step == self.STEPS - 1 else tr("Suivant ▶"))

    def _page0(self):
        self.lb_title.configure(text=tr("Votre station"))
        self._text("Bienvenue dans HFImage ! Indiquez votre indicatif et votre locator : ils partent avec vos "
                   "images et apparaissent sur la carte des stations. Écouteur (SWL) : mettez votre identifiant "
                   "(ex. F-12345, PA0041SWL) ; HFImage n'émettra pas, vos reports partiront par Internet.")
        g = ttk.Frame(self.body)
        g.pack(anchor="w")
        ttk.Label(g, text=tr("Indicatif")).grid(row=0, column=0, sticky="w", pady=4)
        e = ttk.Entry(g, textvariable=self.app.v_call, width=14, font=("TkDefaultFont", 12))
        e.grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(g, text=tr("Locator")).grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(g, textvariable=self.app.v_loc, width=10, font=("TkDefaultFont", 12)).grid(
            row=1, column=1, sticky="w", padx=8)
        ttk.Label(g, text=tr("(ex. IN98QR)"), foreground="#666").grid(row=1, column=2, sticky="w")
        e.focus_set()

    def _page1(self):
        self.lb_title.configure(text=tr("Carte son du poste"))
        self._text("Choisissez la carte son reliée au poste (souvent « USB Audio CODEC » pour un poste "
                   "récent branché en USB) : la sortie va vers le poste, l'entrée vient du poste.")
        g = ttk.Frame(self.body)
        g.pack(anchor="w", fill="x")
        ttk.Label(g, text=tr("Sortie (vers le poste)")).grid(row=0, column=0, sticky="w", pady=4)
        ttk.Combobox(g, textvariable=self.app.v_out, values=self.app.cb_out["values"], width=40,
                     state="readonly").grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(g, text=tr("Entrée (depuis le poste)")).grid(row=1, column=0, sticky="w", pady=4)
        ttk.Combobox(g, textvariable=self.app.v_in, values=self.app.cb_in["values"], width=40,
                     state="readonly").grid(row=1, column=1, sticky="w", padx=8)
        b = ttk.Frame(self.body)
        b.pack(anchor="w", pady=(10, 0))
        ttk.Button(b, text=tr("Tester la sortie (1 kHz, sans émettre)"), command=self.app.test_audio).pack(
            side="left")
        ttk.Button(b, text=tr("Actualiser la liste"), command=self._rescan).pack(side="left", padx=8)

    def _rescan(self):
        try:
            self.app._rescan_audio(manual=True)
        except Exception:
            pass
        self.show()

    def _page2(self):
        self.lb_title.configure(text=tr("Poste radio (CAT et PTT)"))
        self._text("Pour que HFImage passe en émission et lise la fréquence, choisissez votre poste et "
                   "son port COM. Si votre poste passe par Hamlib, la fenêtre propose de l'installer "
                   "(une seule fois, quelques secondes). Sans liaison CAT, choisissez « PTT par VOX ».")
        ttk.Button(self.body, text=tr("Choisir le poste (CAT / PTT)…"), command=self.app.radio_dialog).pack(
            anchor="w")
        self._text("")
        self._text("Tout reste modifiable plus tard : menu Réglages, et Réglages → Assistant de démarrage… "
                   "pour revoir ces trois étapes.")

    # ------------------------------------------------------------------ navigation
    def _check(self):
        if self.step == 0:
            call = self.app.v_call.get().strip().upper()
            self.app.v_call.set(call)
            if not CALL_RE.match(call):
                messagebox.showwarning(self.title(), tr("Indiquez votre indicatif (ex. F4GOP) ou votre identifiant d'écouteur (ex. F-12345)."), parent=self)
                return False
            loc = self.app.v_loc.get().strip()
            if loc and not LOC_RE.match(loc):
                messagebox.showwarning(self.title(), tr("Locator incorrect (ex. IN98QR) : corrigez-le ou "
                                                        "laissez-le vide."), parent=self)
                return False
            self.app.v_loc.set(loc.upper())
        return True

    def next(self):
        if not self._check():
            return
        if self.step < self.STEPS - 1:
            self.step += 1
            self.show()
        else:
            self.finish()

    def prev(self):
        if self.step:
            self.step -= 1
            self.show()

    def finish(self):
        app = self.app
        try:
            app._in_changed()              # enregistre les réglages et relance l'écoute sur l'entrée choisie
        except Exception:
            app.save_conf(quiet=True)
        try:
            app.net_start()                # stations en ligne avec le nouvel indicatif
        except Exception:
            pass
        app.log(tr("Assistant de démarrage terminé."))
        self.destroy()

    def close(self):
        try:
            self.app.save_conf(quiet=True)
        except Exception:
            pass
        self.destroy()
