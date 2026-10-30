"""1.94 : le mode DATA ne se règle plus qu'avec le bouton « DATA auto » (demande de F4GOP)."""
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import app  # noqa: E402


class Conversion(unittest.TestCase):
    def test_anciens_reglages(self):
        """Ceux à qui HFImage passait le poste en DATA gardent le bouton DATA auto allumé."""
        f = app.data_policy_from_old
        self.assertEqual(f({"data_auto": True, "data_action": "send"}, {}), "auto")
        self.assertEqual(f({"data_action": "send"}, {"set_mode": "data"}), "auto")   # Mode Data/Pkt
        self.assertEqual(f({"data_action": "send"}, {"set_mode": "none"}), "none")   # Émettre sans rien dire
        self.assertEqual(f({"data_action": "send"}, {"set_mode": "usb"}), "none")
        self.assertEqual(f({"data_action": "ask"}, {}), "auto")
        self.assertEqual(f({"data_action": "switch"}, {}), "auto")
        self.assertEqual(f({}, {}), "auto")


class Bouton(unittest.TestCase):
    def stub(self, conf):
        s = types.SimpleNamespace(conf=conf, radio_cfg={}, logs=[])
        s.log = s.logs.append
        s._save_conf_file = lambda: None
        s._data_auto_paint = lambda: None
        for k in ("data_policy", "set_data_policy", "_data_auto_toggle"):
            setattr(s, k, getattr(app.App, k).__get__(s))
        return s

    def test_bouton_allume_eteint(self):
        s = self.stub({"data_policy": "none"})
        s._data_auto_toggle()
        self.assertEqual(s.data_policy(), "auto")
        s._data_auto_toggle()
        self.assertEqual(s.data_policy(), "none")

    def test_bouton_eteint_par_defaut_ne_touche_pas(self):
        s = self.stub({"data_policy": "auto"})
        s._data_auto_toggle()
        self.assertEqual(s.data_policy(), "none")

    def test_reglage_inconnu(self):
        s = self.stub({"data_policy": "n'importe quoi", "data_auto": True})
        self.assertEqual(s.data_policy(), "auto")


if __name__ == "__main__":
    unittest.main()
