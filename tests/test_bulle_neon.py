"""Style de bulle « néon » : texte lumineux sans bulle (lueur de la couleur choisie)."""
import os
import sys
import unittest

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import bubbles  # noqa: E402


class Neon(unittest.TestCase):
    def test_lueur_autour_du_texte(self):
        im = Image.new("RGB", (600, 300), (10, 10, 30))
        b = dict(bubbles.new("73 de F4GOP", "néon", "grande", 0.5, 0.5), fg="#ff3ec8")
        out = bubbles.draw(im, [b])
        self.assertEqual(out.size, im.size)
        px = [out.getpixel((x, 150)) for x in range(0, 600, 4)]
        self.assertTrue(any(p[0] > 150 and p[2] > 100 for p in px))      # rose visible
        self.assertEqual(out.getpixel((5, 5)), (10, 10, 30))             # loin du texte : rien

    def test_pas_de_pointe(self):
        self.assertIn("néon", bubbles.NO_TAIL)
