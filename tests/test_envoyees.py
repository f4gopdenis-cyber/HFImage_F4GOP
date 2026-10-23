"""1.34 (demande de RK1AT) : dossier « envoyees » sans doublons, et seulement les N dernières si on veut."""
import io
import os
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


def jpeg(color):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (64, 48), color).save(b, "JPEG")
    return b.getvalue()


class Envoyees(unittest.TestCase):
    def setUp(self):
        try:
            import app
            import gallery
        except (ImportError, OSError) as e:
            self.skipTest(str(e))
        self.app, self.gallery = app, gallery
        self.dir = tempfile.mkdtemp()
        s = types.SimpleNamespace(conf={}, gal_store=gallery.GalleryStore(self.dir),
                                  gal=types.SimpleNamespace(refresh=lambda: None), mycall=lambda: "RK1AT",
                                  log_exc=lambda *a: self.fail(a), _web_queue=lambda *a: None,
                                  _journal=lambda t: None, log=lambda m: None)
        for n in ("_gallery_add", "_prune_sent"):
            setattr(s, n, getattr(app.App, n).__get__(s))
        self.s = s

    def send(self, data):
        job = {"kind": "hybrid", "tx": types.SimpleNamespace(data=data)}
        self.app.App._gallery_sent(self.s, job, "DATAC13")

    def files(self):
        out = []
        for top, _d, fs in os.walk(os.path.join(self.dir, self.gallery.SENT_DIR)):
            out += fs
        return sorted(out)

    def test_pas_de_doublon(self):
        a = jpeg((200, 0, 0))
        self.send(a)
        self.send(a)                                   # même image renvoyée
        self.assertEqual(len(self.files()), 1)
        self.send(jpeg((0, 200, 0)))
        self.assertEqual(len(self.files()), 2)
        tx = [e for e in self.s.gal_store.items if e.get("dir") == "tx"]
        self.assertEqual(len(tx), 2)

    def test_la_derniere_seulement(self):
        self.send(jpeg((200, 0, 0)))
        self.send(jpeg((0, 200, 0)))
        self.s.conf["sent_keep"] = 1
        self.send(jpeg((0, 0, 200)))
        self.assertEqual(len(self.files()), 1)
        tx = [e for e in self.s.gal_store.items if e.get("dir") == "tx"]
        self.assertEqual(len(tx), 1)
        with open(tx[0]["file"], "rb") as f:
            self.assertEqual(f.read(), jpeg((0, 0, 200)))
        # images reçues (hors « envoyees ») : jamais touchées
        rx = os.path.join(self.dir, "2026-10-23")
        os.makedirs(rx)
        open(os.path.join(rx, "recue.jpg"), "wb").close()
        self.send(jpeg((90, 90, 90)))
        self.assertTrue(os.path.exists(os.path.join(rx, "recue.jpg")))
        self.assertEqual(len(self.files()), 1)


if __name__ == "__main__":
    unittest.main()
