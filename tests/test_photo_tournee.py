"""1.21 (demande de G4GIM) : photos de téléphone « couchées » remises droites, boutons pour tourner."""
import io
import os
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import imgfmt  # noqa: E402
from PIL import Image  # noqa: E402


def phone_photo(path, orientation=6):
    """Photo enregistrée couchée (400×300) avec l'indication « tourner de 90° » (6)."""
    im = Image.new("RGB", (400, 300), (0, 0, 255))
    im.paste((255, 0, 0), (0, 0, 400, 30))              # bande rouge en haut du capteur
    ex = Image.Exif()
    ex[0x0112] = orientation
    im.save(path, "JPEG", exif=ex.tobytes(), quality=95)


class Photo(unittest.TestCase):
    def test_remise_droite(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "tel.jpg")
            phone_photo(p)
            notes = []
            img, raw, kind = imgfmt.load_source(p, notes)
        self.assertEqual(img.size, (300, 400))                 # debout
        self.assertEqual(notes, [6])
        self.assertEqual(kind, "jpeg")
        sent = Image.open(io.BytesIO(raw))                     # octets « originaux » envoyés : droits
        self.assertEqual(sent.size, (300, 400))
        self.assertEqual(imgfmt.orientation(sent), 1)
        # orientation 6 : le haut du capteur (rouge) se retrouve à droite
        self.assertGreater(img.getpixel((295, 200))[0], 200)

    def test_photo_normale_intacte(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "n.jpg")
            Image.new("RGB", (400, 300)).save(p)
            with open(p, "rb") as f:
                raw0 = f.read()
            notes = []
            img, raw, kind = imgfmt.load_source(p, notes)
        self.assertEqual((img.size, raw, notes), ((400, 300), raw0, []))

    def test_reception_et_site(self):
        import websync
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "tel.jpg")
            phone_photo(p)
            self.assertEqual(imgfmt.open_upright(p).size, (300, 400))
            blob, size = websync.label_image(p, "G4GIM")
        self.assertEqual(size[0], 300)

    def test_boutons_tourner(self):
        try:
            import app
        except (ImportError, OSError) as e:
            self.skipTest(str(e))
        logs = []
        s = types.SimpleNamespace(src_img=Image.new("RGB", (400, 300)), src_kind="jpeg", src_raw=b"x",
                                  src_anim=None, tx_busy=False, bubbles=[1], tx=object(), src_path="a.jpg",
                                  _show=lambda *a: None, _set_text=lambda *a: None, prepare=lambda: None,
                                  log=logs.append, lb_src=None, lb_src_info=None)
        app.App._rotate_tx(s, -90)
        self.assertEqual(s.src_img.size, (300, 400))
        self.assertEqual(Image.open(io.BytesIO(s.src_raw)).size, (300, 400))
        self.assertEqual((s.bubbles, s.tx), ([], None))
        s.src_kind = "svg"
        app.App._rotate_tx(s, 90)
        self.assertEqual(s.src_img.size, (300, 400))
        self.assertTrue(logs)


if __name__ == "__main__":
    unittest.main()
