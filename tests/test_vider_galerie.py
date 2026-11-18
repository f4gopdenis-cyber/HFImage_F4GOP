"""2.43 (demande de VK6ATI) : retirer plusieurs images de la galerie, ou la vider d'un coup
(les fichiers restent dans le dossier)."""
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image  # noqa: E402


class FakeApp:
    def gallery_show(self, e):
        pass

    def gallery_full(self, e):
        pass


class ViderGalerie(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            import gallery
            self.root = tk.Tk()
        except Exception as e:
            raise unittest.SkipTest(str(e))
        self.gallery = gallery
        self.d = tempfile.mkdtemp()
        self.files = []
        now = time.time()
        st = gallery.GalleryStore(self.d)
        st.items = []
        for i in range(6):
            p = os.path.join(self.d, f"img{i}.png")
            Image.new("RGB", (40, 30), (i * 40, 80, 120)).save(p)
            self.files.append(p)
            st.add({"file": p, "png": p, "dir": "rx" if i < 4 else "tx", "t": now - i, "call": "VK6ATI"})
        self.st = st
        self.g = gallery.GalleryView(self.root, FakeApp(), lambda t: t)
        self.g.pack(fill="both", expand=True)
        self.root.geometry("800x500")
        self.g.set_store(st)
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def test_vider_les_recues(self):
        g = self.g
        self.assertEqual(len(g.shown), 4)
        with mock.patch("tkinter.messagebox.askyesno", return_value=True) as ask:
            self.assertEqual(g._clear_dir(), 4)
            self.assertIn("4", ask.call_args[0][1])                     # « Retirer les 4 images… ? »
        self.assertEqual(g.shown, [])
        self.assertEqual(self.st.count("rx"), 0)
        self.assertEqual(self.st.count("tx"), 2)                        # les envoyées ne bougent pas
        self.assertTrue(all(os.path.exists(p) for p in self.files))     # fichiers gardés
        st2 = self.gallery.GalleryStore(self.d)                         # retenu après redémarrage
        self.assertEqual(st2.count("rx"), 0)

    def test_non_ne_retire_rien(self):
        with mock.patch("tkinter.messagebox.askyesno", return_value=False):
            self.assertEqual(self.g._clear_dir(), 0)
        self.assertEqual(self.st.count("rx"), 4)

    def test_retirer_les_images_choisies(self):
        g = self.g
        g._toggle(g.shown[0])
        g._toggle(g.shown[2])
        self.assertEqual(g._remove_selection(), 2)
        self.assertEqual(self.st.count("rx"), 2)
        self.assertEqual(g.sel, [])

    def test_menus(self):
        g = self.g
        g.select_all()

        class Ev:
            x_root = y_root = 10
        with mock.patch.object(g.menu, "tk_popup"):
            g._popup(Ev(), g.shown[0])
        labels = [g.menu.entrycget(i, "label") for i in range(g.menu.index("end") + 1)
                  if g.menu.type(i) != "separator"]
        self.assertIn("Retirer les 4 images choisies de la galerie", labels)
        self.assertIn("Vider la galerie (Dernières reçues)…", labels)
        g.clear_selection()
        g.set_dir("tx")
        with mock.patch.object(g.menu_bg, "tk_popup"), mock.patch.object(g, "_on_image", return_value=False):
            g._popup_bg(Ev())
        labels = [g.menu_bg.entrycget(i, "label") for i in range(g.menu_bg.index("end") + 1)
                  if g.menu_bg.type(i) != "separator"]
        self.assertIn("Vider la galerie (Dernières envoyées)…", labels)
        self.assertNotIn("Retirer les 2 images choisies de la galerie", labels)


if __name__ == "__main__":
    unittest.main()
