"""1.32 : émoticônes animées dans les bulles (mode hybride : GIF animé)."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import bubbles  # noqa: E402
import imgfmt  # noqa: E402
from PIL import Image  # noqa: E402


class Animees(unittest.TestCase):
    def test_gif_anime(self):
        im = Image.new("RGB", (1600, 1200), (90, 140, 200))
        b = bubbles.new("73 ❤ 👋 😉", cx=0.5, cy=0.3)
        self.assertFalse(bubbles.has_anim([b]))
        b["anim"] = True
        self.assertTrue(bubbles.has_anim([b]))
        self.assertFalse(bubbles.has_anim([dict(b, text="73 sans émoticône")]))
        data, how = bubbles.make_gif(im, json.dumps([b]), wmax=800)
        self.assertTrue(imgfmt.is_animated_gif(data))
        n, secs = imgfmt.gif_info(data)
        self.assertEqual(n, bubbles.ANIM_FRAMES)
        self.assertEqual(Image.open(__import__("io").BytesIO(data)).size, (800, 600))
        frames, _ = imgfmt.gif_frames(data)
        self.assertNotEqual(frames[0].tobytes(), frames[3].tobytes())      # ça bouge

    def test_fixe_sans_anim(self):
        im = Image.new("RGB", (400, 300), (90, 140, 200))
        b = bubbles.new("73 ❤", cx=0.5, cy=0.3)
        self.assertEqual(bubbles.draw(im, [b], 0.25).tobytes(), bubbles.draw(im, [b]).tobytes())

    def test_toutes_les_emoticones(self):
        for ch in bubbles.EMOJI:
            for t in (0.0, 0.3, 0.8):
                em, dx, dy = bubbles.anim_emoji(ch, 30, t)
                self.assertIsNotNone(em, ch)


if __name__ == "__main__":
    unittest.main()
