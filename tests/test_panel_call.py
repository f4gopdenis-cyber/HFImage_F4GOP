"""Version 0.87 : indicatif du panneau — la réception la plus récente gagne, et pas d'ancien indicatif."""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Stub:
    def __init__(self, App):
        self.shown = []
        self.panel = type("P", (), {"set_call": lambda _s, c: self.shown.append(c or "—")})()
        self.online, self.rig_freq = {}, 7058000
        self.v_call = type("V", (), {"get": lambda _s: "F4GOP"})()
        self.mycall = lambda: "F4GOP"
        self._rx_call = App._rx_call.__get__(self)
        self._guess_tx_call = App._guess_tx_call.__get__(self)


class IndicatifPanneau(unittest.TestCase):
    def setUp(self):
        try:
            import app
        except ImportError as e:                         # pas de tkinter sur cette machine
            self.skipTest(str(e))
        self.s = Stub(app.App)

    def test_ancienne_image_n_ecrase_plus(self):
        s, t0 = self.s, time.time() - 60
        s._rx_call("F1ABL", t0)                          # ancienne image DATAC
        s._rx_call("M0JGM")                              # annonce hybride reçue maintenant
        s._rx_call("F1ABL", t0)                          # rafraîchissement du panneau (ancienne image)
        self.assertEqual(s.shown[-1], "M0JGM")

    def test_station_en_emission_sur_la_frequence(self):
        s = self.s
        s._rx_call("F1ABL", time.time() - 60)
        now = time.time()
        s.online = {"M0JGM": {"call": "M0JGM", "state": "TX", "freq": 7058000, "seen": now},
                    "RK1AT": {"call": "RK1AT", "state": "TX", "freq": 14233000, "seen": now},
                    "F4EEH": {"call": "F4EEH", "state": "RX", "freq": 7058000, "seen": now}}
        s._rx_call(s._guess_tx_call(), now, guess=True)
        self.assertEqual(s.shown[-1], "M0JGM ?")
        s._rx_call("M0JGM", now + 30)                    # identification de fin reçue
        self.assertEqual(s.shown[-1], "M0JGM")

    def test_sans_station_connue(self):
        s = self.s
        s._rx_call("F1ABL", time.time() - 60)
        now = time.time()
        s._rx_call(s._guess_tx_call(), now, guess=bool(s._guess_tx_call()))
        self.assertEqual(s.shown[-1], "—")                # plus l'ancien F1ABL

    def test_deux_stations_en_emission(self):
        s, now = self.s, time.time()
        s.online = {k: {"call": k, "state": "TX", "freq": 7058500, "seen": now} for k in ("M0JGM", "F1ABL")}
        self.assertIsNone(s._guess_tx_call())           # ambigu : on ne devine pas


if __name__ == "__main__":
    unittest.main()
