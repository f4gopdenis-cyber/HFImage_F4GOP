"""2.10 : passage de Moderne à Classique : le fond arrondi (sombre) des jauges RX/SNR restait affiché."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Jauges(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            raise unittest.SkipTest(str(e))
        import panel
        import theme
        self.p = panel.StatusPanel(self.root)
        self.p.pack()
        self.P = theme.MODERN["Néon bleu"]

    def tearDown(self):
        self.root.destroy()

    def test_fond_moderne_efface(self):
        p = self.p
        p.set_modern(self.P)
        p.set_bar("RX", -70, -80, 0, "-70 dBFS")
        p.set_bar("SNR", None, 0, 30, "")
        self.assertTrue(all(c.find_withtag("t") for c, _v, _u in p.bars.values()))
        p.set_modern(None)
        for c, _v, _u in p.bars.values():
            self.assertEqual(c.find_withtag("t"), ())
