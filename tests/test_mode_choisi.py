"""Version 1.10 : après une image EasyPal reçue, le mode choisi à la main (Auto) est gardé."""
import os
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class ModeChoisi(unittest.TestCase):
    def test_auto_garde_apres_easypal(self):
        try:
            import app
            import i18n
        except (ImportError, OSError) as e:
            self.skipTest(str(e))
        home = tempfile.mkdtemp()
        with mock.patch.dict(os.environ, {"HOME": home, "APPDATA": home, "LOCALAPPDATA": home}), \
                mock.patch.object(app, "CONF_PATH", os.path.join(home, "absent", "c.json")), \
                mock.patch.object(i18n, "detect_lang", lambda: "fr"), \
                mock.patch.object(app.App, "_startup_dialogs", lambda self: None), \
                mock.patch.object(app.App, "net_start", lambda self: None):
            try:
                a = app.App()
            except Exception as e:
                self.skipTest(f"fenêtre principale impossible ici : {e}")
            try:
                a.rx_stream = object()                      # « écoute en cours »
                a.v_follow.set(True)
                a.v_mode.set("Auto")
                now = time.time()
                st = {"time_sync": True, "fac_valid": True, "msc_valid": True, "seg_received": 40,
                      "seg_total": 40, "callsign": "RK1AT", "mode": 1, "qam": 16, "bandwidth": 1}
                eng = types.SimpleNamespace(drm_status=st, drm_good=st, drm_t=now, drm_done_t=now,
                                            activity={}, drm_incomplete=lambda: None)
                a._update_panel_drm(eng, now, True)
                self.assertEqual(a.v_mode.get(), app.engine.DRM_MODE)      # suit la station EasyPal
                a.v_mode.set("Auto")                                       # choix à la main
                for k in range(5):                                         # rafraîchissements suivants
                    a._update_panel_drm(eng, now + k, True)
                self.assertEqual(a.v_mode.get(), "Auto")
                eng.drm_t = now - 30                                       # fin du signal…
                a._update_panel_drm(eng, now, True)
                eng.drm_t = time.time()                                    # …nouvelle émission EasyPal
                a._update_panel_drm(eng, eng.drm_t, True)
                self.assertEqual(a.v_mode.get(), app.engine.DRM_MODE)
            finally:
                a.rx_stream = None
                a.destroy()


if __name__ == "__main__":
    unittest.main()
