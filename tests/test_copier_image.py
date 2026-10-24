"""1.38 (demande de VK6ATI) : copier une image de la galerie / de l'onglet RX dans le
presse-papiers, pour la coller dans MS Teams, un e-mail…"""
import gc
import os
import stat
import struct
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image  # noqa: E402
import clip  # noqa: E402
import i18n  # noqa: E402


class Formats(unittest.TestCase):
    def test_dib(self):
        im = Image.new("RGB", (30, 20), (200, 10, 10))
        d = clip.dib_bytes(im)
        size, w, h = struct.unpack("<IiI", d[:12])
        self.assertEqual((size, w, h), (40, 30, 20))           # BITMAPINFOHEADER, sans en-tête de fichier
        self.assertNotEqual(d[:2], b"BM")

    def test_transparence(self):
        im = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        self.assertTrue(clip.png_bytes(im).startswith(b"\x89PNG"))
        self.assertEqual(struct.unpack("<H", clip.dib_bytes(im)[14:16])[0], 24)   # fond blanc, 24 bits
        self.assertTrue(clip.png_bytes(Image.new("P", (5, 5))).startswith(b"\x89PNG"))

    def test_gif_anime_premiere_image(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "a.gif")
        fr = [Image.new("RGB", (16, 16), c) for c in ((255, 0, 0), (0, 0, 255))]
        fr[0].save(p, save_all=True, append_images=fr[1:], duration=100, loop=0)
        im = clip.load(p)
        self.assertGreater(im.convert("RGB").getpixel((5, 5))[0], 200)


@unittest.skipIf(sys.platform.startswith("win"), "xclip : Linux")
class Linux(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.out = os.path.join(self.d, "clip.bin")
        x = os.path.join(self.d, "xclip")
        with open(x, "w") as f:
            f.write(f"#!/bin/sh\necho \"$@\" > {self.out}.args\ncat > {self.out}\n")
        os.chmod(x, os.stat(x).st_mode | stat.S_IEXEC)

    def test_xclip(self):
        env = dict(os.environ, PATH=self.d + os.pathsep + "/usr/bin:/bin", WAYLAND_DISPLAY="")
        with mock.patch.dict(os.environ, env, clear=True):
            clip.copy_image(Image.new("RGB", (8, 8), (1, 2, 3)))
        with open(self.out, "rb") as f:
            self.assertTrue(f.read().startswith(b"\x89PNG"))
        with open(self.out + ".args") as f:
            self.assertIn("image/png", f.read())

    def test_sans_xclip(self):
        with mock.patch.dict(os.environ, {"PATH": tempfile.mkdtemp()}, clear=True):
            with self.assertRaises(clip.ClipError) as c:
                clip.copy_image(Image.new("RGB", (8, 8)))
        self.assertIn("sudo apt install xclip", str(c.exception))
        try:
            i18n.set_lang("en")
            self.assertIn("install xclip", i18n.tr(str(c.exception)))
        finally:
            i18n.set_lang("fr")


@unittest.skipUnless(sys.platform.startswith("win"), "presse-papiers Windows")
class Windows(unittest.TestCase):
    def test_copie_relue(self):
        import ctypes
        from ctypes import wintypes
        import time
        clip.copy_image(Image.new("RGB", (33, 21), (5, 6, 7)))
        u = ctypes.WinDLL("user32")
        k = ctypes.WinDLL("kernel32")
        u.GetClipboardData.restype = wintypes.HANDLE
        u.GetClipboardData.argtypes = [wintypes.UINT]
        u.RegisterClipboardFormatW.restype = wintypes.UINT
        u.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
        k.GlobalLock.restype = ctypes.c_void_p
        k.GlobalLock.argtypes = [wintypes.HGLOBAL]
        k.GlobalSize.restype = ctypes.c_size_t
        k.GlobalSize.argtypes = [wintypes.HGLOBAL]
        k.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        for _ in range(20):
            if u.OpenClipboard(None):
                break
            time.sleep(0.05)
        try:
            self.assertTrue(u.IsClipboardFormatAvailable(8))                     # CF_DIB
            h = u.GetClipboardData(u.RegisterClipboardFormatW("PNG"))
            self.assertTrue(h)
            ptr = k.GlobalLock(h)
            data = ctypes.string_at(ptr, k.GlobalSize(h))
            k.GlobalUnlock(h)
        finally:
            u.CloseClipboard()
        import io
        self.assertEqual(Image.open(io.BytesIO(data)).size, (33, 21))


class Appli(unittest.TestCase):
    def setUp(self):
        gc.collect()

    def tearDown(self):
        gc.collect()

    def _fake(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        f = mock.Mock()
        f.copy_image = lambda src: app.App.copy_image(f, src)
        f._gallery_src = lambda e: app.App._gallery_src(f, e)
        return app, f

    def test_galerie(self):
        app, f = self._fake()
        d = tempfile.mkdtemp()
        p = os.path.join(d, "F4GOP_photo.jpg")
        Image.new("RGB", (64, 48), (10, 200, 10)).save(p)
        got = []
        with mock.patch.object(clip, "copy_image", lambda im: got.append(im.size)):
            self.assertTrue(app.App.gallery_copy(f, {"file": p, "png": ""}))
        self.assertEqual(got, [(64, 48)])
        self.assertIn("64×48", f.log.call_args[0][0])

    def test_erreur_affichee(self):
        app, f = self._fake()
        d = tempfile.mkdtemp()
        p = os.path.join(d, "x.png")
        Image.new("RGB", (4, 4)).save(p)

        def boom(im):
            raise clip.ClipError("copie impossible : le presse-papiers est occupé par un autre programme")
        with mock.patch.object(clip, "copy_image", boom), mock.patch.object(app.messagebox, "showerror") as se:
            self.assertFalse(app.App.copy_image(f, p))
        se.assert_called_once()

    def test_menu_onglet_rx(self):
        import tkinter as tk
        import panel
        try:
            root = tk.Tk()
        except tk.TclError as e:
            raise unittest.SkipTest(str(e))
        try:
            v = panel.ImageView(root, width=50, height=50)
            v.pack()
            root.update()
            seen = []
            v.menu_cb = seen.append
            v.event_generate("<Button-3>", x=5, y=5)
            root.update()
            self.assertEqual(len(seen), 1)                  # clic droit -> menu (Copier l'image…)
        finally:
            root.destroy()

    def test_traductions(self):
        try:
            i18n.set_lang("en")
            self.assertEqual(i18n.tr("Copier l'image"), "Copy image")
        finally:
            i18n.set_lang("fr")


if __name__ == "__main__":
    unittest.main()
