"""1.51 : grande photo en AVIF (mode hybride) préparée bien plus vite : qualité cherchée sur un
échantillon, photo entière compressée une seule fois (ou quelques fois si elle dépasse)."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import numpy as np  # noqa: E402
from PIL import Image, ImageFilter  # noqa: E402
import engine  # noqa: E402


def photo(w=2200, h=1400, seed=5):
    rng = np.random.default_rng(seed)
    a = np.zeros((h, w, 3), dtype=np.uint8)
    a[: h // 2] = np.linspace(120, 230, h // 2, dtype=np.uint8)[:, None, None]
    a[h // 2:] = (rng.random((h - h // 2, w, 3)) * 255).astype(np.uint8)
    return Image.fromarray(a).filter(ImageFilter.GaussianBlur(1.5))


class AvifRapide(unittest.TestCase):
    def test_tient_et_peu_d_encodages(self):
        im = photo()
        sizes = []
        real = engine._encode

        def spy(img, fmt, q, speed):
            sizes.append(img.size)
            return real(img, fmt, q, speed)
        target = 400_000
        with mock.patch.object(engine, "_encode", spy):
            data, q, size = engine.compress(im, "originale", target, "avif")
        self.assertLessEqual(len(data), target)
        self.assertGreater(len(data), target * 0.6)                    # la place est bien utilisée
        self.assertEqual(size, im.size)
        self.assertLessEqual(sum(1 for s in sizes if s == im.size), 3)  # avant : une quinzaine
        self.assertTrue(Image.open(__import__("io").BytesIO(data)).size == im.size)

    def test_petite_image_inchangee(self):
        im = photo(800, 500)
        data, q, _ = engine.compress(im, "originale", 40_000, "avif")
        self.assertLessEqual(len(data), 40_000)


if __name__ == "__main__":
    unittest.main()
