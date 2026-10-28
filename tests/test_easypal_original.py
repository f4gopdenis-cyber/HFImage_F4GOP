"""1.81 : mode EasyPal, fichier original trop long pour la durée choisie -> refusé avec un message
(VK6ATI : 48 min en E / QAM4 / RS4, on croyait que rien ne partait). Traduction ligne par ligne."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import i18n  # noqa: E402


class TraductionMultiligne(unittest.TestCase):
    def tearDown(self):
        i18n.set_lang("fr")

    def test_deux_lignes_traduites_separement(self):
        i18n.set_lang("en")
        s = ("Fichier original (138193 octets) : 90 s, c'est trop court en EasyPal.\n"
             "Minimum : environ 48 min 15 s, ou choisissez avif / jpeg pour le réduire.")
        out = i18n.tr(s)
        self.assertEqual(out.split("\n")[0], "Original file (138193 bytes): 90 s is too short in EasyPal.")
        self.assertTrue(out.split("\n")[1].startswith("Minimum: about 48 min 15 s"), out)


class EasyPalOriginal(unittest.TestCase):
    def test_refus_si_trop_long(self):
        import hamdrm
        if not hamdrm.AVAILABLE:
            self.skipTest("hamdrm absent")
        import tkinter as tk
        try:
            import app
            a = app.App()
        except tk.TclError:
            self.skipTest("pas d'écran")
        try:
            from PIL import Image
            import io
            im = Image.effect_noise((320, 240), 30).convert("RGB")
            b = io.BytesIO()
            im.save(b, "JPEG", quality=80)
            a.src_img, a.src_raw, a.src_kind = Image.open(io.BytesIO(b.getvalue())), b.getvalue(), "jpeg"
            v = a.v_drm
            v["drm_mode"].set("E"); v["drm_qam"].set("QAM4"); v["drm_rs"].set("RS4")
            a.tx = None
            a._prepare_drm(a.src_img, "auto", "original", 90)
            self.assertIsNone(a.tx)
            self.assertIn("EasyPal", a.v_txinfo.get())
            a._prepare_drm(a.src_img, "auto", "original", 7200)
            self.assertIsNotNone(a.tx)
        finally:
            a.destroy()


if __name__ == "__main__":
    unittest.main()
