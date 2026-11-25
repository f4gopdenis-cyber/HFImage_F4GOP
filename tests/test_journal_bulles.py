"""2.51 : copier le texte du journal (VK6ATI) ; garder les bulles d'une image à l'autre (VK6NJP)."""
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Essai(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        cls.app_mod = app
        conf = os.path.join(tempfile.mkdtemp(), "c.json")
        with open(conf, "w") as f:
            json.dump({"callsign": "VK6ATI", "licence_ok": "1.0", "lang": "en", "net_on": False}, f)
        gc.collect()
        cls.p = mock.patch.object(app, "CONF_PATH", conf)
        cls.p.start()
        try:
            cls.a = app.App()
        except Exception as e:
            cls.p.stop()
            raise unittest.SkipTest(str(e))

    @classmethod
    def tearDownClass(cls):
        cls.a.destroy()
        cls.p.stop()
        import i18n
        i18n.set_lang("fr")

    def test_copier_journal(self):
        a = self.a
        a.log("Image EasyPal de VK6NJP incomplète (40/52 segments) : cliquez sur BSR pour demander les segments manquants.")
        w = a.logbox
        self.assertEqual(str(w.cget("state")), "disabled")
        i = w.search("40/52", "1.0")
        w.tag_add("sel", i, f"{i} lineend")
        w._copy_sel()
        self.assertTrue(a.clipboard_get().startswith("40/52 segments"))
        self.assertIn("40/52 segments", a.clipboard_get())
        w._select_all()
        w._copy_sel()
        self.assertIn("VK6NJP", a.clipboard_get())
        self.assertIn("missing segments", a.clipboard_get())      # journal en anglais

    def test_garder_bulles(self):
        from PIL import Image
        a = self.a
        p = os.path.join(tempfile.mkdtemp(), "i.png")
        Image.new("RGB", (320, 240), "blue").save(p)
        a.bubbles = [{"text": "Net starts 08:00 UTC", "cx": 0.5, "cy": 0.2}]
        a.v_keep_bubbles.set(False)
        with mock.patch.object(a, "prepare"):
            a.load_image(p)
        self.assertEqual(a.bubbles, [])
        a.bubbles = [{"text": "Net starts 08:00 UTC", "cx": 0.5, "cy": 0.2}]
        a.v_keep_bubbles.set(True)
        with mock.patch.object(a, "prepare"):
            a.load_image(p)
        self.assertEqual(len(a.bubbles), 1)
        a.v_keep_bubbles.set(False)


if __name__ == "__main__":
    unittest.main()
