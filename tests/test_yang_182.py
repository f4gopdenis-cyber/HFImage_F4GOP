"""1.82 (BH2RMX) : indicatifs bloqués, bulles d'aide dans l'écran, WAV en mode EasyPal, nom du mode
sur la cascade."""
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import app  # noqa: E402


class Blocage(unittest.TestCase):
    def test_liste(self):
        lst = "bh2xxx, F4ABC;EA1Z  k1aa"
        for c in ("BH2XXX", "f4abc", "F4ABC/P", "EA/F4ABC", "EA1Z", "K1AA"):
            self.assertTrue(app.call_blocked(c, lst), c)
        for c in ("F4GOP", "F4AB", "?", "", None):
            self.assertFalse(app.call_blocked(c, lst), c)
        self.assertFalse(app.call_blocked("F4ABC", ""))

    def test_image_bloquee_effacee(self):
        import tempfile
        d = tempfile.mkdtemp()
        p1 = os.path.join(d, "a.avif")
        p2 = os.path.join(d, "a.png")
        for p in (p1, p2):
            open(p, "wb").close()
        logs = []
        s = types.SimpleNamespace(conf={"rx_block": "F4ABC"}, log=logs.append,
                                  pb_rx=types.SimpleNamespace(configure=lambda **k: None),
                                  _full_call=lambda c: c)
        for k in ("is_blocked", "_drop_blocked", "_got_image"):
            setattr(s, k, getattr(app.App, k).__get__(s))
        s._got_image({"call": "F4ABC", "id": 1, "size": 10}, p1, p2, "DATAC1")
        self.assertFalse(os.path.exists(p1) or os.path.exists(p2))
        self.assertTrue(any("F4ABC" in m for m in logs))


class Bulles(unittest.TestCase):
    def test_bord_droit_et_bas(self):
        self.assertEqual(app.tip_pos(100, 100, 200, 20, 1920, 1080), (112, 116))
        x, y = app.tip_pos(1900, 100, 200, 20, 1920, 1080)
        self.assertEqual(x, 1900 - 8 - 200)                 # à gauche de la souris
        x, y = app.tip_pos(100, 1070, 200, 20, 1920, 1080)
        self.assertEqual(y, 1070 - 8 - 20)                  # au-dessus


if __name__ == "__main__":
    unittest.main()
