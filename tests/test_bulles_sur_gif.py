"""1.41 : répondre avec un GIF animé reçu + une bulle : la bulle est dessinée sur chaque image
et l'animation d'origine est gardée (avant, le GIF repartait tel quel, sans la bulle)."""
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image  # noqa: E402
import bubbles  # noqa: E402
import imgfmt  # noqa: E402


def gif(colors, dur=200, size=(200, 150)):
    fr = [Image.new("RGB", size, c) for c in colors]
    b = io.BytesIO()
    fr[0].save(b, "GIF", save_all=True, append_images=fr[1:], duration=dur, loop=0)
    return b.getvalue()


class BullesSurGif(unittest.TestCase):
    def test_bulle_sur_chaque_image(self):
        src = gif([(200, 0, 0), (0, 0, 200), (0, 160, 0)])
        b = bubbles.new("Merci Bob !", cx=0.5, cy=0.5)
        data, how = bubbles.gif_with_bubbles(src, json.dumps([b]), 2_000_000)
        frames, durs = imgfmt.gif_frames(data)
        self.assertEqual(len(frames), 3)                         # animation d'origine gardée
        self.assertEqual(sum(durs), 600)
        for f, c in zip(frames, ((200, 0, 0), (0, 0, 200), (0, 160, 0))):
            self.assertGreater(min(f.getpixel((100, 70))), 200)  # fond blanc de la bulle au centre
            corner = f.getpixel((3, 3))
            self.assertLess(sum(abs(a - b) for a, b in zip(corner, c)), 60)   # couleur d'origine autour

    def test_emoticone_animee_ajoutee(self):
        src = gif([(200, 0, 0), (0, 0, 200)], dur=540)
        heart = next(ch for ch, code in bubbles.EMOJI.items() if code == "2764")
        b = dict(bubbles.new("73 " + heart, cx=0.5, cy=0.5), anim=True)
        data, _ = bubbles.gif_with_bubbles(src, json.dumps([b]), 2_000_000)
        frames, durs = imgfmt.gif_frames(data)
        self.assertGreater(len(frames), 2)                       # images longues découpées : le cœur bat
        self.assertEqual(sum(durs), 1080)
        self.assertGreater(len({f.tobytes() for f in frames[:6]}), 1)

    def test_taille_max(self):
        import random
        random.seed(1)
        fr = [Image.frombytes("RGB", (400, 300), bytes(random.getrandbits(8) for _ in range(400 * 300 * 3)))
              for _ in range(4)]
        b = io.BytesIO()
        fr[0].save(b, "GIF", save_all=True, append_images=fr[1:], duration=100, loop=0)
        data, how = bubbles.gif_with_bubbles(b.getvalue(), json.dumps([bubbles.new("Hi")]), 150_000)
        self.assertLessEqual(len(data), 150_000)
        self.assertTrue(how)


if __name__ == "__main__":
    unittest.main()
