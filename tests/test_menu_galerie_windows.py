"""2.45 (signalé par F4GOP) : sous Windows, après le menu d'une image, le menu du fond s'ouvrait aussi
et effaçait le choix fait (« Renvoyer cette image (onglet TX) » ne faisait plus rien)."""
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image  # noqa: E402


class FakeApp:
    def __init__(self):
        self.calls = []

    def gallery_show(self, e):
        self.calls.append("show")

    def gallery_full(self, e):
        self.calls.append("full")

    def gallery_copy(self, e):
        self.calls.append("copy")

    def gallery_to_tx(self, e):
        self.calls.append("to_tx")

    def set_pip(self, e, add=False):
        self.calls.append("pip")

    def show_map(self, call):
        self.calls.append("map")

    def gallery_folder(self, e):
        self.calls.append("folder")


class MenuWindows(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            import gallery
            self.root = tk.Tk()
        except Exception as e:
            raise unittest.SkipTest(str(e))
        self.tk = tk
        d = tempfile.mkdtemp()
        st = gallery.GalleryStore(d)
        st.items = []
        for i in range(3):
            p = os.path.join(d, f"i{i}.png")
            Image.new("RGB", (40, 30), (90, 90, 90)).save(p)
            st.add({"file": p, "png": p, "dir": "rx", "t": time.time() - i, "call": "F1UGC"})
        self.app = FakeApp()
        self.g = gallery.GalleryView(self.root, self.app, lambda t: t)
        self.g.pack(fill="both", expand=True)
        self.root.geometry("700x400+0+0")
        self.g.set_store(st)
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def test_renvoyer_en_tx(self):
        g, tk = self.g, self.tk
        x0, y0, x1, y1 = g.cv.bbox("t0")
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        posted = []
        orig = tk.Menu.tk_popup

        def windows_popup(menu, x, y, entry=""):
            """Comme Windows : le menu bloque ; la souris quitte l'image ; le choix est exécuté ensuite."""
            posted.append(menu)
            if menu is g.menu and len(posted) == 1:
                labels = [menu.entrycget(i, "label") if menu.type(i) != "separator" else ""
                          for i in range(menu.index("end") + 1)]
                k = labels.index("Renvoyer cette image (onglet TX)")
                g.cv.event_generate("<Motion>", x=690, y=390)          # souris sur le menu, plus sur l'image
                self.root.after_idle(lambda: menu.invoke(k))
        g.cv.event_generate("<Motion>", x=cx, y=cy)
        self.root.update()
        with mock.patch.object(tk.Menu, "tk_popup", windows_popup), \
                mock.patch("tkinter.messagebox.askyesno", return_value=False):
            g.cv.event_generate("<Button-3>", x=cx, y=cy)
            for _ in range(20):
                self.root.update()
                time.sleep(0.01)
        tk.Menu.tk_popup = orig
        self.assertEqual(self.app.calls, ["to_tx"])                   # le choix est bien fait
        self.assertEqual(len(posted), 1)                               # pas de menu du fond en plus

    def test_fond_toujours_possible(self):
        g, tk = self.g, self.tk
        posted = []
        with mock.patch.object(tk.Menu, "tk_popup", lambda m, *a, **k: posted.append(m)):
            g.cv.event_generate("<Motion>", x=690, y=390)
            g.cv.event_generate("<Button-3>", x=690, y=390)
            self.root.update()
        self.assertEqual(posted, [g.menu_bg])


if __name__ == "__main__":
    unittest.main()
