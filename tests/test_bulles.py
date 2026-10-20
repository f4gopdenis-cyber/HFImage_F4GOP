"""Version 1.06 : bulles de texte façon BD sur l'image émise."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from PIL import Image  # noqa: E402

import bubbles  # noqa: E402


class Bulles(unittest.TestCase):
    def setUp(self):
        self.im = Image.new("RGB", (800, 600), (40, 90, 160))

    def test_dessin_tous_styles(self):
        for st in bubbles.STYLES:
            b = dict(bubbles.new("Bonjour de Flers ! 73", st, "moyenne", 0.3, 0.3), tx=0.6, ty=0.8)
            out = bubbles.draw(self.im, [b])
            self.assertEqual(out.size, self.im.size)
            g = bubbles.layout(800, 600, b)
            x = int(g["cx"] - g["rx"] + max(g["lw"] * 3, 6))      # dans la bulle, à côté du texte
            self.assertGreater(min(out.getpixel((x, int(g["cy"])))), 230, st)
            self.assertEqual(self.im.getpixel((240, 150)), (40, 90, 160))      # original intact

    def test_bulle_vide_ignoree(self):
        self.assertIs(bubbles.draw(self.im, [bubbles.new("   ")]), self.im)

    def test_reste_dans_l_image(self):
        b = bubbles.new("Texte assez long pour une grande bulle", "cri", "grande", 0.99, 0.99)
        x0, y0, x1, y1 = bubbles.layout(800, 600, b)["box"]
        self.assertTrue(x0 >= 0 and y0 >= 0 and x1 <= 800 and y1 <= 600)

    def test_taille_relative(self):
        b = bubbles.new("73", size="moyenne")
        self.assertEqual(bubbles.font_px(600, "moyenne") * 2, bubbles.font_px(1200, "moyenne"))
        self.assertGreaterEqual(bubbles.font_px(120, "petite"), bubbles.MIN_PX)
        small, big = bubbles.layout(400, 300, b), bubbles.layout(800, 600, b)
        self.assertAlmostEqual(big["cx"] / small["cx"], 2, delta=0.1)

    def test_clic(self):
        b = dict(bubbles.new("Salut", "parole", "moyenne", 0.5, 0.3), tx=0.5, ty=0.8)
        self.assertEqual(bubbles.hit(800, 600, [b], 400, 180), (0, "bulle"))
        self.assertEqual(bubbles.hit(800, 600, [b], 400, 480), (0, "pointe"))
        self.assertIsNone(bubbles.hit(800, 600, [b], 20, 20))


if __name__ == "__main__":
    unittest.main()
