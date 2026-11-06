"""2.12 (demandes de VK3DNH) : sans CAT, la fréquence choisie dans le menu « Fréquence » est publiée
dans la liste des stations ; notre indicatif est en tête de la liste dès qu'on est connecté."""
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class SansCat(unittest.TestCase):
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
            json.dump({"callsign": "VK3DNH", "licence_ok": "1.0", "lang": "fr", "net_on": False}, f)
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
        self.a.net = None
        self.a.destroy()
        self.a = None
        gc.collect()
        self.p.stop()

    def test_frequence_choisie_sans_cat(self):
        a = self.a
        self.assertEqual(self.app.radio.rig_entry(a.radio_cfg["rig"])["kind"], "none")
        with mock.patch.object(self.app.messagebox, "showinfo") as info:
            a._qsy(7_058_000, "LSB")
        info.assert_not_called()                           # plus de « Pas de liaison CAT »
        self.assertEqual(a.rig_freq, 7_058_000)
        self.assertIn("7.058", a.lb_heard.cget("text"))
        self.assertNotIn("qsy_freq", json.dumps(a.conf))   # rien d'enregistré

    def test_notre_indicatif_en_tete(self):
        a = self.a
        a.net = mock.MagicMock(call="VK3DNH")
        a.net_ok = True
        a.online = {"F4GOP": {"call": "F4GOP", "freq": 7_058_000, "seen": 9e12}}
        a._heard_refresh()
        self.assertEqual(a._heard_names[0], "VK3DNH")
        self.assertIn("VK3DNH", a.lst_heard.get(0))
        self.assertTrue(a.lb_heard.cget("text").startswith(self.app.tr("Stations (1)")))
        a.net_ok = False                                   # pas connecté : pas de ligne pour nous
        a._heard_refresh()
        self.assertNotIn("VK3DNH", a._heard_names)
