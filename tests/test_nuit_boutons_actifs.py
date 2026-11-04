"""2.07 : en thème Nuit (style Classique), les boutons activés (fond jaune) gardaient un texte clair,
illisible — signalé par Gérard. Le texte passe en noir sur les fonds jaune/orange/rouge."""
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import theme  # noqa: E402


class Nuit(unittest.TestCase):
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
            json.dump({"callsign": "F4GOP", "licence_ok": "1.0", "lang": "fr", "look_style": "classique",
                       "theme": "Nuit"}, f)
        self.p = mock.patch.object(app, "CONF_PATH", self.conf)
        self.p.start()
        try:
            self.a = app.App()
        except Exception as e:
            self.p.stop()
            raise unittest.SkipTest(str(e))
        self.a.update()

    def tearDown(self):
        self.a.destroy()
        self.a = None
        gc.collect()
        self.p.stop()

    def ct(self, b):
        hx = lambda c: "#%02x%02x%02x" % tuple(v // 257 for v in self.a.winfo_rgb(c))
        return theme._contrast(hx(b.cget("fg")), hx(b.cget("bg")))

    def test_texte_lisible_sur_bouton_actif(self):
        a = self.a
        self.assertIsNone(a.look.palette())
        self.assertEqual(a.look.theme, "Nuit")
        b = next(iter(a.gbtn.values()))
        for st in ("on", "wait", "tx"):
            a._btn_color(b, st)
            self.assertGreaterEqual(self.ct(b), 4.5, st)
        a._btn_color(b, "off")                     # au repos : texte clair du thème Nuit
        self.assertTrue(a._is_light(b.cget("fg")))
        self.assertGreaterEqual(self.ct(b), 4.5)

    def test_reapplique_apres_changement_de_theme(self):
        a = self.a
        b = next(iter(a.gbtn.values()))
        a._btn_color(b, "on")
        a._apply_look(save=False)
        self.assertGreaterEqual(self.ct(b), 4.5)

    def test_classique_clair_inchange(self):
        a = self.a
        a.conf["theme"] = "Vert EasyPal"
        if hasattr(a, "v_theme"):
            a.v_theme.set(a.conf["theme"])
        a._apply_look(save=False)
        b = next(iter(a.gbtn.values()))
        a._btn_color(b, "on")
        self.assertFalse(a._is_light(b.cget("fg")))
