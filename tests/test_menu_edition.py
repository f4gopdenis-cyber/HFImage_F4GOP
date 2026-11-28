"""2.57 (VK6ATI) : clic droit Couper / Copier / Coller / Tout sélectionner dans les cases de texte."""
import gc
import json
import os
import sys
import tempfile
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class MenuEdition(unittest.TestCase):
    def test_menus(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        conf = os.path.join(tempfile.mkdtemp(), "c.json")
        with open(conf, "w") as f:
            json.dump({"callsign": "VK6ATI", "licence_ok": "1.0", "lang": "en", "net_on": False}, f)
        gc.collect()
        with mock.patch.object(app, "CONF_PATH", conf):
            try:
                a = app.App()
            except Exception as e:
                raise unittest.SkipTest(str(e))
            try:
                posted = []

                def fake_popup(menu, x, y):
                    posted.append([menu.entrycget(i, "label") for i in range(menu.index("end") + 1)
                                   if menu.type(i) == "command"])
                    posted.append(menu)

                with mock.patch.object(tk.Menu, "tk_popup", fake_popup):
                    # case d'envoi de texte : menu complet ; Coller colle le presse-papiers
                    a.win_txt.deiconify()
                    a.update()
                    t = a.txt_msg
                    a.clipboard_clear()
                    a.clipboard_append("VK6WK incomplete (5/174 segments)")
                    r = a._edit_menu(SimpleNamespace(widget=t, x_root=10, y_root=10))
                    self.assertEqual(r, "break")
                    self.assertEqual(posted[0], ["Cut", "Copy", "Paste", "Select all"])
                    m = posted[1]
                    m.invoke(2)
                    a.update()
                    self.assertIn("5/174 segments", t.get("1.0", "end-1c"))
                    posted.clear()
                    # cadre Messages (lecture seule) : Copier et Tout sélectionner
                    a._show_message("VK6WK", "hello")
                    a._edit_menu(SimpleNamespace(widget=a.msgbox, x_root=10, y_root=10))
                    self.assertEqual(posted[0], ["Copy", "Select all"])
                    posted.clear()
                    # une case Entry
                    e = tk.Entry(a)
                    e.insert(0, "F4GOP")
                    e.pack()
                    a.update()
                    a._edit_menu(SimpleNamespace(widget=e, x_root=10, y_root=10))
                    self.assertEqual(posted[0], ["Cut", "Copy", "Paste", "Select all"])
                    posted[1].invoke(4)
                    self.assertTrue(e.selection_present())
                self.assertIn(("Text", "<Button-3>"),
                              [("Text", b) for b in a.bind_class("Text") if b == "<Button-3>"])
            finally:
                a.destroy()
                import i18n
                i18n.set_lang("fr")


if __name__ == "__main__":
    unittest.main()
