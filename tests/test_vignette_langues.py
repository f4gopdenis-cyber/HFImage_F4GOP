"""2.32 (BH2RMX) : la vignette de la dernière image reçue s'affiche dans toutes les langues,
à la même taille (avant : rien en chinois ni en allemand, trop grande en russe)."""
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image  # noqa: E402


class Vignette(unittest.TestCase):
    def _panel(self, lang):
        gc.collect()
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        d = tempfile.mkdtemp()
        conf = os.path.join(d, "c.json")
        with open(conf, "w") as f:
            json.dump({"callsign": "BH2RMX", "licence_ok": "1.0", "lang": lang, "net_on": False}, f)
        with mock.patch.object(app, "CONF_PATH", conf):
            try:
                a = app.App()
            except Exception as e:
                raise unittest.SkipTest(str(e))
            try:
                a.update()
                a.panel.set_thumb(Image.new("RGB", (320, 240), "orange"), "BH2RMX\n9059 km")
                a.update()
                img = [i for i in a.panel.thumb.find_all() if a.panel.thumb.type(i) == "image"]
                bb = a.panel.thumb.bbox(img[0]) if img else None
                right = a.panel.thumb.winfo_rootx() + a.panel.thumb.winfo_width() - a.panel.winfo_rootx()
                return bb, right, a.panel.winfo_width()
            finally:
                a._closing = True
                a.destroy()

    def test_toutes_les_langues(self):
        for lang in ("fr", "en", "de", "es", "it", "ru", "zh"):
            bb, right, pw = self._panel(lang)
            self.assertIsNotNone(bb, lang)
            self.assertLessEqual(bb[2] - bb[0], 80, lang)            # pas plus grande en russe
            self.assertGreaterEqual(bb[2] - bb[0], 40, lang)
            self.assertLessEqual(right, pw, lang)                     # pas coupée au bord du panneau
