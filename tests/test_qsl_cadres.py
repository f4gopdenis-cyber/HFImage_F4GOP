"""2.48 (F4GOP, d'après la carte de M7WUV) : carte QSL avec cadres lumineux autour des textes."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image  # noqa: E402
import qsl  # noqa: E402

ARGS = ("F4GOP", "IN98QR", "M7WUV", "7.058 MHz", "SNR +4 dB", "TNX QSO, 73 !", "2026-11-22 15:42")


def photo():
    im = Image.new("RGB", (1200, 750))
    for y in range(750):
        for x in range(0, 1200, 40):
            im.paste((x % 255, y % 255, 150), (x, y, x + 40, y + 1))
    return im


class Cadres(unittest.TestCase):
    def test_sans_cadres_inchange(self):
        bg = photo()
        a = qsl.make_card(bg, *ARGS, style=dict(qsl.DEFAULT_STYLE))
        b = qsl.make_card(bg, *ARGS)
        self.assertEqual(a.tobytes(), b.tobytes())                 # par défaut : comme avant
        self.assertFalse(qsl.DEFAULT_STYLE["frames"])

    def test_cadres_a_la_place_des_bandeaux(self):
        bg = photo()
        boxes = {}
        card = qsl.make_card(bg, *ARGS, style=dict(qsl.DEFAULT_STYLE, frames=True), boxes=boxes)
        self.assertEqual(card.size, qsl.card_size(bg))
        W, H = card.size
        # milieu du bandeau du haut, loin des textes : la photo reste visible (pas de bandeau sombre)
        x, y = W // 2, 20
        self.assertEqual(card.getpixel((x, y)), bg.resize(card.size).getpixel((x, y)))
        # bord du cadre de l'indicatif : couleur du contour (doré)
        x0, y0, x1, y1 = boxes["call"]
        edge = card.getpixel((int((x0 + x1) / 2), int(y1 + 6 * card.size[0] / 960)))
        self.assertGreater(edge[0], 150)
        self.assertGreater(edge[1], 120)
        for k in ("call", "loc", "to", "info", "msg"):               # cadres de déplacement à la souris
            self.assertIn(k, boxes)

    def test_couleur_et_halo(self):
        bg = photo()
        st = dict(qsl.DEFAULT_STYLE, frames=True, frame_color="#3ad6ff")
        a = qsl.make_card(bg, *ARGS, style=dict(st, frame_glow=0))
        b = qsl.make_card(bg, *ARGS, style=dict(st, frame_glow=100))
        self.assertNotEqual(a.tobytes(), b.tobytes())             # le halo change l'image
        c = qsl.make_card(None, *ARGS, style=st, size=(480, 300))  # aperçu, fond dégradé
        self.assertEqual(c.size, (480, 300))


class Neon(unittest.TestCase):
    """2.49 : cadres néon, intérieur sombre et lueur seulement à l'extérieur (textes lisibles)."""

    def test_neon_different_du_dore(self):
        bg = photo()
        st = dict(qsl.DEFAULT_STYLE, frames=True, frame_color="#ff2ec8")
        a = qsl.make_card(bg, *ARGS, style=st)
        b = qsl.make_card(bg, *ARGS, style=dict(st, frame_style="neon"))
        self.assertNotEqual(a.tobytes(), b.tobytes())
        self.assertIn("Rose", qsl.NEON_COLORS)

    def test_interieur_sombre_et_lueur_dehors(self):
        bg = Image.new("RGB", (1200, 750), (220, 220, 220))          # photo très claire
        boxes = {}
        card = qsl.make_card(bg, *ARGS, style=dict(qsl.DEFAULT_STYLE, frames=True, frame_style="neon",
                                                  frame_color="#20e8ff", frame_glow=100), boxes=boxes)
        k = card.size[0] / 960
        x0, y0, x1, y1 = boxes["msg"]
        inner = card.getpixel((int(x1 + 6 * k), int((y0 + y1) / 2)))      # dans le cadre, après le texte
        self.assertLess(sum(inner), 200)                                 # intérieur sombre : texte lisible
        outer = card.getpixel((int(x1 + 30 * k), int((y0 + y1) / 2)))    # juste à l'extérieur : lueur bleue
        self.assertGreater(outer[2], outer[0])

    def test_texte_de_la_couleur_du_cadre_en_blanc(self):
        self.assertTrue(qsl._close((255, 209, 102), (255, 196, 64)))
        self.assertFalse(qsl._close((255, 255, 255), (32, 232, 255)))


class Fenetre(unittest.TestCase):
    """La case « Cadres lumineux » de la fenêtre Carte QSL change l'aperçu et reste dans le style."""

    def test_case_cadres(self):
        import gc
        import json
        import tempfile
        import time
        from unittest import mock
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        conf = os.path.join(tempfile.mkdtemp(), "c.json")
        with open(conf, "w") as f:
            json.dump({"callsign": "F4GOP", "licence_ok": "1.0", "lang": "fr", "net_on": False}, f)
        gc.collect()
        with mock.patch.object(app, "CONF_PATH", conf):
            try:
                a = app.App()
            except Exception as e:
                raise unittest.SkipTest(str(e))
            try:
                a.src_img = photo()
                seen = []
                real = app.qsl.make_card
                with mock.patch.object(app.qsl, "make_card",
                                       lambda *x, **k: (seen.append(dict(k.get("style") or {})), real(*x, **k))[1]):
                    a.qsl_dialog()
                    import tkinter as tk
                    from tkinter import ttk

                    def walk(w):
                        yield w
                        for c in w.winfo_children():
                            yield from walk(c)
                    win = [w for w in a.winfo_children() if isinstance(w, tk.Toplevel) and w.title() == "Carte QSL"][0]
                    cb = next(w for w in walk(win) if isinstance(w, ttk.Checkbutton)
                              and "Cadres lumineux" in str(w.cget("text")))
                    cb.invoke()
                    end = time.time() + 2
                    while time.time() < end and not any(s.get("frames") for s in seen):
                        a.update()
                        time.sleep(0.02)
                self.assertTrue(any(s.get("frames") for s in seen))
                win.destroy()
            finally:
                a.destroy()


if __name__ == "__main__":
    unittest.main()
