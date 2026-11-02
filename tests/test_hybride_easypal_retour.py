"""1.96 (signalé par VK6NJP) : en hybride, repasser d'EasyPal à un mode DATAC avec la même image
envoyait encore l'annonce EasyPal : l'image préparée gardait son étiquette « EasyPal »."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Retour(unittest.TestCase):
    def test_easypal_puis_datac1x_meme_image(self):
        try:
            import app
            import engine
            import i18n
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        from PIL import Image as PI
        home = tempfile.mkdtemp()
        p = os.path.join(home, "photo.jpg")
        PI.effect_noise((640, 480), 60).convert("RGB").save(p, quality=90)
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
                a.v_mode.set(engine.DRM_MODE)
                a.prepare(sync=True)
                self.assertTrue(getattr(a.tx, "drm", False))            # hybride EasyPal
                a.tx.pre = ("dépôt EasyPal", ("nom", b"blob"))          # dépôt d'avance EasyPal
                a.v_mode.set("DATAC1X")
                a.prepare(sync=True)
                self.assertIsInstance(a.tx, app.HybridJob)
                self.assertFalse(a.tx.drm)                             # annonce HFImage (DATAC)
                self.assertIsNone(a.tx.pre)                            # le dépôt EasyPal n'est pas repris
                a.v_mode.set(engine.DRM_MODE)
                a.prepare(sync=True)
                self.assertTrue(a.tx.drm)                              # et retour EasyPal possible
            finally:
                a.destroy()


if __name__ == "__main__":
    unittest.main()
