"""Fenêtre de l'analyseur d'enregistrement (Fichiers → Analyser un enregistrement WAV…)."""
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import wavanalyze

COLORS = {"DATAC1X": "#1f6fd1", "DATAC1": "#1c8f1c", "DATAC3": "#c27c00", "DATAC4": "#8a3fc2", "DATAC0": "#666666",
          "DATAC13": "#d0006f"}
SEV = {"ok": ("#1c6f1c", "✓"), "info": ("#1f4f9f", "•"), "warn": ("#b06000", "!"), "bad": ("#b00000", "✗")}


class AnalyzerWindow(tk.Toplevel):
    def __init__(self, app, path):
        super().__init__(app)
        self.app, self.tr = app, app_tr(app)
        self.title("Analyse d'enregistrement")
        self.geometry("980x720")
        self.rep = None
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        self.lb_file = ttk.Label(top, text="", font=("TkDefaultFont", 9, "bold"))
        self.lb_file.pack(side="left")
        ttk.Button(top, text="Autre fichier…", command=self.other).pack(side="right")
        ttk.Button(top, text="Enregistrer le rapport…", command=self.save).pack(side="right", padx=4)
        ttk.Button(top, text="Copier le rapport", command=self.copy).pack(side="right")
        self.pb = ttk.Progressbar(self, maximum=100)
        self.pb.pack(fill="x", padx=8)
        self.lb_state = ttk.Label(self, text="")
        self.lb_state.pack(anchor="w", padx=8)
        pw = tk.PanedWindow(self, orient="vertical", sashwidth=6)
        pw.pack(fill="both", expand=True, padx=8, pady=8)
        self.txt = tk.Text(pw, height=12, wrap="word", font=("TkDefaultFont", 10))
        for k, (c, _) in SEV.items():
            self.txt.tag_configure(k, foreground=c)
        pw.add(self.txt, minsize=120, height=230)
        self.cv = tk.Canvas(pw, bg="white", highlightthickness=0)
        self.cv._no_theme = True
        pw.add(self.cv, minsize=200)
        self.cv.bind("<Configure>", lambda e: self.draw())
        app._translate_ui(self)
        self.start(path)

    # ------------------------------------------------------------------ calcul
    def start(self, path):
        self.rep = None
        self.lb_file.configure(text=os.path.basename(path))
        self.txt.delete("1.0", "end")
        self.cv.delete("all")

        def prog(f, msg=""):
            self.app.ui(self._prog, f, msg)

        def run():
            try:
                rep = wavanalyze.analyze(path, prog)
                self.app.ui(self._done, rep)
            except Exception as e:
                self.app.ui(self._fail, e)
        threading.Thread(target=run, daemon=True).start()

    def _prog(self, f, msg):
        if not self.winfo_exists():
            return
        self.pb.configure(value=f * 100)
        self.lb_state.configure(text=self.tr("Analyse en cours…") + (f" {msg}" if msg else ""))

    def _fail(self, e):
        if self.winfo_exists():
            self.lb_state.configure(text="")
            messagebox.showerror("HFImage", self.tr("Analyse impossible :") + f"\n{e}", parent=self)

    def _done(self, rep):
        if not self.winfo_exists():
            return
        self.rep = rep
        self.pb.configure(value=100)
        lv = rep["level"]
        self.lb_state.configure(text=self.tr(f"Durée {rep['duration']:.0f} s, {lv['fs']} Hz"))
        self.txt.delete("1.0", "end")
        for sev, t in rep["diag"]:
            c, mark = SEV[sev]
            self.txt.insert("end", f"{mark} {self.tr(t)}\n", sev)
        self.draw()
        self.app.log(f"Analyse de {os.path.basename(rep['path'])} terminée.")

    # ------------------------------------------------------------------ graphique
    def draw(self):
        cv = self.cv
        cv.delete("all")
        rep = self.rep
        if not rep:
            return
        W, H = max(cv.winfo_width(), 300), max(cv.winfo_height(), 200)
        L, R, T, B = 50, 20, 24, 36
        dur = max(rep["duration"], 1)
        ev = [(e, m) for m, d in rep["modes"].items() for e in d["events"]]
        snrs = [e[2] for e, _ in ev] or [0, 10]
        lo, hi = min(-2, min(snrs) - 1), max(12, max(snrs) + 1)
        X = lambda t: L + (W - L - R) * t / dur
        Y = lambda s: T + (H - T - B) * (hi - s) / (hi - lo)
        cv.create_text(L, 10, anchor="w", font=("TkDefaultFont", 9, "bold"),
                       text=self.tr("SNR de chaque trame (rond : juste, croix : perdue)"))
        for s in range(int(lo) // 2 * 2, int(hi) + 1, 2):
            cv.create_line(L, Y(s), W - R, Y(s), fill="#eeeeee")
            cv.create_text(L - 6, Y(s), anchor="e", text=f"{s:+d}", font=("TkDefaultFont", 8), fill="#555")
        for m, th in (("DATAC1X", 9), ("DATAC1", 5)):
            cv.create_line(L, Y(th), W - R, Y(th), fill=COLORS[m], dash=(4, 3))
            cv.create_text(W - R - 2, Y(th) - 7, anchor="e", text=self.tr(f"seuil {m}"), fill=COLORS[m],
                           font=("TkDefaultFont", 8))
        step = max(5, int(dur / 10 // 5 * 5) or 5)
        for t in range(0, int(dur) + 1, step):
            cv.create_line(X(t), H - B, X(t), H - B + 4, fill="#555")
            cv.create_text(X(t), H - B + 12, text=f"{t // 60}:{t % 60:02d}", font=("TkDefaultFont", 8), fill="#555")
        cv.create_line(L, H - B, W - R, H - B, fill="#888")
        for e, m in ev:
            x, y, c = X(e[0]), Y(e[2]), COLORS.get(m, "#000")
            if e[1]:
                cv.create_oval(x - 4, y - 4, x + 4, y + 4, fill=c, outline="")
            else:
                cv.create_line(x - 4, y - 4, x + 4, y + 4, fill="#d00000", width=2)
                cv.create_line(x - 4, y + 4, x + 4, y - 4, fill="#d00000", width=2)
        x = L
        for m in ("DATAC1X", "DATAC1", "DATAC3", "DATAC4", "DATAC0", "DATAC13"):
            if rep["modes"][m]["events"]:
                cv.create_oval(x, H - 14, x + 8, H - 6, fill=COLORS[m], outline="")
                cv.create_text(x + 12, H - 10, anchor="w", text=m, font=("TkDefaultFont", 8))
                x += 80
        for f, frac in rep["qrm"]:
            cv.create_text(x + 10, H - 10, anchor="w", fill="#b06000", font=("TkDefaultFont", 8),
                           text=self.tr(f"QRM {f:.0f} Hz ({frac * 100:.0f} %)"))
            x += 130

    # ------------------------------------------------------------------ actions
    def text(self):
        return wavanalyze.report_text(self.rep, self.tr) if self.rep else ""

    def copy(self):
        if self.rep:
            self.clipboard_clear()
            self.clipboard_append(self.text())
            self.lb_state.configure(text=self.tr("Rapport copié : vous pouvez le coller dans un message."))

    def save(self):
        if not self.rep:
            return
        p = filedialog.asksaveasfilename(parent=self, defaultextension=".txt",
                                         initialfile=os.path.splitext(os.path.basename(self.rep["path"]))[0]
                                         + "_analyse.txt", filetypes=[("Texte", "*.txt")])
        if p:
            with open(p, "w", encoding="utf-8") as f:
                f.write(self.text())

    def other(self):
        p = filedialog.askopenfilename(parent=self, filetypes=[("WAV", "*.wav"), ("Tous", "*.*")])
        if p:
            self.start(p)


def app_tr(app):
    from i18n import tr
    return tr
