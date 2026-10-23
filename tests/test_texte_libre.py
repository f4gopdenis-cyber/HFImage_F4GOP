"""1.34 (demande de RK1AT) : texte libre sur l'image, sans bulle."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import bubbles  # noqa: E402
from PIL import Image  # noqa: E402


class TexteLibre(unittest.TestCase):
    def test_sans_bulle(self):
        im = Image.new("RGB", (800, 600), (30, 120, 30))
        b = bubbles.new("73 de RK1AT", cx=0.5, cy=0.5)
        b.update(style="texte", fg="#ffffff", bg="#000000", tx=0.9, ty=0.9)
        out = bubbles.draw(im, [b])
        g = bubbles.layout(800, 600, b)
        x0, y0, x1, y1 = (int(v) for v in g["box"])
        crop = out.crop((x0, y0, x1, y1))
        cols = set(crop.getdata())
        self.assertIn((30, 120, 30), cols)              # le fond de l'image reste visible : pas de bulle
        self.assertTrue(any(c[0] > 240 and c[1] > 240 for c in cols))   # texte blanc
        self.assertTrue(any(max(c) < 40 for c in cols))                 # contour noir
        self.assertFalse(bubbles._has_tail(g))          # jamais de pointe
        self.assertEqual(out.getpixel((int(0.9 * 800), int(0.9 * 600))), (30, 120, 30))
        self.assertIsNone(bubbles.hit(800, 600, [b], 0.9 * 800, 0.9 * 600))


if __name__ == "__main__":
    unittest.main()
