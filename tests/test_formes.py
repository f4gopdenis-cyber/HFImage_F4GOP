"""1.50 : forme des images incrustées : rectangle (comme avant), coins arrondis, rond, ovale."""
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


class Formes(unittest.TestCase):
    def setUp(self):
        self.base = Image.new("RGB", (800, 600), BG)
        self.th = Image.new("RGB", (400, 300), TH)

    def lay(self, shape, cap=""):
        return trafic.pip_layout(self.base.size, self.th.size if shape != "rond" else (300, 300), cap,
                                 "haut-gauche", "grande", [0.5, 0.5], None, shape=shape)[:4]

    def test_rectangle_inchange(self):
        a = trafic.pip(self.base, self.th, "de F5PEY", "haut-gauche", "grande", [0.5, 0.5], None)
        b = trafic.pip(self.base, self.th, "de F5PEY", "haut-gauche", "grande", [0.5, 0.5], None, shape="rect")
        self.assertEqual(a.tobytes(), b.tobytes())

    def test_coins_arrondis(self):
        x, y, W, H = self.lay("arrondi")
        im = trafic.pip(self.base, self.th, "", "haut-gauche", "grande", [0.5, 0.5], None, shape="arrondi")
        self.assertTrue(near(im.getpixel((x + 1, y + 1)), BG))               # coin coupé
        self.assertTrue(near(im.getpixel((x + W // 2, y + H // 2)), TH))

    def test_rond(self):
        x, y, W, H = self.lay("rond")
        self.assertEqual(W, H)                                               # carré -> vrai rond
        im = trafic.pip(self.base, self.th, "", "haut-gauche", "grande", [0.5, 0.5], None, shape="rond")
        self.assertTrue(near(im.getpixel((x + W // 7, y + H // 7)), BG))     # hors du cercle
        self.assertTrue(near(im.getpixel((x + W // 2, y + H // 2)), TH))

    def test_ovale_avec_legende(self):
        x, y, W, H = self.lay("ovale", "de F5PEY")
        im = trafic.pip(self.base, self.th, "de F5PEY", "haut-gauche", "grande", [0.5, 0.5], None,
                        shape="ovale")
        self.assertTrue(near(im.getpixel((x + 2, y + 2)), BG))
        self.assertTrue(near(im.getpixel((x + W // 2, y + H // 3)), TH))
        bottom = [im.getpixel((x + W // 2, y + H - k)) for k in range(2, 8)]
        self.assertTrue(any(max(c) < 60 for c in bottom))                    # pastille sombre de la légende

    def test_logo_decoupe(self):
        logo = Image.new("RGBA", (300, 300), (30, 160, 60, 255))
        x, y, W, H = trafic.pip_layout(self.base.size, (300, 300), "", "haut-gauche", "grande", [0.5, 0.5],
                                       None, logo=True, shape="rond")[:4]
        im = trafic.pip(self.base, logo, "", "haut-gauche", "grande", [0.5, 0.5], None, logo=True, shape="rond")
        self.assertTrue(near(im.getpixel((x + 2, y + 2)), BG))
        self.assertTrue(near(im.getpixel((x + W // 2, y + H // 2)), (30, 160, 60)))

    def test_forme_inconnue(self):
        im = trafic.pip(self.base, self.th, "", "haut-gauche", "petite", None, None, shape="étoile")
        self.assertEqual(im.size, self.base.size)

    def test_forme_retenue(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        s = types.SimpleNamespace(conf={}, PIP_MAX_N=4, PIP_CORNERS=app.App.PIP_CORNERS)
        s.pips = [{"path": "a", "corner": "haut-droite", "size": "moyenne", "pos": None, "scale": None,
                   "shape": "rond"}, {"path": "b", "shape": "ovale"}]
        app.App._pip_save_layouts(s)
        self.assertEqual(app.App._pip_slot_layout(s, 0)["shape"], "rond")
        self.assertEqual(app.App._pip_slot_layout(s, 1)["shape"], "ovale")


if __name__ == "__main__":
    unittest.main()
