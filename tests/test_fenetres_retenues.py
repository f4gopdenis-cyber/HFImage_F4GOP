"""2.29 (F4EEH) : « Sites des stations » et « Carte des stations » se rouvrent comme on les a laissées."""
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Geo(unittest.TestCase):
    def setUp(self):
        gc.collect()
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.app = app
        d = tempfile.mkdtemp()
        self.conf = os.path.join(d, "c.json")
        with open(self.conf, "w") as f:
            json.dump({"callsign": "F4EEH", "licence_ok": "1.0", "lang": "fr", "net_on": False}, f)
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

    def test_sites_retenus(self):
        a = self.a
        a.show_sites()
        w = a.sites_win
        w.geometry("640x480+120+90")
        a.update()
        w.protocol("WM_DELETE_WINDOW")                       # la fermeture passe par notre fonction
        a.tk.call(w.protocol("WM_DELETE_WINDOW"))
        a.update()
        self.assertTrue(a.conf["sites_geom"].startswith("640x480"))
        a.show_sites()
        a.update()
        self.assertTrue(a.sites_win.geometry().startswith("640x480"))

    def test_hors_ecran_ignore(self):
        a = self.a
        a.conf["map_geom"] = "800x600+90000+90000"           # écran débranché depuis
        a.show_map()
        a.update()
        x = a.map_win.win.winfo_x()
        self.assertLess(x, 5000)
