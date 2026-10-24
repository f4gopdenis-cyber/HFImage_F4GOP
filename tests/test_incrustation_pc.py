"""1.48 : une image du PC incrustée dans l'image émise, avec une légende libre."""
import os
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image  # noqa: E402


def _app():
    try:
        import app
        return app
    except (ImportError, OSError) as e:
        raise unittest.SkipTest(str(e))


def fake(conf=None):
    app = _app()
    s = types.SimpleNamespace(conf=dict(conf or {}), gal_store=None, heard={}, pips=[])
    s._pip_local_label = app.App._pip_local_label
    return app, s


class ImagePC(unittest.TestCase):
    def test_legendes(self):
        app, s = fake({"pip_report": True})
        recue = {"path": "x", "call": "M7WUV", "snr": 8}
        self.assertEqual(app.App._pip_caption(s, recue), "de M7WUV  —  +8 dB")
        self.assertEqual(app.App._pip_caption(s, dict(recue, cap="Merci Andy")), "Merci Andy")
        pc = {"path": "y", "call": "", "snr": None, "local": True}
        self.assertEqual(app.App._pip_caption(s, pc), "")                     # pas de « de ? »
        self.assertEqual(app.App._pip_caption(s, dict(pc, cap="Ma station")), "Ma station")

    def test_images_du_pc_retenues(self):
        app, s = fake()
        d = tempfile.mkdtemp()
        paths = []
        for i in range(12):
            p = os.path.join(d, f"photo{i}.jpg")
            Image.new("RGB", (40, 30), (i * 20, 0, 0)).save(p)
            paths.append(p)
            app.App._pip_remember_local(s, p)
        self.assertEqual(s.conf["pip_local"][0], paths[-1])                   # la dernière en tête
        self.assertEqual(len(s.conf["pip_local"]), 10)
        app.App._pip_remember_local(s, paths[5])
        self.assertEqual(s.conf["pip_local"][0], paths[5])
        self.assertEqual(s.conf["pip_local"].count(paths[5]), 1)
        os.remove(paths[11])                                                  # fichier effacé : plus proposé
        cands = app.App._pip_candidates(s)
        self.assertTrue(all(c["local"] for _, c in cands))
        self.assertTrue(all(lab.startswith("📁 ") for lab, _ in cands))
        self.assertNotIn(paths[11], [c["path"] for _, c in cands])

    def test_photo_de_telephone_redressee(self):
        app, s = fake()
        s.pips = []
        d = tempfile.mkdtemp()
        p = os.path.join(d, "tel.jpg")
        im = Image.new("RGB", (60, 40), (10, 20, 30))
        exif = Image.Exif()
        exif[0x0112] = 6                                                      # « tourner de 90° »
        im.save(p, exif=exif)
        th = app.App._pip_thumb(s, p)
        self.assertEqual(th.size, (40, 60))


if __name__ == "__main__":
    unittest.main()
