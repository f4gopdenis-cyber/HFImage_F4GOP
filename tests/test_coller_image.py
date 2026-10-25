"""Version 1.67 : coller dans l'onglet TX une image copiée dans le navigateur (demande de G0GOO)."""
import gc
import os
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Coller(unittest.TestCase):
    def setUp(self):
        gc.collect()
        try:
            import app
            from PIL import ImageGrab
        except ImportError as e:
            self.skipTest(str(e))
        self.app, self.ImageGrab = app, ImageGrab
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        gc.collect()

    def stub(self):
        A = self.app.App
        s = mock.Mock()
        s.tx_busy = False
        s.PASTE_EXT = A.PASTE_EXT
        s.v_folder.get.return_value = self.dir
        s.paste_image = lambda: A.paste_image(s)
        return s

    def test_image_du_navigateur(self):
        s = self.stub()
        with mock.patch.object(self.ImageGrab, "grabclipboard", lambda: Image.new("RGB", (120, 80), "red")):
            s.paste_image()
        p = s.load_image.call_args[0][0]
        self.assertTrue(p.startswith(os.path.join(self.dir, "collées")))
        self.assertEqual(Image.open(p).size, (120, 80))
        s.show_tab.assert_called_with("tx")

    def test_fichier_copie_dans_l_explorateur(self):
        s = self.stub()
        f = os.path.join(self.dir, "photo.jpg")
        Image.new("RGB", (10, 10)).save(f)
        with mock.patch.object(self.ImageGrab, "grabclipboard", lambda: [os.path.join(self.dir, "x.txt"), f]):
            s.paste_image()
        s.load_image.assert_called_with(f)

    def test_pas_d_image(self):
        s = self.stub()
        shown = []
        with mock.patch.object(self.ImageGrab, "grabclipboard", lambda: None), \
                mock.patch.object(self.app.messagebox, "showinfo", lambda *a, **k: shown.append(a[1])):
            s.paste_image()
        s.load_image.assert_not_called()
        self.assertIn("Copier l'image", shown[0])

    def test_pendant_l_emission_rien(self):
        s = self.stub()
        s.tx_busy = True
        with mock.patch.object(self.ImageGrab, "grabclipboard", lambda: Image.new("RGB", (5, 5))):
            s.paste_image()
        s.load_image.assert_not_called()

    def test_ctrl_v_dans_une_case_de_texte(self):
        s = self.stub()
        e = mock.Mock()
        e.widget.winfo_class.return_value = "TEntry"
        self.assertIsNone(self.app.App._ctrl_v(s, e))           # Ctrl+V colle le texte comme d'habitude
        e.widget.winfo_class.return_value = "Label"
        s._tab_shown.return_value = True
        s.paste_image = mock.Mock()
        self.assertEqual(self.app.App._ctrl_v(s, e), "break")
        s.paste_image.assert_called_once()


if __name__ == "__main__":
    unittest.main()
