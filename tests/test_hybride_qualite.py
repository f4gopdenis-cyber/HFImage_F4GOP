"""Version 1.04 : en hybride, l'image part en pleine qualité (fichier original) par défaut."""
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


def _app():
    try:
        import app
        return app
    except (ImportError, OSError) as e:
        raise unittest.SkipTest(str(e))


class Reglages(unittest.TestCase):
    def conf(self, saved):
        app = _app()
        p = os.path.join(tempfile.mkdtemp(), "c.json")
        if saved is not None:
            with open(p, "w") as f:
                json.dump(saved, f)
        with mock.patch.object(app, "CONF_PATH", p):
            return app.load_conf()

    def test_nouvelle_installation(self):
        c = self.conf(None)
        self.assertEqual((c["hyb_fmt"], c["hyb_width"]), ("original", "originale"))

    def test_anciens_reglages_trop_petits(self):
        c = self.conf({"conf_v": 63, "hyb_width": 1024, "hyb_kb": 60, "hyb_fmt": "avif"})
        self.assertEqual((c["hyb_fmt"], c["hyb_width"], c["hyb_kb"]), ("original", "originale", 3000))

    def test_choix_personnel_garde(self):
        c = self.conf({"conf_v": 63, "hyb_width": 1920, "hyb_kb": 800, "hyb_fmt": "jpg"})
        self.assertEqual((c["hyb_fmt"], c["hyb_width"], c["hyb_kb"]), ("jpg", 1920, 800))


class Image(unittest.TestCase):
    def test_photo_part_telle_quelle(self):
        app = _app()
        import i18n
        from PIL import Image as PI
        home = tempfile.mkdtemp()
        p = os.path.join(home, "photo.jpg")
        im = PI.effect_noise((2400, 1600), 60).convert("RGB")
        im.save(p, quality=92)
        raw = open(p, "rb").read()
        with mock.patch.dict(os.environ, {"HOME": home, "APPDATA": home, "LOCALAPPDATA": home}), \
                mock.patch.object(app, "CONF_PATH", os.path.join(home, "absent", "c.json")), \
                mock.patch.object(i18n, "detect_lang", lambda: "fr"), \
                mock.patch.object(app.App, "_startup_dialogs", lambda self: None), \
                mock.patch.object(app.App, "net_start", lambda self: None), \
                mock.patch.object(app.messagebox, "showinfo", lambda *a, **k: None):
            try:
                a = app.App()
            except Exception as e:
                self.skipTest(f"fenêtre principale impossible ici : {e}")
            try:
                a.load_image(p)
                a.v_hyb.set(True)
                a._toggle_hyb_ui()
                a.prepare(sync=True)
                self.assertEqual(a.tx.data, raw)                     # pleine qualité, octet pour octet
                with mock.patch.object(app, "HYB_MAX_BYTES", 50_000):
                    a.tx = None
                    a.prepare(sync=True)
                    self.assertLessEqual(len(a.tx.data), 50_000)    # trop gros : recompressée
                    self.assertGreaterEqual(PI.open(io.BytesIO(a.tx.data)).width, 320)
            finally:
                a.destroy()


if __name__ == "__main__":
    unittest.main()
