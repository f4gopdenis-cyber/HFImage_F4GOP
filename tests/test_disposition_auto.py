"""1.97 (signalé par F1ABL) : la disposition des fenêtres n'était enregistrée qu'à la fermeture par la
croix ; un PC éteint avec HFImage ouvert la perdait. Elle est maintenant enregistrée dès qu'un séparateur
est lâché, avec « Enregistrer les réglages », et quand Windows s'éteint."""
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Disposition(unittest.TestCase):
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
            json.dump({"callsign": "F1ABL", "licence_ok": "1.0", "lang": "fr",
                       "layout": {"left": 333}}, f)
        self.p = mock.patch.object(app, "CONF_PATH", self.conf)
        self.p.start()
        try:
            self.a = app.App()
        except Exception as e:
            self.p.stop()
            raise unittest.SkipTest(str(e))
        self.a.geometry("1320x880")
        self.a.update()

    def tearDown(self):
        self.a._closing = True
        self.a.destroy()
        self.a = None
        gc.collect()
        self.p.stop()

    def saved(self):
        with open(self.conf, encoding="utf-8") as f:
            return json.load(f)

    def test_pas_d_ecrasement_au_demarrage(self):
        a = self.a
        a._layout_ready = False
        a._save_layout()                                     # avant la remise en place des tailles
        self.assertEqual(self.saved()["layout"], {"left": 333})

    def test_separateur_lache_enregistre(self):
        a = self.a
        a._layout_autosave()
        p = a.panes["left"]
        a.update()
        n = a._pane_len(p)
        p.sash_place(0, 0, n - 250)                          # stations : 250 px, waterfall agrandi
        a.update()
        p.event_generate("<ButtonRelease-1>", x=5, y=5)
        a._layout_save_now()
        lay = self.saved()["layout"]
        self.assertAlmostEqual(lay["left"], 250, delta=8)

    def test_bouton_enregistrer_et_arret_windows(self):
        a = self.a
        a._layout_autosave()
        p = a.panes["left"]
        a.update()
        p.sash_place(0, 0, a._pane_len(p) - 222)
        a.update()
        a.save_conf(quiet=True)
        self.assertAlmostEqual(self.saved()["layout"]["left"], 222, delta=8)
        self.assertTrue(a.protocol("WM_SAVE_YOURSELF"))     # Windows qui s'éteint : enregistrement


if __name__ == "__main__":
    unittest.main()
