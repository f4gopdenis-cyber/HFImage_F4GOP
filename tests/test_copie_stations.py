"""2.54 (VK6ATI) : copier le journal de l'onglet Stations (lignes choisies, tout, images reçues)."""
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Copie(unittest.TestCase):
    def test_copie(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        conf = os.path.join(tempfile.mkdtemp(), "c.json")
        with open(conf, "w") as f:
            json.dump({"callsign": "vk6ati", "licence_ok": "1.0", "lang": "en", "net_on": False}, f)
        gc.collect()
        with mock.patch.object(app, "CONF_PATH", conf), mock.patch.object(app, "DEFAULT_OUT", tempfile.mkdtemp()):
            try:
                a = app.App()
            except Exception as e:
                raise unittest.SkipTest(str(e))
            try:
                a.rig_freq = None
                a.station_event("VK6NJP", "Image reçue", "EasyPal", 12, "34567 octets")
                a.station_event("VK6NJP", "BSR EasyPal : 3 segments", "EasyPal", 10, "")
                a.station_event("VK6ABC", app.tr("Image reçue") + " (" + app.tr("hybride") + ")", "DATAC3-HYB", 5,
                                "1000 octets")
                t = a._tree_text("all")
                lines = t.splitlines()
                self.assertTrue(lines[0].startswith("HFImage — VK6ATI — "))
                self.assertIn("Callsign", lines[1])
                self.assertEqual(len(lines), 5)
                self.assertIn("VK6NJP\tImage received\tEasyPal\t+12 dB\t34567 bytes", lines[2])   # plus ancien d'abord
                self.assertIn("Image received (hybrid)", lines[4])
                im = a._tree_text("images").splitlines()
                self.assertEqual(len(im), 4)
                self.assertNotIn("BSR", "".join(im))
                self.assertEqual(a._tree_text("sel"), "")
                a.tree.selection_set(a.tree.get_children()[0])
                self.assertIn("VK6ABC", a._tree_text("sel"))
                a.tree.event_generate("<Control-c>")
            finally:
                a.destroy()
                import i18n
                i18n.set_lang("fr")


if __name__ == "__main__":
    unittest.main()
