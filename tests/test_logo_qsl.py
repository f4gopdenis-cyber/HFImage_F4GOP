"""1.49 (demandes de RK1AT) : logo PNG à fond transparent incrusté sans cadre ; hauteur des
bandeaux de la carte QSL."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image, ImageDraw  # noqa: E402
import qsl  # noqa: E402
import trafic  # noqa: E402

BG = (90, 140, 190)
RED = (220, 30, 30)


def logo():
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([20, 20, 180, 180], fill=RED + (255,))
    return im


class Logo(unittest.TestCase):
    def setUp(self):
        self.base = Image.new("RGB", (800, 600), BG)

    def test_transparence(self):
        self.assertTrue(trafic.has_alpha(logo()))
        self.assertFalse(trafic.has_alpha(Image.new("RGB", (5, 5))))
        self.assertFalse(trafic.has_alpha(Image.new("RGBA", (5, 5), (1, 2, 3, 255))))   # alpha plein : non
        x, y, W, H = trafic.pip_layout(self.base.size, (200, 200), "x", "haut-gauche", "grande", None, None,
                                       logo=True)[:4]
        self.assertEqual(W, H)                                   # ni cadre ni légende
        im = trafic.pip(self.base, logo(), "de RK1AT", "haut-gauche", "grande", None, None, logo=True)
        self.assertEqual(im.getpixel((x + 2, y + 2)), BG)        # coin transparent : la photo se voit
        self.assertEqual(im.getpixel((x + W // 2, y + H // 2)), RED)
        self.assertEqual(im.getpixel((x + W // 2, y + H + 3)), BG)   # pas de légende ni d'ombre

    def test_opacite(self):
        x, y, W, H = trafic.pip_layout(self.base.size, (200, 200), "", "haut-gauche", "grande", None, None,
                                       logo=True)[:4]
        im = trafic.pip(self.base, logo(), "", "haut-gauche", "grande", None, None, logo=True, opacity=0.5)
        c = im.getpixel((x + W // 2, y + H // 2))
        self.assertTrue(abs(c[0] - (RED[0] + BG[0]) / 2) < 4 and abs(c[2] - (RED[2] + BG[2]) / 2) < 4)

    def test_logo_tourne(self):
        im = trafic.pip(self.base, logo(), "", "bas-droite", "moyenne", None, None, 30, 0.5, logo=True)
        self.assertEqual(im.size, self.base.size)


class BandeauxQSL(unittest.TestCase):
    def band_top(self, card):
        """Hauteur du bandeau du bas : première ligne (en partant du bas) qui n'est plus sombre."""
        for y in range(card.height - 1, 0, -1):
            if card.getpixel((card.width - 3, y))[2] > 150:
                return card.height - 1 - y
        return card.height

    def card(self, **st):
        bg = Image.new("RGB", (960, 600), (200, 220, 255))
        return qsl.make_card(bg, "RK1AT", "KP40", "F4GOP", "7.058 MHz", "+12 dB", "73",
                             style=dict({"band": "#000000", "band_alpha": 100}, **st))

    def test_hauteurs(self):
        normal = self.band_top(self.card())
        fin = self.band_top(self.card(band_h=50))
        haut = self.band_top(self.card(band_h=150))
        self.assertAlmostEqual(normal, 190, delta=3)
        self.assertAlmostEqual(fin, 95, delta=3)
        self.assertAlmostEqual(haut, 285, delta=3)
        self.assertEqual(self.band_top(self.card(band_h=999)), haut)          # borné

    def test_bandeau_du_haut(self):
        def head(card):
            for y in range(card.height):
                if card.getpixel((card.width // 2, y))[2] > 150:
                    return y
        self.assertLess(head(self.card(head_h=50)), head(self.card()))
        self.assertGreater(head(self.card(head_h=150)), head(self.card()))

    def test_style_par_defaut(self):
        self.assertEqual((qsl.DEFAULT_STYLE["head_h"], qsl.DEFAULT_STYLE["band_h"]), (100, 100))


if __name__ == "__main__":
    unittest.main()
