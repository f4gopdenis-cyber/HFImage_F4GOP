"""1.52 (demande de RK1AT) : textes et logos ajoutés, déplacés, agrandis et tournés directement
sur l'image de l'onglet TX, à la souris ; clic droit : menu."""
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image, ImageDraw  # noqa: E402


class E:
    def __init__(self, x, y, state=0):
        self.x, self.y, self.x_root, self.y_root, self.state, self.delta = x, y, x, y, state, 120


class EditionDirecte(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        cls.appmod = app
        d = cls.d = tempfile.mkdtemp()
        cls.conf = os.path.join(d, "c.json")
        with open(cls.conf, "w") as f:
            json.dump({"callsign": "RK1AT", "licence_ok": "1.0", "lang": "fr", "hybrid": True}, f)
        cls.photo = os.path.join(d, "scene.jpg")
        Image.new("RGB", (1200, 800), (60, 110, 160)).save(cls.photo)
        cls.logo = os.path.join(d, "logo.png")
        lg = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
        ImageDraw.Draw(lg).ellipse([10, 10, 290, 290], fill=(220, 30, 30, 255))
        lg.save(cls.logo)

    def setUp(self):
        gc.collect()
        self.p = mock.patch.object(self.appmod, "CONF_PATH", self.conf)
        self.p.start()
        try:
            self.a = self.appmod.App()
        except Exception as e:
            self.p.stop()
            raise unittest.SkipTest(str(e))
        a = self.a
        a.geometry("1400x900+0+0")
        a.show_tab("tx")
        a.update()
        a.load_image(self.photo)
        a.prepare(sync=True)
        a.update()
        self.ed = a.tx_editor

    def tearDown(self):
        self.ed.cancel()
        self.a.destroy()
        self.a = None
        gc.collect()
        self.p.stop()

    def box(self):
        b = self.a.lb_cmp.image_box()
        self.assertIsNotNone(b)
        return b

    def test_ajouter_deplacer_agrandir_texte(self):
        a, ed = self.a, self.ed
        ed.add_text("73 de RK1AT")
        self.assertEqual(a.bubbles[-1]["text"], "73 de RK1AT")
        ox, oy, dw, dh = self.box()
        cx, cy = ox + dw // 2, oy + dh // 2
        self.assertEqual(ed.hit(E(cx, cy))[:2], ("b", 0))
        ed.press(E(cx, cy))
        ed.motion(E(ox + dw // 4, oy + dh // 4))
        ed.release(E(ox + dw // 4, oy + dh // 4))
        b = a.bubbles[0]
        self.assertAlmostEqual(b["cx"], 0.25, delta=0.03)
        self.assertAlmostEqual(b["cy"], 0.25, delta=0.03)
        ed.wheel(E(ox + dw // 4, oy + dh // 4), 1)
        self.assertGreater(b["k"], 1.0)
        a.prepare(sync=True)
        self.assertIsNotNone(a.tx)

    def test_logo_png_et_menu(self):
        a, ed = self.a, self.ed
        ed.add_pc_image(self.logo)
        p = a.pips[-1]
        self.assertTrue(p["logo"])                                   # PNG transparent : logo
        self.assertTrue(a.conf["pip_on"])
        ox, oy, dw, dh = self.box()
        cx, cy = ox + dw // 2, oy + dh // 2
        self.assertEqual(ed.hit(E(cx, cy))[:2], ("p", 0))
        ed.press(E(cx, cy))
        ed.motion(E(ox + 60, oy + 60))
        ed.release(E(ox + 60, oy + 60))
        self.assertLess(p["pos"][0], 0.2)
        import trafic
        old = p.get("scale") or trafic.PIP_SCALE[p.get("size", "moyenne")]
        ed.wheel(E(ox + 60, oy + 60), -1)
        self.assertLess(p["scale"], old)
        ed.wheel(E(ox + 60, oy + 60), 1, rotate=True)
        self.assertEqual(p["rot"], 3)
        ed.set_pip(shape="rond")
        self.assertEqual(p["shape"], "rond")
        ed.delete()
        self.assertEqual(a.pips, [])

    def click(self, x, y):
        a = self.a
        a._cmp_press = (x, y)
        self.ed.press(E(x, y))
        a._cmp_click(E(x, y))
        self.ed.release(E(x, y))

    def test_clics(self):
        # 1.53 : clic à côté des textes / logos : ouvre une image comme avant ; sur un texte : sélection
        a, ed = self.a, self.ed
        ed.add_text("73")
        ox, oy, dw, dh = self.box()
        with mock.patch.object(a, "open_image") as op:
            self.click(ox + dw // 2, oy + dh // 2)            # sur le texte : sélection
            op.assert_not_called()
            self.assertEqual(ed.sel, ("b", 0))
            self.click(ox + 5, oy + 5)                        # à côté, sélection active : désélection
            op.assert_not_called()
            self.assertIsNone(ed.sel)
            self.click(ox + 5, oy + 5)                        # à côté, rien de sélectionné : ouverture
            op.assert_called_once()

    def test_apercu_rapide(self):
        a = self.a
        self.ed.add_text("Hello")
        im = a._edit_preview((300, 200))
        self.assertEqual(im.size, (300, 200))


if __name__ == "__main__":
    unittest.main()
