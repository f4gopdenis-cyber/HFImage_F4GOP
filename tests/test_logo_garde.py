"""Version 1.66 : le logo (et les images du PC) incrustés restent en place après un redémarrage."""
import os
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class LogoGarde(unittest.TestCase):
    def setUp(self):
        try:
            import app
        except ImportError as e:
            self.skipTest(str(e))
        self.app = app
        d = tempfile.mkdtemp()
        self.logo = os.path.join(d, "logo.png")
        Image.new("RGBA", (40, 20), (255, 0, 0, 128)).save(self.logo)
        self.recu = os.path.join(d, "F1ABC.png")
        Image.new("RGB", (40, 20)).save(self.recu)

    def stub(self, conf):
        A = self.app.App

        class S:
            PIP_MAX_N, PIP_KEEP_KEYS = A.PIP_MAX_N, A.PIP_KEEP_KEYS
            _pip_keep_load, _pip_keep_save = A._pip_keep_load, A._pip_keep_save
        s = S()
        s.conf, s.pips = conf, []
        return s

    def test_aller_retour(self):
        s = self.stub({})
        s.pips = [{"path": self.logo, "call": "", "local": True, "logo": True, "opa": 0.6, "corner": "libre",
                   "pos": [0.8, 0.1], "scale": 0.2, "rot": 15, "tilt": 0, "shape": "rect", "size": "libre"},
                  {"path": self.recu, "call": "F1ABC", "snr": 7, "corner": "haut-gauche", "size": "petite"}]
        s._pip_keep_save()
        self.assertEqual([p["path"] for p in s.conf["pip_keep"]], [self.logo])     # image reçue : pas gardée
        t = self.stub(dict(s.conf))                                               # nouveau lancement
        t._pip_keep_load()
        self.assertEqual(len(t.pips), 1)
        p = t.pips[0]
        self.assertEqual((p["path"], p["logo"], p["opa"], p["pos"], p["rot"]), (self.logo, True, 0.6, [0.8, 0.1], 15))

    def test_fichier_disparu(self):
        t = self.stub({"pip_keep": [{"path": "/n/existe/pas.png", "local": True}, "n'importe quoi"]})
        t._pip_keep_load()
        self.assertEqual(t.pips, [])


if __name__ == "__main__":
    unittest.main()
