"""2.37 : bandeau défilant (style de bulle « bandeau »), vitesse réglable."""
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image, ImageSequence  # noqa: E402
import bubbles  # noqa: E402


def _b(speed="moyenne", text="CQ CQ de F4GOP  HFImage\nMerci à tous les OM  73 !"):
    b = bubbles.new(text, style="bandeau", cy=0.9)
    b.update(bg="#0a1432", fg="#ffd75a", speed=speed)
    return b


class Bandeau(unittest.TestCase):
    def setUp(self):
        self.img = Image.new("RGB", (800, 500), (40, 120, 200))

    def test_toute_la_largeur(self):
        g = bubbles.layout(800, 500, dict(_b(), cx=0.2))
        self.assertAlmostEqual(g["box"][0], 0, delta=1)
        self.assertAlmostEqual(g["box"][2], 800, delta=1)
        self.assertEqual(len(g["lines"]), 1)                      # une seule ligne

    def test_fixe_en_radio(self):
        out = bubbles.draw(self.img, [_b()])                       # sans t : fixe
        self.assertEqual(out.size, self.img.size)
        self.assertNotEqual(out.getpixel((5, 450)), self.img.getpixel((5, 450)))   # la bande est là
        self.assertEqual(out.getpixel((400, 100)), self.img.getpixel((400, 100)))

    def test_anime_et_vitesse(self):
        self.assertTrue(bubbles.has_anim([_b()]))
        n = {sp: bubbles.anim_timing(800, 500, [_b(sp)]) for sp in bubbles.SPEEDS}
        tours = {sp: k * ms for sp, (k, ms) in n.items()}
        self.assertGreater(tours["lente"], tours["moyenne"])
        self.assertGreater(tours["moyenne"], tours["rapide"])
        data, _ = bubbles.make_gif(self.img, json.dumps([_b("rapide")]), 800, 2_000_000)
        g = Image.open(io.BytesIO(data))
        fr = [f.convert("RGB").crop((0, 420, 800, 480)) for f in ImageSequence.Iterator(g)]
        self.assertGreater(len(fr), 10)
        self.assertNotEqual(fr[0].tobytes(), fr[len(fr) // 2].tobytes())   # le texte bouge

    def test_texte_long_reduit_en_fixe(self):
        b = _b(text="très long " * 30)
        bubbles.draw(self.img, [b])                                # ne plante pas, tient dans l'image
