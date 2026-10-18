"""Version 0.84 : une seule copie par image, rangement par jour, nettoyage des anciennes images."""
import datetime
import io
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from PIL import Image  # noqa: E402

import engine  # noqa: E402
import imgfmt  # noqa: E402
import rxclean  # noqa: E402

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="30"><rect width="40" height="30" fill="red"/></svg>'


def encoded(fmt):
    b = io.BytesIO()
    Image.new("RGB", (64, 48), (10, 120, 200)).save(b, fmt)
    return b.getvalue()


class UneSeuleCopie(unittest.TestCase):
    def test_formats_raster(self):
        d = tempfile.mkdtemp()
        for fmt, pil in (("jpeg", "JPEG"), ("webp", "WEBP"), ("png", "PNG"), ("avif", "AVIF")):
            try:
                data = encoded(pil)
            except (KeyError, OSError):
                continue                              # format absent de ce Pillow
            path, shown = imgfmt.save_received(os.path.join(d, "img_" + fmt), fmt, data)
            self.assertEqual(shown, path, fmt)        # affiché tel quel, pas de copie
        self.assertFalse([n for n in os.listdir(d) if n.endswith(".png") and not n.startswith("img_png")])

    def test_svg_rendu_cache(self):
        d = tempfile.mkdtemp()
        try:
            path, shown = imgfmt.save_received(os.path.join(d, "dessin"), "svg", SVG)
        except Exception as e:
            self.skipTest(str(e))
        self.assertTrue(path.endswith(".svg"))
        if shown:
            self.assertEqual(os.path.dirname(shown), os.path.join(d, imgfmt.PREVIEW_DIR))
        self.assertEqual(sorted(n for n in os.listdir(d) if os.path.isfile(os.path.join(d, n))), ["dessin.svg"])

    def test_visionneuse(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "a.jpg")
        with open(p, "wb") as f:
            f.write(encoded("JPEG"))
        self.assertEqual(imgfmt.viewable(p), p)
        try:
            data = encoded("AVIF")
        except (KeyError, OSError):
            self.skipTest("AVIF absent")
        a = os.path.join(d, "b.avif")
        with open(a, "wb") as f:
            f.write(data)
        v = imgfmt.viewable(a)
        self.assertTrue(v.endswith(".png") and os.path.exists(v))


class ParJour(unittest.TestCase):
    def test_image_rangee_dans_le_dossier_du_jour(self):
        out = tempfile.mkdtemp()
        rx = engine.RxEngine.__new__(engine.RxEngine)
        rx.outdir, rx.saved = out, {}
        got = []
        rx.on_image = lambda info, path, shown, mode: got.append((path, shown))
        rx._save(({"id": 5, "call": "F4EMK", "fmt": "jpeg"}, encoded("JPEG")), "DATAC1X")
        path, shown = got[0]
        self.assertEqual(os.path.dirname(path), os.path.join(out, time.strftime("%Y-%m-%d")))
        self.assertEqual(shown, path)

    def test_galerie_retrouve_les_dossiers_du_jour(self):
        try:
            import gallery
        except ImportError as e:                       # pas de tkinter sur cette machine
            self.skipTest(str(e))
        out = tempfile.mkdtemp()
        day = os.path.join(out, "2026-10-18")
        os.makedirs(day)
        with open(os.path.join(day, "20261018_193812_DATAC0-HYB_M0JGM.jpg"), "wb") as f:
            f.write(encoded("JPEG"))
        items = gallery.GalleryStore.__new__(gallery.GalleryStore)
        items.folder = out
        found = items.scan()
        self.assertEqual([(e["call"], e["mode"]) for e in found], [("M0JGM", "DATAC0-HYB")])


class Nettoyage(unittest.TestCase):
    def test_seuls_les_vieux_dossiers_du_jour(self):
        out = tempfile.mkdtemp()
        today = datetime.date(2026, 10, 18)
        keep = ["2026-10-18", "2026-09-19", "fichiers", "wav", "enregistrements", "mes photos", "2026-13-40",
                os.path.join("envoyees", "2026-10-01")]
        drop = ["2026-09-17", "2025-01-01", os.path.join("envoyees", "2026-08-01"),
                os.path.join("relecture", "2026-07-14")]
        for n in keep + drop:
            os.makedirs(os.path.join(out, n))
            with open(os.path.join(out, n, "x.jpg"), "wb") as f:
                f.write(b"12345")
        with open(os.path.join(out, "20260101_120000_DATAC1_F4GOP.avif"), "wb") as f:   # ancienne image à plat
            f.write(b"x")
        n, freed = rxclean.clean(out, 30, today)
        self.assertEqual((n, freed), (len(drop), 5 * len(drop)))
        for k in keep:
            self.assertTrue(os.path.isdir(os.path.join(out, k)), k)
        for k in drop:
            self.assertFalse(os.path.exists(os.path.join(out, k)), k)
        self.assertTrue(os.path.exists(os.path.join(out, "20260101_120000_DATAC1_F4GOP.avif")))


if __name__ == "__main__":
    unittest.main()
