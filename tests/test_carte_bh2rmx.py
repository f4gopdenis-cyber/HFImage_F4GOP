"""2.30 (BH2RMX) : noms de la carte dans la langue choisie, carte ouverte sur notre région,
bulle d'une station qui reste tant que la souris est dessus."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import stationmap as sm  # noqa: E402
import protocol  # noqa: E402


def _country(n):
    return next(c for c in sm.load()["countries"] if c["n"] == n)


def _city(n):
    return next(c for c in sm.load()["cities"] if c[0] == n)


class Langues(unittest.TestCase):
    def test_noms_traduits(self):
        self.assertEqual(_country("Germany")["t"]["de"], "Deutschland")
        self.assertEqual(_country("Germany")["t"]["ru"], "Германия")
        self.assertEqual(_country("China")["t"]["zh"], "中国")              # nom court
        self.assertEqual(_country("Taiwan")["t"]["zh"], "台湾")             # nom neutre
        self.assertEqual(_city("Jinxi")[5]["zh"], "葫芦岛")
        self.assertEqual(_city("Hailar")[5]["zh"], "呼伦贝尔")
        self.assertLessEqual(_city("Jinzhou")[3], 4)                       # visible

    def test_rendu(self):
        v = sm.View(14, 50, 30, 1000, 640)
        self.assertIn("Берлин", sm.render(v, [], None, lang="ru").info["cities"])
        self.assertIn("DEUTSCHLAND", sm.render(v, [], None, lang="de").info["countries"])
        self.assertIn("Vienne", sm.render(v, [], None, lang="fr").info["cities"])
        self.assertIn("Vienna", sm.render(v, [], None, lang="en").info["cities"])
        self.assertIn("北京", sm.render(sm.View(115, 33, 45, 1000, 640), [], None, lang="zh").info["cities"])


class Region(unittest.TestCase):
    def test_region(self):
        L = protocol.locator_to_latlon
        self.assertEqual(sm.home_region(L("IN98QR")), "Europe")
        self.assertEqual(sm.home_region(L("PN41")), "Asie")                 # Chine
        self.assertEqual(sm.home_region(L("OF78")), "Océanie")              # VK6
        self.assertEqual(sm.home_region(L("FN31")), "Amérique du Nord")
        self.assertIsNone(sm.home_region(None))

    def _win(self, me, st):
        import tkinter as tk
        try:
            root = tk.Tk()
        except tk.TclError as e:
            raise unittest.SkipTest(str(e))
        w = sm.MapWindow(root, lambda: (me, st))
        w.win.geometry("800x500")
        root.update()
        return root, w

    def test_vue_de_depart_asie(self):
        L = protocol.locator_to_latlon
        me = {"call": "BH2RMX", "pos": L("PN41")}
        st = [{"call": "F4GOP", "pos": L("IN98QR"), "ok": True, "rep": 0},
              {"call": "BG2AAA", "pos": L("PN40"), "ok": True, "rep": 0}]
        root, w = self._win(me, st)
        try:
            w.set_view("home")
            lon, lat = w.view.lonlat(w.view.w / 2, w.view.h / 2)
            self.assertGreater(lon, 60)                                     # l'Asie, pas le monde
            self.assertLess(w.view.span(), 100)
        finally:
            root.destroy()

    def test_bulle_reste(self):
        L = protocol.locator_to_latlon
        me = {"call": "F4GOP", "pos": L("IN98QR")}
        st = [{"call": "F6DSP", "name": "Henry", "pos": L("JN13LC"), "ok": True, "rep": 0}]
        root, w = self._win(me, st)
        try:
            w.set_view("*")
            root.update()
            h = w._last[0][0]["_hit"]
            w._hover(sm._Pt(h[4], h[5]))
            self.assertTrue(w.cv.find_withtag("tip"))
            w.redraw()                                                      # rafraîchissement de la liste
            self.assertTrue(w.cv.find_withtag("tip"))
            w._unhover()
            w.redraw()
            self.assertFalse(w.cv.find_withtag("tip"))
        finally:
            root.destroy()
