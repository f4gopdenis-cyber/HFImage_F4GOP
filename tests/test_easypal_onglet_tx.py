"""2.03 (signalé par F4GOP) : pendant la réception d'une image EasyPal, HFImage revenait sans cesse sur
l'onglet RX (le total de segments et l'indicatif changent pendant la réception). Il n'y passe plus qu'une
fois par réception : l'opérateur peut préparer son image dans l'onglet TX."""
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Onglet(unittest.TestCase):
    def setUp(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        A = app.App
        s = types.SimpleNamespace(tx_busy=False, DRM_EPISODE_GAP_S=A.DRM_EPISODE_GAP_S, shown=[])
        s.tab = "tx"
        s._tab_shown = lambda name: s.tab == name
        s.show_tab = lambda name, focus=True: (s.shown.append(name), setattr(s, "tab", name))
        for n in ("_drm_episode", "_rx_tab_auto"):
            setattr(s, n, getattr(A, n).__get__(s))
        self.s = s

    def poll(self, t):
        self.s._rx_tab_auto(("easypal", self.s._drm_episode(t)))

    def test_une_seule_fois_par_reception(self):
        s = self.s
        self.poll(100.0)
        self.assertEqual(s.shown, ["rx"])                  # début de l'image : onglet RX
        s.tab = "tx"                                       # l'opérateur revient préparer son image
        for t in range(101, 160):                          # signal continu (total et indicatif qui changent)
            self.poll(float(t))
        self.assertEqual(s.tab, "tx")                      # laissé sur TX
        self.assertEqual(s.shown, ["rx"])

    def test_nouvelle_image_apres_une_pause(self):
        s = self.s
        self.poll(100.0)
        s.tab = "tx"
        self.poll(130.0)                                   # 30 s sans signal : autre émission
        self.assertEqual(s.shown, ["rx", "rx"])

    def test_etat_affiche_apres_le_signal(self):
        s = self.s
        self.poll(100.0)
        s.tab = "tx"
        for _ in range(20):                                # l'état reste affiché, drm_t ne bouge plus
            self.poll(100.0)
        self.assertEqual(s.shown, ["rx"])


if __name__ == "__main__":
    unittest.main()
