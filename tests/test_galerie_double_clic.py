"""2.39 (signalé par BH2RMX) : dans la galerie, double-clic = plein format (le clic simple passait
tout de suite à l'onglet RX et le double-clic n'arrivait jamais)."""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class FakeApp:
    def __init__(self):
        self.calls = []

    def gallery_show(self, e):
        self.calls.append(("show", e["file"]))

    def gallery_full(self, e):
        self.calls.append(("full", e["file"]))


class DoubleClic(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            import gallery
            self.root = tk.Tk()
        except Exception as e:
            raise unittest.SkipTest(str(e))
        self.app = FakeApp()
        self.g = gallery.GalleryView(self.root, self.app, lambda t: t)
        self.e = {"file": "a.avif", "dir": "rx"}

    def tearDown(self):
        self.root.destroy()

    def wait(self, ms):
        end = time.time() + ms / 1000
        while time.time() < end:
            self.root.update()
            time.sleep(0.01)

    def test_clic_simple_affiche(self):
        self.g._click(self.e)
        self.assertEqual(self.app.calls, [])                       # pas tout de suite
        self.wait(self.g.DCLICK_MS + 200)
        self.assertEqual(self.app.calls, [("show", "a.avif")])

    def test_double_clic_plein_format(self):
        self.g._click(self.e)                                      # 1er clic (Tk : Button-1)
        self.wait(50)
        self.g._full(self.e)                                       # 2e clic (Tk : Double-Button-1)
        self.wait(self.g.DCLICK_MS + 200)
        self.assertEqual(self.app.calls, [("full", "a.avif")])     # pas de passage à l'onglet RX

    def test_vrais_clics_de_souris(self):
        """Clics envoyés à la fenêtre, comme avec la souris, sur une vignette liée comme dans la galerie."""
        cv, g, e = self.g.cv, self.g, self.e
        g.pack(fill="both", expand=True)
        self.root.geometry("600x500+0+0")
        cv.create_rectangle(10, 10, 100, 100, fill="red", tags=("t0",))
        cv.tag_bind("t0", "<Button-1>", lambda ev: g._click(e))
        cv.tag_bind("t0", "<Double-Button-1>", lambda ev: g._full(e))
        self.root.update()
        cv.event_generate("<Motion>", x=50, y=50)          # la souris sur la vignette (« current »)
        self.root.update()
        for _ in range(2):
            cv.event_generate("<ButtonPress-1>", x=50, y=50)
            cv.event_generate("<ButtonRelease-1>", x=50, y=50)
        self.wait(g.DCLICK_MS + 200)
        self.assertEqual(self.app.calls, [("full", "a.avif")])

if __name__ == "__main__":
    unittest.main()
