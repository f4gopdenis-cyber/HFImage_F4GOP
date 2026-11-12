"""2.35 : la coche des menus (Hybride → Mode hybride…) a la couleur du texte du menu (lisible sur fond sombre)."""
import gc
import json
import os
import sys
import tempfile
import tkinter as tk
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Coche(unittest.TestCase):
    def test_coche_lisible(self):
        gc.collect()
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        for look in ({"look_style": "moderne", "modern_theme": "Néon violet"}, {"look_style": "classique"}):
            d = tempfile.mkdtemp()
            conf = os.path.join(d, "c.json")
            with open(conf, "w") as f:
                json.dump(dict({"callsign": "F4GOP", "licence_ok": "1.0", "lang": "fr", "net_on": False}, **look), f)
            with mock.patch.object(app, "CONF_PATH", conf):
                try:
                    a = app.App()
                except Exception as e:
                    raise unittest.SkipTest(str(e))
                try:
                    a.update()
                    menus = []
                    stack = [a]
                    while stack:
                        w = stack.pop()
                        stack.extend(w.winfo_children())
                        if isinstance(w, tk.Menu):
                            menus.append(w)
                    self.assertTrue(menus)
                    for m in menus:
                        self.assertEqual(a.winfo_rgb(m.cget("selectcolor")), a.winfo_rgb(m.cget("foreground")),
                                         (look, str(m)))
                finally:
                    a._closing = True
                    a.destroy()
                    gc.collect()
