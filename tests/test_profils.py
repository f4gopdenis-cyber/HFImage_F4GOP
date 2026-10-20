"""Version 1.05 : plusieurs HFImage ouverts en même temps (profils), ex. 40 m + 20 m + 28,680 MHz."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import presence  # noqa: E402


def _app():
    try:
        import app
        return app
    except (ImportError, OSError) as e:
        raise unittest.SkipTest(str(e))


class Profils(unittest.TestCase):
    def test_argument(self):
        app = _app()
        argv = ["HFImage.exe", "--profil", "20m"]
        self.assertEqual(app._take_profile(argv), "20m")
        self.assertEqual(argv, ["HFImage.exe"])
        argv = ["HFImage.exe", "--profile=28 MHz!", "--selftest", "r.txt"]
        self.assertEqual(app._take_profile(argv), "28MHz")
        self.assertEqual(argv, ["HFImage.exe", "--selftest", "r.txt"])
        self.assertEqual(app._take_profile(["HFImage.exe"]), "")

    def test_nouveau_profil_part_des_reglages_habituels(self):
        app = _app()
        d = tempfile.mkdtemp()
        main, prof = os.path.join(d, ".hfimage.json"), os.path.join(d, ".hfimage_20m.json")
        with open(main, "w") as f:
            json.dump({"conf_v": 64, "callsign": "F-12345", "in_dev": "1: Câble A", "folder": "C:/HF"}, f)
        out = os.path.join(d, "HFImage", "20m")
        with mock.patch.multiple(app, PROFILE="20m", CONF_PATH=prof, CONF_MAIN=main, DEFAULT_OUT=out):
            c = app.load_conf()
        self.assertEqual((c["callsign"], c["in_dev"], c["folder"]), ("F-12345", "1: Câble A", out))
        with open(prof, "w") as f:                       # ensuite : ses propres réglages
            json.dump({"conf_v": 64, "callsign": "F-12345", "in_dev": "2: Câble B", "folder": out}, f)
        with mock.patch.multiple(app, PROFILE="20m", CONF_PATH=prof, CONF_MAIN=main, DEFAULT_OUT=out):
            self.assertEqual(app.load_conf()["in_dev"], "2: Câble B")

    def test_une_presence_par_instance(self):
        p = presence.Presence(presence.DEFAULT_HOST, 1883, None, None, None)
        p.call = "F-12345"
        self.assertEqual(p._st_topic(), f"{presence.BASE}/st/F-12345")
        p.tag = "20m"
        self.assertEqual(p._st_topic(), f"{presence.BASE}/st/F-12345~20M")

    def test_commande_de_lancement(self):
        app = _app()
        cmd = app.App._launch_cmd("20m")
        self.assertEqual(cmd[-2:], ["--profil", "20m"])


if __name__ == "__main__":
    unittest.main()
