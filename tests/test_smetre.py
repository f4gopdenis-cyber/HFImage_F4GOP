"""Version 1.78 : S-mètre du poste dans le panneau, à la place de la fréquence en double."""
import os
import sys
import tkinter as tk
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import app  # noqa: E402
import panel  # noqa: E402
import radio  # noqa: E402


class Echelle(unittest.TestCase):
    def test_texte(self):
        self.assertEqual(radio.s_text(None), "S —")
        self.assertEqual(radio.s_text(-54), "S0")
        self.assertEqual(radio.s_text(-12), "S7")
        self.assertEqual(radio.s_text(0), "S9")
        self.assertEqual(radio.s_text(4), "S9")
        self.assertEqual(radio.s_text(5), "S9+10")
        self.assertEqual(radio.s_text(20), "S9+20")
        self.assertEqual(radio.s_text(90), "S9+60")

    def test_kenwood(self):
        self.assertEqual(radio.kenwood_db(0, "TS-890S"), -54)
        self.assertEqual(radio.kenwood_db(35, "TS-890S"), 0)
        self.assertEqual(radio.kenwood_db(70, "TS-990S"), 60)
        self.assertEqual(radio.kenwood_db(15, "TS-590S"), 0)
        self.assertEqual(radio.kenwood_db(30, "TS-590S"), 60)


class Pilotes(unittest.TestCase):
    def test_kenwood_sm0(self):
        r = radio.KenwoodRig.__new__(radio.KenwoodRig)
        r.model = "TS-890S"
        r.query = lambda cmd, timeout=0.6: "SM00035;" if cmd == "SM0;" else ""
        self.assertEqual(r.smeter(), 0)
        r.query = lambda cmd, timeout=0.6: ""                   # pas de réponse
        self.assertIsNone(r.smeter())

    def test_hamlib_strength(self):
        r = radio.RigctlRig.__new__(radio.RigctlRig)
        sent = []
        r.cmd = lambda c, n=1: (sent.append(c), ["-24"])[1]
        self.assertEqual(r.smeter(), -24)
        self.assertEqual(sent, ["l STRENGTH"])
        r.cmd = lambda c, n=1: ["RPRT -11"]                      # niveau non pris en charge
        self.assertIsNone(r.smeter())

        def boom(c, n=1):
            raise RuntimeError("le poste ne répond pas")
        r.cmd = boom
        self.assertIsNone(r.smeter())

    def test_autres_pilotes_sans_smetre(self):
        for cls in (radio.FlrigRig, radio.OmniRigRig, radio.TciRig, radio.CustomRig):
            self.assertFalse(cls.has_smeter, cls.__name__)


class Lecture(unittest.TestCase):
    def stub(self, smeter=True):
        s = types.SimpleNamespace(radio_cfg=dict(radio.DEFAULTS, smeter=smeter), calls=[], logs=[])
        s.panel = types.SimpleNamespace(set_smeter=lambda *a: s.calls.append(a))
        s._show_freq = lambda: s.calls.append("freq")
        s.log = s.logs.append
        s.ui = lambda f, *a: f(*a)
        for k in ("_sm_reset", "_smeter_read"):
            setattr(s, k, getattr(app.App, k).__get__(s))
        s._sm_reset()
        return s

    def test_valeur_envoyee_seulement_si_elle_change(self):
        s = self.stub()
        vals = iter([-12, -12, -6])
        rig = types.SimpleNamespace(has_smeter=True, smeter=lambda: next(vals))
        for _ in range(3):
            s._smeter_read(rig)
        self.assertEqual(s.calls, [(-12,), (-6,)])

    def test_poste_muet_on_arrete_de_demander(self):
        s = self.stub()
        n = []
        rig = types.SimpleNamespace(has_smeter=True, smeter=lambda: n.append(1))
        for _ in range(10):
            s._smeter_read(rig)
        self.assertEqual(len(n), 3)                  # 3 essais, puis plus rien
        self.assertTrue(s._sm_off)
        self.assertIn("freq", s.calls)

    def test_decoche_rien_demande(self):
        s = self.stub(smeter=False)
        n = []
        s._smeter_read(types.SimpleNamespace(has_smeter=True, smeter=lambda: n.append(1)))
        self.assertEqual(n, [])

    def test_raté_passager_garde_le_smetre(self):
        s = self.stub()
        vals = iter([-12, None, None, None, None, -6])
        rig = types.SimpleNamespace(has_smeter=True, smeter=lambda: next(vals))
        for _ in range(6):
            s._smeter_read(rig)
        self.assertFalse(s._sm_off)
        self.assertEqual(s.calls[-1], (-6,))


class Affichage(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("pas d'écran")
        self.p = panel.StatusPanel(self.root)
        self.p.pack()

    def tearDown(self):
        self.root.destroy()

    def test_smetre_remplace_la_frequence(self):
        p = self.p
        p.set_freq("7.058.000", "LSB-DATA1 · 40 m")
        p.show_smeter(True)
        self.root.update()
        self.assertFalse(p.freq.winfo_ismapped())
        self.assertTrue(p.smeter.winfo_ismapped())
        p.set_smeter(10)
        texts = [p.smeter.itemcget(i, "text") for i in p.smeter.find_all() if p.smeter.type(i) == "text"]
        self.assertIn("S9+10", texts)
        n = len(p.smeter.find_all())
        p.set_smeter(10)                              # même valeur : rien redessiné
        self.assertEqual(len(p.smeter.find_all()), n)
        p.set_smeter(10, True)                        # émission : grisé
        p.show_smeter(False)
        self.root.update()
        self.assertTrue(p.freq.winfo_ismapped())
        self.assertFalse(p.smeter.winfo_ismapped())

    def test_style_moderne(self):
        P = {"panel": "#242931", "field": "#1a1e24", "accent": "#2ecc71", "bad": "#e74c3c",
             "fg": "#e6e6e6", "muted": "#98a3af"}
        self.p.show_smeter(True)
        self.p.set_smeter(-20)
        self.p.set_modern(P)
        self.assertEqual(self.p.smeter.cget("bg"), "#242931")


if __name__ == "__main__":
    unittest.main()
