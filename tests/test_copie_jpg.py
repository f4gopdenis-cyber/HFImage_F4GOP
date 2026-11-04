"""2.00 (demande de VK3DNH) : copie JPG de chaque image reçue dans un seul dossier (sites web, QSL.net),
même nom que l'image reçue, sans sous-dossier par jour ; renommée quand l'indicatif arrive."""
import gc
import io
import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from PIL import Image  # noqa: E402

import jpgcopy  # noqa: E402


class Module(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.out = os.path.join(self.d, "jpg")

    def img(self, name, fmt, **kw):
        p = os.path.join(self.d, name)
        Image.new("RGB", (200, 150), "orange").save(p, fmt, **kw)
        return p

    def test_jpeg_copie_tel_quel(self):
        p = self.img("20261103_081500_DATAC1X_F5TGB.jpg", "JPEG")
        dst = jpgcopy.make(self.out, p)
        self.assertEqual(dst, os.path.join(self.out, "20261103_081500_DATAC1X_F5TGB.jpg"))
        with open(dst, "rb") as a, open(p, "rb") as b:
            self.assertEqual(a.read(), b.read())                              # sans perte

    def test_autres_formats_convertis(self):
        for name, fmt in (("a.png", "PNG"), ("b.webp", "WEBP"), ("c.gif", "GIF")):
            dst = jpgcopy.make(self.out, self.img(name, fmt))
            self.assertTrue(dst.endswith(".jpg"))
            with Image.open(dst) as im:
                self.assertEqual(im.format, "JPEG")
        self.assertEqual(sorted(os.listdir(self.out)), ["a.jpg", "b.jpg", "c.jpg"])   # aucun sous-dossier

    def test_renommee_avec_l_indicatif(self):
        first = jpgcopy.make(self.out, self.img("20261103_081500_DATAC3.png", "PNG"))
        dst = jpgcopy.make(self.out, self.img("20261103_081500_DATAC3_VK3DNH.png", "PNG"), old=first)
        self.assertEqual(os.listdir(self.out), [os.path.basename(dst)])
        self.assertIn("VK3DNH", dst)


class Appli(unittest.TestCase):
    def setUp(self):
        gc.collect()
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.app = app
        self.d = tempfile.mkdtemp()
        self.rx = os.path.join(self.d, "HFImage")
        os.makedirs(self.rx)
        self.conf = os.path.join(self.d, "c.json")
        with open(self.conf, "w") as f:
            json.dump({"callsign": "F4GOP", "licence_ok": "1.0", "lang": "fr", "folder": self.rx}, f)
        self.p = mock.patch.object(app, "CONF_PATH", self.conf)
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
        self.a = None
        gc.collect()
        self.p.stop()

    def wait_files(self, folder, n=1):
        ls = lambda: sorted(f for f in os.listdir(folder) if not f.endswith(".part")) if os.path.isdir(folder) else []
        t = time.time()
        while time.time() - t < 5:
            self.a.update()
            if len(ls()) >= n:
                return ls()
            time.sleep(0.05)
        return ls()

    def test_decochee_par_defaut(self):
        self.assertFalse(self.app.DEFAULTS["jpg_copy"])
        p = os.path.join(self.rx, "x.png")
        Image.new("RGB", (64, 64)).save(p)
        self.a._jpg_copy(1, p)
        time.sleep(0.3)
        self.assertFalse(os.path.exists(os.path.join(self.rx, "jpg")))

    def test_copie_puis_indicatif(self):
        a = self.a
        a.conf.update(jpg_copy=True, jpg_dir="")
        day = os.path.join(self.rx, "2026-11-03")
        os.makedirs(day)
        p = os.path.join(day, "20261103_081500_DATAC3.avif")
        buf = io.BytesIO()
        Image.new("RGB", (64, 64), "blue").save(buf, "WEBP")       # contenu lisible (extension .avif)
        with open(p, "wb") as f:
            f.write(buf.getvalue())
        a._jpg_copy(7, p)
        out = os.path.join(self.rx, "jpg")                          # dossier par défaut
        self.assertEqual(self.wait_files(out), ["20261103_081500_DATAC3.jpg"])
        p2 = os.path.join(day, "20261103_081500_DATAC3_VK3DNH.avif")
        os.replace(p, p2)
        a._jpg_copy(7, p2)                                         # l'indicatif est arrivé
        t = time.time()
        while time.time() - t < 5 and os.listdir(out) != ["20261103_081500_DATAC3_VK3DNH.jpg"]:
            a.update()
            time.sleep(0.05)
        self.assertEqual(os.listdir(out), ["20261103_081500_DATAC3_VK3DNH.jpg"])

    def test_pas_dans_le_dossier_des_images_recues(self):
        a = self.a
        a.conf.update(jpg_copy=True, jpg_dir=self.rx)               # galerie : images en double
        p = os.path.join(self.rx, "y.png")
        Image.new("RGB", (64, 64)).save(p)
        a._jpg_copy(2, p)
        time.sleep(0.3)
        self.assertFalse(os.path.exists(os.path.join(self.rx, "y.jpg")))


if __name__ == "__main__":
    unittest.main()
