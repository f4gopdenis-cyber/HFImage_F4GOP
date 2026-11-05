"""2.11 : fenêtre agrandie sur le 2e écran : elle se rouvrait sur l'autre écran (signalé par F4GOP)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Geo(unittest.TestCase):
    def setUp(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.z = app.App._zoomed_geom

    def test_ecran_de_droite(self):
        self.assertEqual(self.z("1320x880+100+60", "1936x1056+1912+-8"), "1320x880+1952+32")

    def test_ecran_de_gauche(self):
        self.assertEqual(self.z("1320x880+2000+60", "1936x1056+-1928+-8"), "1320x880+-1888+32")

    def test_ecran_principal(self):
        self.assertEqual(self.z("1320x880+2000+60", "1936x1056+-8+-8"), "1320x880+32+32")

    def test_sans_ancienne_taille(self):
        self.assertEqual(self.z(None, "1936x1056+1912+-8"), "1320x880+1952+32")

    def test_tk_accepte_la_position(self):
        import tkinter as tk
        try:
            r = tk.Tk()
        except tk.TclError as e:
            raise unittest.SkipTest(str(e))
        try:
            r.geometry(self.z("400x300+0+0", "1936x1056+-1928+-8"))
            r.update_idletasks()
            self.assertTrue(r.geometry().startswith("400x300"))
        finally:
            r.destroy()

    def test_geometrie_illisible(self):
        self.assertEqual(self.z("1320x880+100+60", ""), "1320x880+100+60")
