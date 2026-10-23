"""1.24 (demande de VK6NJP) : image hybride déposée d'avance, l'émission ne redépose pas."""
import os
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class DepotAvance(unittest.TestCase):
    def setUp(self):
        try:
            import app
        except (ImportError, OSError) as e:
            self.skipTest(str(e))
        self.app = app
        self.uploads = []
        cfg = {"host": "ftp.qsl.net", "port": 21, "user": "vk6njp", "dir": "hfimage",
               "url": "https://www.qsl.net/vk6njp/hfimage/"}
        s = types.SimpleNamespace(tx_busy=False, logs=[], conf={}, btn_pre=None)
        s.v_hyb = types.SimpleNamespace(get=lambda: True)
        s.log = s.logs.append
        s.log_exc = lambda *a: s.logs.append(a)
        s.ui = lambda fn, *a: fn(*a)
        s._set_text = lambda *a: None
        s.pb_tx = types.SimpleNamespace(configure=lambda *a: None)
        s._hyb_cfg = lambda: dict(cfg)
        s._pre_sig = app.App._pre_sig

        def up(tx, c, drm):
            self.uploads.append(drm)
            return f"https://www.qsl.net/vk6njp/hfimage/{len(self.uploads)}.jpg"
        s._hyb_upload = up
        s._pre_or_upload = app.App._pre_or_upload.__get__(s)
        s.tx = app.HybridJob(b"image-1", "jpeg", "VK6NJP")
        self.s, self.cfg = s, cfg

    def run_pre(self):
        class T:
            def __init__(self, target, daemon):
                self.t = target

            def start(self):
                self.t()
        with mock.patch.object(self.app.threading, "Thread", T):
            self.app.App.hyb_preupload(self.s)

    def test_depose_une_seule_fois(self):
        self.run_pre()
        self.assertEqual(self.uploads, [False])
        url = self.s._pre_or_upload(self.s.tx, dict(self.cfg), drm=False)      # « Émettre »
        self.assertEqual(url, "https://www.qsl.net/vk6njp/hfimage/1.jpg")
        self.assertEqual(self.uploads, [False])                              # pas de second dépôt
        # émission suivante de la même image : nouveau dépôt (comme avant)
        self.s._pre_or_upload(self.s.tx, dict(self.cfg), drm=False)
        self.assertEqual(len(self.uploads), 2)

    def test_image_ou_serveur_change(self):
        self.run_pre()
        other = self.app.HybridJob(b"image-2", "jpeg", "VK6NJP")
        other.pre = self.s.tx.pre
        self.s._pre_or_upload(other, dict(self.cfg), drm=False)
        self.assertEqual(len(self.uploads), 2)                               # autre image : redéposée
        self.s._pre_or_upload(self.s.tx, dict(self.cfg, dir="autre"), drm=False)
        self.assertEqual(len(self.uploads), 3)                               # autre dossier : redéposée

    def test_deja_deposee(self):
        self.run_pre()
        self.run_pre()
        self.assertEqual(self.uploads, [False])
        self.assertTrue(any("déjà" in str(m) for m in self.s.logs))

    def test_hybride_easypal(self):
        self.s.tx.drm = True
        self.s._hyb_upload = lambda tx, c, drm: (self.uploads.append(drm) or ("de_VK6NJP-1-x.jpg", b"blob"))
        self.run_pre()
        self.assertEqual(self.s._pre_or_upload(self.s.tx, dict(self.cfg), drm=True), ("de_VK6NJP-1-x.jpg", b"blob"))
        self.assertEqual(self.uploads, [True])


if __name__ == "__main__":
    unittest.main()
