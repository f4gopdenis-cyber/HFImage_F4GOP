"""1.98 (signalé par F4GOP, image de F5TGB en RS4) : une image EasyPal protégée par Reed-Solomon
(RS1 à RS4) n'était reconstruite qu'après réception du tout dernier segment, et seulement à partir de
63 % des segments : avec RS4, EasyPal l'affichait une minute plus tôt. Le nombre total de segments est
maintenant lu dans l'en-tête, et la reconstruction est tentée dès que le code RS peut y suffire."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

FS = 48000


class RS4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import hamdrm
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        if not hamdrm.AVAILABLE:
            raise unittest.SkipTest("bibliothèque HamDRM absente")
        cls.h = hamdrm
        rng = np.random.default_rng(1)
        cls.data = rng.integers(0, 256, 6000, dtype=np.uint8).tobytes()
        p = hamdrm.make_params("F5TGB", mode=1, bandwidth=1, qam=1, rs=4)
        cls.sig = hamdrm.tx_file(cls.data, "photo", "jpg", p)

    def recoit(self, coupures):
        """-> (instant de réception en s ou None, segments reçus)."""
        s = self.sig.copy()
        for a, b in coupures:
            s[int(a * FS):int(b * FS) if b else None] = 0
        x = np.concatenate([np.zeros(FS, np.float32), s * 0.8, np.zeros(2 * FS, np.float32)])
        rx = self.h.Receiver()
        rx.reset()
        got = None
        try:
            for i in range(0, len(x), 4800):
                rx.process(x[i:i + 4800])
                for f in rx.files():
                    if f["data"] == self.data and got is None:
                        got = (i - FS) / FS
            return got, rx.status()["seg_received"]
        finally:
            rx.reset()

    def test_dernier_segment_perdu(self):
        # en-tête et dernier segment perdus, fin de l'émission coupée : 60 % des segments
        got, n = self.recoit([(2.6, 3.2), (38, None)])
        self.assertIsNotNone(got, f"image non reconstruite avec {n} segments (RS4)")

    def test_reconstruite_des_que_possible(self):
        got, n = self.recoit([])
        self.assertIsNotNone(got)
        self.assertLess(got, 37)            # avant : 39,7 s (seuil fixe de 63 % des segments)


if __name__ == "__main__":
    unittest.main()
