"""Carte des reports « illustrée » (d'après M7WUV) : même carte, autre style, choix gardé."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Carte(unittest.TestCase):
    def setUp(self):
        try:
            import stationmap
            stationmap.load()
        except Exception as e:
            raise unittest.SkipTest(str(e))
        self.sm = stationmap
        self.st = [{"call": "G4XGT", "pos": (51.5, -1.0), "ok": True, "rep": 2},
                   {"call": "F5PTY", "pos": (43.4, 3.2), "ok": True, "rep": -5}]
        self.me = {"call": "F4GOP", "pos": (48.7, -0.6)}

    def test_deux_styles(self):
        v = self.sm.View(*self.sm.VIEWS["Europe"], 600, 400)
        a = self.sm.render(v, [dict(s) for s in self.st], dict(self.me))
        b = self.sm.render(v, [dict(s) for s in self.st], dict(self.me), vivid=True)
        self.assertEqual(a.size, b.size)
        self.assertEqual(a.getpixel((300, 395)) != b.getpixel((300, 395)), True)
        self.assertEqual(b.getpixel((2, 399)), self.sm.OCEAN_VIF)       # mer bleu nuit

    def test_etiquettes_cliquables(self):
        v = self.sm.View(*self.sm.VIEWS["Europe"], 600, 400)
        st = [dict(s) for s in self.st]
        self.sm.render(v, st, dict(self.me), vivid=True)
        self.assertTrue(all("_hit" in s for s in st))
