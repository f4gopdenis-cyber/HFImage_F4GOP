"""2.46 (demande de VK6ATI) : après « ⇪ Déposer », le bouton passe en vert « ✔ Déposée » tant que
l'image déposée d'avance attend d'être émise."""
import gc
import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class DepotVert(unittest.TestCase):
    def setUp(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.appmod = app
        conf = os.path.join(tempfile.mkdtemp(), "c.json")
        with open(conf, "w") as f:
            json.dump({"callsign": "VK6ATI", "licence_ok": "1.0", "lang": "fr"}, f)
        gc.collect()
        self.p = mock.patch.object(app, "CONF_PATH", conf)
        self.p.start()
        try:
            self.a = app.App()
        except Exception as e:
            self.p.stop()
            raise unittest.SkipTest(str(e))
        a = self.a
        a.v_hyb.set(True)
        a._toggle_hyb_ui()
        a.tx = app.HybridJob(b"\xff\xd8\xffimage", "jpeg", "VK6ATI")
        a._hyb_cfg = lambda: {"host": "ftp.example.org", "url": "https://example.org/", "dir": ""}
        a._hyb_upload = lambda tx, cfg, drm: "https://example.org/img.jpg"

    def tearDown(self):
        self.a.destroy()
        self.p.stop()

    def wait(self, cond, s=3.0):
        end = time.time() + s
        while time.time() < end and not cond():
            self.a.update()
            time.sleep(0.02)

    def test_vert_apres_depot_puis_normal(self):
        a, b = self.a, self.a.btn_pre
        normal_bg = b.cget("bg")
        self.assertEqual(b.cget("text"), "⇪ Déposer")
        a.hyb_preupload()
        self.wait(lambda: b.cget("text") == "✔ Déposée")
        self.assertEqual(b.cget("text"), "✔ Déposée")
        self.assertEqual(b.cget("bg"), a.PRE_DONE_BG)
        # nouvelle image : plus déposée -> bouton normal (vérifié par le tic de 300 ms)
        a.tx = self.appmod.HybridJob(b"autre", "jpeg", "VK6ATI")
        self.wait(lambda: b.cget("text") == "⇪ Déposer", 2)
        self.assertEqual(b.cget("text"), "⇪ Déposer")
        self.assertEqual(b.cget("bg"), normal_bg)

    def test_emission_utilise_le_depot(self):
        a, b = self.a, self.a.btn_pre
        a.hyb_preupload()
        self.wait(lambda: b.cget("text") == "✔ Déposée")
        tx = a.tx
        a._pre_or_upload(tx, a._hyb_cfg(), False)                 # l'émission prend le dépôt
        self.wait(lambda: b.cget("text") == "⇪ Déposer", 2)
        self.assertEqual(b.cget("text"), "⇪ Déposer")

    def test_hors_hybride(self):
        a = self.a
        a.tx.pre = ("sig", "res")
        a.v_hyb.set(False)
        self.assertFalse(a._pre_ready())


if __name__ == "__main__":
    unittest.main()
