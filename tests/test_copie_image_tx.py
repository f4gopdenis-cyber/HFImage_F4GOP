"""2.34 (VK6ATI) : clic droit sur l'image TX -> « Copier l'image » (pour la coller dans Teams)."""
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image  # noqa: E402


class CopieTX(unittest.TestCase):
    def test_copie(self):
        gc.collect()
        try:
            import app
            import clip
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        d = tempfile.mkdtemp()
        conf = os.path.join(d, "c.json")
        with open(conf, "w") as f:
            json.dump({"callsign": "VK6ATI", "licence_ok": "1.0", "lang": "en", "net_on": False}, f)
        with mock.patch.object(app, "CONF_PATH", conf):
            try:
                a = app.App()
            except Exception as e:
                raise unittest.SkipTest(str(e))
            try:
                a.update()
                got = []
                with mock.patch.object(clip, "copy_image", lambda im: got.append(im.size)), \
                        mock.patch.object(app.messagebox, "showinfo"):
                    self.assertFalse(a.copy_tx_image())                 # pas encore d'image
                    a.src_img = Image.new("RGB", (640, 480), "blue")
                    self.assertTrue(a.copy_tx_image())
                self.assertEqual(len(got), 1)
                # l'entrée est bien dans le menu du clic droit
                labels = []
                import tkinter as tk
                with mock.patch.object(tk.Menu, "tk_popup", lambda self, x, y: labels.extend(
                        self.entrycget(i, "label") for i in range(self.index("end") + 1)
                        if self.type(i) == "command")):
                    a.lb_cmp.menu_cb(mock.Mock(x=5, y=5, x_root=5, y_root=5))
                self.assertTrue(any("Copy" in l or "Copier" in l for l in labels), labels)
            finally:
                a._closing = True
                a.destroy()
