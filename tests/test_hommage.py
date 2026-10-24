"""1.33 : drapeau australien et hommage à VK4AES dans la barre du bas."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import flag  # noqa: E402
import i18n  # noqa: E402


class Hommage(unittest.TestCase):
    def test_drapeau(self):
        im = flag.australia(24, 12)
        self.assertEqual(im.size, (24, 12))
        big = flag.australia(200, 100)
        self.assertGreater(big.getpixel((150, 85))[2], 80)          # fond bleu
        self.assertGreater(big.getpixel((50, 25))[0], 150)          # croix rouge au centre de l'Union Jack

    def test_traduction(self):
        try:
            i18n.set_lang("en")
            self.assertEqual(i18n.tr("En hommage à VK4AES"), "In memory of VK4AES")
        finally:
            i18n.set_lang("fr")


    def test_logo_dans_la_fenetre(self):
        # 1.47 : le logo d'hommage dessiné par Denis F4GOP s'affiche dans la fenêtre de dédicace
        import gc
        here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
        self.assertTrue(os.path.exists(os.path.join(here, "hommage_vk4aes.jpg")))
        with open(os.path.join(here, "HFImage.spec"), encoding="utf-8") as f:
            self.assertIn("hommage_vk4aes.jpg", f.read())              # embarqué dans l'exe
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        import tkinter as tk
        gc.collect()
        try:
            root = tk.Tk()
        except tk.TclError as e:
            raise unittest.SkipTest(str(e))
        try:
            root._tribute_win = None
            root.TRIBUTE_LOGO = app.App.TRIBUTE_LOGO
            from unittest import mock

            def no_box(*a, **k):                          # jamais de fenêtre bloquante en test
                raise AssertionError("logo introuvable : message affiché à la place")
            with mock.patch.object(app.messagebox, "showinfo", no_box):
                w = app.App.show_tribute(root)
            root.update()
            imgs = [c for c in w.winfo_children() if isinstance(c, tk.Label) and c.cget("image")]
            self.assertEqual(len(imgs), 1)
            self.assertGreater(imgs[0].image.width(), 300)
        finally:
            root.destroy()
            gc.collect()


if __name__ == "__main__":
    unittest.main()
