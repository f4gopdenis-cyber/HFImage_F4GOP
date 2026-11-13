"""2.38 : bandeau défilant ajouté ou déplacé directement sur l'image TX : place retenue, vitesse reprise."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_edition_directe import EditionDirecte, E  # noqa: E402


class BandeauTX(EditionDirecte):
    test_ajouter_deplacer_agrandir_texte = None
    test_logo_png_et_menu = None

    def test_place_retenue(self):
        a, ed = self.a, self.ed
        ed.add_text("CQ CQ de F4GOP")
        ed.sel = ("b", 0)
        ed.set_bubble(style="bandeau")
        ed.set_bubble(speed="rapide")
        b = a.bubbles[0]
        a.prepare(sync=True)
        a.update()
        ox, oy, dw, dh = self.box()
        y = oy + int(b["cy"] * dh)
        self.assertEqual(ed.hit(E(ox + dw // 2, y))[:2], ("b", 0))
        ed.press(E(ox + dw // 2, y))
        ed.motion(E(ox + dw // 3, oy + int(0.45 * dh)))
        ed.release(E(ox + dw // 3, oy + int(0.45 * dh)))
        self.assertAlmostEqual(a.conf["bub_banner_cy"], 0.45, delta=0.03)
        ed.add_text("Merci à tous les OM")                 # reprend le style : bandeau
        n = a.bubbles[1]
        self.assertEqual(n["style"], "bandeau")
        self.assertAlmostEqual(n["cy"], 0.45, delta=0.03)  # à la place retenue, pas au milieu
        self.assertEqual(n.get("speed"), "rapide")
        a.prepare(sync=True)
        self.assertIsNotNone(a.tx)


if __name__ == "__main__":
    unittest.main()
