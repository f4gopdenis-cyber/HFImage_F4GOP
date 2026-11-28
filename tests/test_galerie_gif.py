"""2.56 (VK6NJP) : les GIF animés bougent dans les vignettes de la galerie."""
import os
import shutil
import sys
import tempfile
import time
import tkinter as tk
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import gallery  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


class _App:
    def gallery_show(self, e):
        pass

    def gallery_full(self, e):
        pass


class GalerieGif(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            raise unittest.SkipTest(str(e))
        self.root.geometry("800x600")

    def tearDown(self):
        self.root.destroy()

    def test_vignette_animee(self):
        from PIL import Image
        d = tempfile.mkdtemp()
        gif = os.path.join(d, "anim.gif")
        shutil.copy(os.path.join(HERE, "..", "exemples", "exemple_anime.gif"), gif)
        jpg = os.path.join(d, "fixe.jpg")
        Image.new("RGB", (320, 240), "red").save(jpg)
        store = gallery.GalleryStore(d)
        store.add({"t": time.time() - 5, "dir": "rx", "call": "VK6NJP", "mode": "DATAC3-HYB", "file": gif,
                   "png": None, "size": 1})
        store.add({"t": time.time(), "dir": "rx", "call": "VK6ATI", "mode": "DATAC1", "file": jpg, "png": jpg,
                   "size": 1})
        v = gallery.GalleryView(self.root, _App(), lambda s: s)
        v.pack(fill="both", expand=True)
        v.set_store(store)
        t0 = time.time()
        while time.time() - t0 < 2.0:
            self.root.update()
            time.sleep(0.02)
        self.assertEqual(len(v._anims), 1)                 # seul le GIF est animé
        a = v._anims[0]
        self.assertGreater(len(a["frames"]), 1)
        k0 = a["k"]
        t0 = time.time()
        while time.time() - t0 < 1.5 and a["k"] == k0:
            self.root.update()
            time.sleep(0.02)
        self.assertNotEqual(a["k"], k0)                     # l'image change
        self.assertTrue(any(v.cv.itemcget(i, "text") == "GIF" for i in v.cv.find_all()
                            if v.cv.type(i) == "text"))


if __name__ == "__main__":
    unittest.main()
