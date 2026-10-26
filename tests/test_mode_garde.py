"""Version 1.72 : un mode choisi à la main n'est plus changé par les images reçues pendant 10 min (G0GOO)."""
import os
import sys
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class ModeGarde(unittest.TestCase):
    def stub(self):
        try:
            import app
        except ImportError as e:
            self.skipTest(str(e))
        A = app.App
        s = mock.Mock()
        s.MODE_KEEP_S = A.MODE_KEEP_S
        s.tx_busy = False
        s.v_follow.get.return_value = True
        mode = {"v": "Auto"}
        s.v_mode.get.side_effect = lambda: mode["v"]
        s.v_mode.set.side_effect = lambda v: mode.update(v=v)
        s.v_drm = {}
        s.follow = lambda: A._follow_mode(s, {"call": "G4ABC", "hybrid": True}, "/x/y.jpg", True)
        s._mode_chosen = lambda: A._mode_chosen(s)
        return s, mode, app

    def test_image_easypal_change_le_mode(self):
        s, mode, app = self.stub()
        s._mode_manual_t = 0
        s.follow()
        self.assertEqual(mode["v"], app.engine.DRM_MODE)

    def test_choix_a_la_main_garde(self):
        s, mode, app = self.stub()
        s._mode_chosen()
        s.follow()
        self.assertEqual(mode["v"], "Auto")
        s._mode_manual_t = time.time() - 601                  # 10 minutes plus tard
        s.follow()
        self.assertEqual(mode["v"], app.engine.DRM_MODE)


if __name__ == "__main__":
    unittest.main()
