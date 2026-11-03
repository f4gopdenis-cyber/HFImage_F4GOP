"""1.99 (idée de VK6ATI) : Galerie, plusieurs images choisies (Ctrl+clic) envoyées l'une après l'autre,
dans le mode réglé, en respectant « Attendre fréquence libre » ; STOP arrête la série."""
import gc
import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class EnvoiGroupe(unittest.TestCase):
    def setUp(self):
        gc.collect()
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        from PIL import Image
        self.app = app
        d = tempfile.mkdtemp()
        self.conf = os.path.join(d, "c.json")
        with open(self.conf, "w") as f:
            json.dump({"callsign": "VK6ATI", "licence_ok": "1.0", "lang": "fr"}, f)
        self.files = []
        for i, col in enumerate(("red", "green", "blue")):
            p = os.path.join(d, f"img{i}.jpg")
            Image.new("RGB", (320, 240), col).save(p)
            self.files.append({"file": p, "dir": "rx", "call": f"F{i}ABC", "t": 1000 + i, "mode": "DATAC3"})
        self.p = mock.patch.object(app, "CONF_PATH", self.conf)
        self.p.start()
        try:
            self.a = app.App()
        except Exception as e:
            self.p.stop()
            raise unittest.SkipTest(str(e))
        self.a.update()

    def tearDown(self):
        self.a._closing = True
        self.a.destroy()
        self.a = None
        gc.collect()
        self.p.stop()

    def test_choix_dans_la_galerie(self):
        g = self.a.gal
        store = mock.Mock(latest=lambda d, n: list(reversed(self.files)))    # la plus récente en tête
        g.set_store(store)
        self.a.update()
        g._toggle(self.files[2])
        g._toggle(self.files[0])
        self.assertEqual([e["file"] for e in g.selected()], [self.files[0]["file"], self.files[2]["file"]])
        self.assertIn("2", g.lb_status.cget("text"))
        g._toggle(self.files[0])                                     # 2e Ctrl+clic : retirée
        self.assertEqual(len(g.selected()), 1)
        g.select_all()
        self.assertEqual(len(g.selected()), 3)
        g.clear_selection()
        self.assertEqual(g.selected(), [])

    def run_batch(self, stop_at=None):
        a = self.a
        sent = []

        def fake_transmit(*args, **kw):
            sent.append(os.path.basename(a._src_path_for_test))
            a.tx_busy = True
            if stop_at is not None and len(sent) == stop_at:
                a.stop_tx.set()                                      # STOP pendant cette image
            a.after(10, lambda: a._tx_done(False))
            return True

        orig_load = a.load_image

        def load(p):
            a._src_path_for_test = p
            return orig_load(p)
        with mock.patch.object(a, "transmit", fake_transmit), \
                mock.patch.object(a, "load_image", load), \
                mock.patch.object(a, "BATCH_PAUSE_MS", 10), \
                mock.patch.object(self.app.messagebox, "askyesno", lambda *x, **k: True), \
                mock.patch.object(a, "_tx_when_free", lambda fn, what="": fn()):
            self.assertTrue(a.gallery_send_batch(self.files))
            t = time.time()
            while a._batch is not None and time.time() - t < 10:
                a.update()
                time.sleep(0.01)
        return sent

    def test_envoyees_dans_l_ordre(self):
        sent = self.run_batch()
        self.assertEqual(sent, ["img0.jpg", "img1.jpg", "img2.jpg"])
        self.assertIsNone(self.a._batch)

    def test_stop_arrete_la_serie(self):
        sent = self.run_batch(stop_at=2)
        self.assertEqual(sent, ["img0.jpg", "img1.jpg"])
        self.assertIsNone(self.a._batch)

    def test_attente_annulee_arrete_la_serie(self):
        a = self.a
        a._batch = {"paths": ["x"], "n": 2, "k": 1}
        a._wait_cancel()
        self.assertIsNone(a._batch)


if __name__ == "__main__":
    unittest.main()
