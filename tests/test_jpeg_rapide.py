"""1.44 : image hybride en JPEG (grande photo) préparée plus vite : la qualité est estimée sur un
échantillon de la photo puis confirmée sur la photo entière ; même résultat que la recherche
complète."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402
import engine  # noqa: E402


def photo(w=1800, h=1200, seed=3):
    """Photo d'essai inégale : ciel lisse en haut, détails en bas, un objet net au milieu."""
    rng = np.random.default_rng(seed)
    a = np.zeros((h, w, 3), dtype=np.uint8)
    a[: h // 2] = np.linspace(120, 230, h // 2, dtype=np.uint8)[:, None, None]          # ciel
    a[h // 2:] = (rng.random((h - h // 2, w, 3)) * 255).astype(np.uint8)                 # herbe
    im = Image.fromarray(a).filter(ImageFilter.GaussianBlur(1.2))
    d = ImageDraw.Draw(im)
    d.rectangle([w // 3, h // 3, w // 2, h // 2], fill=(200, 20, 20))
    d.text((40, 40), "F4GOP IN98QR", fill=(0, 0, 0))
    return im


def full_search(img, target):
    best, lo, hi = None, 1, 95
    while lo <= hi:
        m = (lo + hi) // 2
        if len(engine._encode(img, "jpeg", m, 6)) <= target:
            best, lo = m, m + 1
        else:
            hi = m - 1
    return best


class JpegRapide(unittest.TestCase):
    def test_meme_resultat(self):
        im = photo()
        for target in (300_000, 700_000, 1_500_000):
            data, q, size = engine.compress(im, "originale", target, "jpeg")
            self.assertLessEqual(len(data), target)
            self.assertEqual(q, full_search(im, target), target)
            self.assertEqual(size, im.size)

    def test_peu_d_encodages_de_la_photo_entiere(self):
        im = photo()
        sizes = []
        real = engine._encode

        def spy(img, fmt, q, speed):
            sizes.append(img.size)
            return real(img, fmt, q, speed)
        with mock.patch.object(engine, "_encode", spy):
            engine.compress(im, "originale", 700_000, "jpeg")
        self.assertLessEqual(sum(1 for s in sizes if s == im.size), 4)       # avant : une dizaine

    def test_petite_image_inchangee(self):
        im = photo(600, 400)                                   # sous le seuil : recherche habituelle
        data, q, _ = engine.compress(im, "originale", 60_000, "jpeg")
        self.assertLessEqual(len(data), 60_000)
        self.assertEqual(q, full_search(im, 60_000))


if __name__ == "__main__":
    unittest.main()
