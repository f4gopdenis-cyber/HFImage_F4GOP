"""Version 1.69 : logo réductible jusqu'à 4 % de la largeur de l'image (demande de M7WUV)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

try:
    import trafic  # noqa: E402
except ImportError:
    trafic = None


@unittest.skipIf(trafic is None, "dépendances absentes")
class LogoPetit(unittest.TestCase):
    def test_tres_petit_logo_sur_grande_image(self):
        x, y, W, H, tw = trafic.pip_layout((4000, 3000), (200, 200), "", "haut-droite", "libre", None, 0.04,
                                           logo=True)[:5]
        self.assertEqual(tw, 160)                         # 4 % de 4000 px (avant : 10 % au moins = 400 px)

    def test_limite_basse(self):
        tw = trafic.pip_layout((1000, 800), (100, 100), "", scale=0.01, logo=True)[4]
        self.assertEqual(tw, 40)                          # pas plus petit que 4 %

    def test_image_correspondant_inchangee(self):
        tw = trafic.pip_layout((600, 400), (100, 100), "F1ABC", scale=0.04)[4]
        self.assertEqual(tw, 40)                          # 40 px au moins avec légende


if __name__ == "__main__":
    unittest.main()
