"""1.46 (demande de M7WUV) : image du correspondant incrustée tournée et / ou en perspective."""
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image  # noqa: E402
import trafic  # noqa: E402

BG = (90, 140, 190)
TH = (230, 200, 60)


def near(a, b, tol=40):
    return sum(abs(x - y) for x, y in zip(a, b)) <= tol


class Penchee(unittest.TestCase):
    def setUp(self):
        self.base = Image.new("RGB", (800, 600), BG)
        self.th = Image.new("RGB", (400, 300), TH)

    def test_droite_inchangee(self):
        a = trafic.pip(self.base, self.th, "de F5PEY", "haut-droite", "grande", [0.5, 0.5], None)
        b = trafic.pip(self.base, self.th, "de F5PEY", "haut-droite", "grande", [0.5, 0.5], None, 0, 0)
        self.assertEqual(a.tobytes(), b.tobytes())

    def test_rotation(self):
        x, y, W, H = trafic.pip_layout(self.base.size, self.th.size, "de F5PEY", "haut-droite", "grande",
                                       [0.5, 0.5], None)[:4]
        im = trafic.pip(self.base, self.th, "de F5PEY", "haut-droite", "grande", [0.5, 0.5], None, 30, 0)
        self.assertEqual(im.size, self.base.size)
        self.assertTrue(near(im.getpixel((x + W // 2, y + H // 3)), TH))       # même centre
        self.assertTrue(near(im.getpixel((x + 3, y + 3)), BG))                 # coin : fond visible (transparent)
        # tournée : le coin haut-droit d'origine n'est plus couvert, un point au-dessus du cadre l'est
        straight = trafic.pip(self.base, self.th, "de F5PEY", "haut-droite", "grande", [0.5, 0.5], None)
        self.assertNotEqual(im.tobytes(), straight.tobytes())

    def test_perspective(self):
        x, y, W, H = trafic.pip_layout(self.base.size, self.th.size, "", "haut-droite", "grande",
                                       [0.5, 0.5], None)[:4]
        im = trafic.pip(self.base, self.th, "", "haut-droite", "grande", [0.5, 0.5], None, 0, 1.0)
        # bord droit éloigné : plus court, donc le coin haut-droit montre le fond ; le gauche reste plein
        self.assertTrue(near(im.getpixel((x + W - 4, y + 4)), BG))
        self.assertFalse(near(im.getpixel((x + 6, y + 6)), BG))
        im2 = trafic.pip(self.base, self.th, "", "haut-droite", "grande", [0.5, 0.5], None, 0, -1.0)
        self.assertTrue(near(im2.getpixel((x + 4, y + 4)), BG))
        self.assertFalse(near(im2.getpixel((x + W - 6, y + 6)), BG))

    def test_bornes(self):
        im = trafic.pip(self.base, self.th, "x", "bas-gauche", "petite", None, None, 400, 9)   # bornées
        self.assertEqual(im.size, self.base.size)


class Reglages(unittest.TestCase):
    def test_garde_par_emplacement(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        s = types.SimpleNamespace(conf={}, PIP_MAX_N=4, PIP_CORNERS=app.App.PIP_CORNERS)
        s.pips = [{"path": "a", "corner": "haut-droite", "size": "moyenne", "pos": None, "scale": None,
                   "rot": -12, "tilt": 0.4},
                  {"path": "b", "corner": "bas-gauche", "size": "petite", "pos": [0.2, 0.3], "scale": 0.3,
                   "rot": 20, "tilt": -0.5}]
        app.App._pip_save_layouts(s)
        self.assertEqual((s.conf["pip_rot"], s.conf["pip_tilt"]), (-12, 0.4))
        lay0 = app.App._pip_slot_layout(s, 0)
        lay1 = app.App._pip_slot_layout(s, 1)
        self.assertEqual((lay0["rot"], lay0["tilt"]), (-12, 0.4))
        self.assertEqual((lay1["rot"], lay1["tilt"]), (20, -0.5))
        s.pips = s.pips[:1]
        self.assertEqual(app.App._pip_slot_layout(s, 3)["rot"], 0)


if __name__ == "__main__":
    unittest.main()
