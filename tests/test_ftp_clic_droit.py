"""2.36 (F6BAZ) : clic droit sur l'image RX -> « Envoyer sur le site web (FTP) », comme EasyPal."""
import gc
import json
import os
import sys
import tempfile
import tkinter as tk
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image  # noqa: E402


class FtpClic(unittest.TestCase):
    def setUp(self):
        gc.collect()
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.app = app
        self.d = tempfile.mkdtemp()
        conf = os.path.join(self.d, "c.json")
        with open(conf, "w") as f:
            json.dump({"callsign": "F6BAZ", "licence_ok": "1.0", "lang": "fr", "net_on": False}, f)
        self.p = mock.patch.object(app, "CONF_PATH", conf)
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
        gc.collect()
        self.p.stop()

    def _menu(self):
        labels = {}
        with mock.patch.object(tk.Menu, "tk_popup", lambda m, x, y: labels.update(
                {m.entrycget(i, "label"): m.entrycget(i, "state") for i in range(m.index("end") + 1)
                 if m.type(i) == "command"})):
            self.a._rx_menu(mock.Mock(x_root=5, y_root=5))
        return labels

    def test_envoi(self):
        a = self.a
        self.assertEqual(self._menu().get("Envoyer sur le site web (FTP)"), "disabled")   # pas d'image
        png = os.path.join(self.d, "rx.png")
        Image.new("RGB", (320, 240), "green").save(png)
        a.gallery_show({"file": png, "png": png, "call": "G7VQV", "mode": "DATAC3", "dir": "rx"})
        a.update()
        self.assertEqual(self._menu().get("Envoyer sur le site web (FTP)"), "normal")
        sent = []
        with mock.patch.object(a.web, "add", lambda cfg, kind, path, cap: sent.append((kind, path, cap))), \
                mock.patch.object(self.app.messagebox, "showinfo") as info:
            with mock.patch.object(a, "_web_cfg", return_value={"host": ""}):
                self.assertFalse(a.web_upload_shown())                    # serveur non réglé : message
                info.assert_called_once()
            with mock.patch.object(a, "_web_cfg", return_value={"host": "ftp.example.org"}):
                self.assertTrue(a.web_upload_shown())
        self.assertEqual(sent[0][0], "rx")
        self.assertEqual(sent[0][1], png)
        self.assertTrue(sent[0][2].startswith("G7VQV"))
