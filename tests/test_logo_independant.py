"""2.02 (demande de Gérard) : le logo (et les images du PC) est indépendant des images des correspondants :
case « Logo » à part dans l'onglet TX, et « Répondre avec cette image » ne retire plus le logo."""
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from PIL import Image  # noqa: E402


class Logo(unittest.TestCase):
    def start(self, saved):
        gc.collect()
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.app = app
        self.d = tempfile.mkdtemp()
        conf = os.path.join(self.d, "c.json")
        with open(conf, "w") as f:
            json.dump(dict({"callsign": "F4GOP", "licence_ok": "1.0", "lang": "fr"}, **saved), f)
        self.p = mock.patch.object(app, "CONF_PATH", conf)
        self.p.start()
        self.m = mock.patch.object(app.messagebox, "showinfo", lambda *a, **k: None)
        self.m.start()
        try:
            self.a = app.App()
        except Exception as e:
            self.p.stop()
            raise unittest.SkipTest(str(e))
        self.a.update()
        base = os.path.join(self.d, "base.jpg")
        Image.new("RGB", (640, 480), (40, 80, 160)).save(base)
        self.a.load_image(base)
        self.logo = os.path.join(self.d, "logo.png")
        Image.new("RGBA", (100, 100), (255, 0, 0, 255)).save(self.logo)
        self.recue = os.path.join(self.d, "recue.jpg")
        Image.new("RGB", (320, 240), (0, 200, 0)).save(self.recue)

    def tearDown(self):
        a = getattr(self, "a", None)
        if a is not None:
            a._closing = True
            a.destroy()
            self.a = None
            gc.collect()
            self.m.stop()
            self.p.stop()

    def add_logo(self):
        a = self.a
        a.pips.append(dict(a._pip_new({"path": self.logo, "call": "", "snr": None, "local": True}),
                           cap=None, logo=True, opa=1.0, pos=[0.9, 0.9]))
        a.conf["logo_on"] = True

    def px(self, xy):
        return self.a._pip_source().convert("RGB").getpixel(xy)

    def test_repondre_garde_le_logo(self):
        self.start({})
        a = self.a
        self.add_logo()
        a.set_pip({"file": self.recue, "call": "F1ABL", "snr": 5})          # « Répondre avec cette image »
        self.assertEqual(len(a.pips), 2)
        self.assertTrue(any(a._pip_mine(p) for p in a.pips))
        self.assertEqual(a.pips[0]["call"], "F1ABL")
        a.set_pip({"file": self.recue, "call": "F5TGB", "snr": 3})          # autre réponse : logo toujours là
        self.assertEqual([p.get("call") for p in a.pips], ["F5TGB", ""])

    def test_cases_independantes(self):
        self.start({})
        a = self.a
        self.add_logo()
        a.set_pip({"file": self.recue, "call": "F1ABL", "snr": 5})
        logo_xy = (int(640 * 0.9) - 10, int(480 * 0.9) - 10)
        self.assertEqual(len(a._pips_shown()), 2)
        a.conf["pip_on"] = False                                           # correspondants masqués
        self.assertEqual([p.get("call") for p in a._pips_shown()], [""])
        fond = self.a.src_img.convert("RGB").getpixel(logo_xy)
        self.assertNotEqual(self.px(logo_xy), fond)                         # logo toujours posé
        a.conf.update(pip_on=True, logo_on=False)                          # logo masqué, pas perdu
        self.assertEqual([p.get("call") for p in a._pips_shown()], ["F1ABL"])
        self.assertEqual(self.px(logo_xy), fond)
        self.assertEqual(len(a.pips), 2)

    def test_reprise_des_anciens_reglages(self):
        self.start({"pip_on": False})                                      # avant 2.02 : logo éteint avec la case
        self.assertFalse(self.a.conf["logo_on"])
        self.assertFalse(self.a.v_logoon.get())


if __name__ == "__main__":
    unittest.main()
