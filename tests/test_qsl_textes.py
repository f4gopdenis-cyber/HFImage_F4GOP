"""Version 1.68 : textes de la carte QSL déplacés à la souris (positions gardées)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

try:
    import qsl  # noqa: E402
except ImportError:
    qsl = None


@unittest.skipIf(qsl is None, "PIL absent")
class QslTextes(unittest.TestCase):
    def card(self, pos=None):
        boxes = {}
        im = qsl.make_card(None, "F4GOP", "IN98QR", "VK6NJP", "7.058 MHz", "SNR +8 dB", "TNX QSO, 73 !",
                           "2026-10-26 08:58", style={"pos": pos or {}}, boxes=boxes)
        return im, boxes

    def test_cadres_de_tous_les_blocs(self):
        _, b = self.card()
        self.assertEqual(set(b), set(qsl.BLOCKS))
        for k, (x0, y0, x1, y1) in b.items():
            self.assertTrue(0 <= x0 < x1 <= qsl.W and 0 <= y0 < y1 <= qsl.H, k)

    def test_deplacement(self):
        im0, b0 = self.card()
        im1, b1 = self.card({"call": [0.25, 0.2]})
        self.assertAlmostEqual(b1["call"][0] - b0["call"][0], 0.25 * qsl.W, delta=1)
        self.assertAlmostEqual(b1["call"][1] - b0["call"][1], 0.2 * qsl.H, delta=1)
        self.assertEqual(b1["msg"], b0["msg"])                   # les autres blocs ne bougent pas
        self.assertNotEqual(im0.tobytes(), im1.tobytes())

    def test_valeurs_folles_ignorees(self):
        _, b = self.card({"call": ["x", None], "to": [99, -99]})
        self.assertIn("call", b)


if __name__ == "__main__":
    unittest.main()
