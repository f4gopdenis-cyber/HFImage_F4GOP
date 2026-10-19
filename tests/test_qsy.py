"""Version 1.01 : changer de fréquence par CAT (idée de G7VQV)."""
import os
import sys
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import radio  # noqa: E402
from test_mode_data import FakeKenwood  # noqa: E402


class Kenwood(FakeKenwood):
    def __init__(self, model, mode, hz):
        super().__init__(model, mode)
        self.hz = hz

    def write(self, cmd):
        if cmd.startswith("FA"):
            self.sent.append(cmd)
            self.hz = int(cmd[2:-1])
        else:
            super().write(cmd)

    def query(self, cmd, timeout=0.6):
        if cmd == "FA;":
            return f"FA{self.hz:011d};"
        return super().query(cmd, timeout)


class Rigctl(radio.RigctlRig):
    def __init__(self):
        self.model, self.lock, self.f, self.m = "IC-7300", threading.Lock(), 14233000, "PKTUSB"

    def cmd(self, c, nlines=1):
        if c == "f":
            return [str(self.f)]
        if c == "m":
            return [self.m, "3000"]
        if c.startswith("F "):
            self.f = int(c[2:])
        elif c.startswith("M "):
            self.m = c.split()[1]
        return ["RPRT 0"]


class Qsy(unittest.TestCase):
    def setUp(self):
        self.old, radio.time.sleep = radio.time.sleep, (lambda s: None)

    def tearDown(self):
        radio.time.sleep = self.old

    def test_ts890_14_vers_7_reste_en_data(self):
        r = Kenwood("TS-890S", "2", 14233000)
        r.data = True                                    # USB-DATA sur 20 m
        msg = r.qsy(7058000, "LSB")
        self.assertEqual(r.freq(), 7058000)
        self.assertEqual(r.mode(), "LSB-DATA1")
        self.assertIn("FA00007058000;", r.sent)
        self.assertIn("7.058", msg)

    def test_ts990_meme_bande_laterale(self):
        r = Kenwood("TS-990S", "1", 3733000)
        r.qsy(7058000, "LSB")
        self.assertEqual(r.sent, ["FA00007058000;"])     # rien d'autre à changer

    def test_hamlib(self):
        r = Rigctl()
        r.qsy(7058000, "LSB")
        self.assertEqual((r.f, r.m), (7058000, "PKTLSB"))

    def test_poste_reste_ailleurs(self):
        r = Kenwood("TS-590SG", "2", 14233000)
        r.set_freq = lambda hz: None                     # le poste ignore la commande
        with self.assertRaises(RuntimeError):
            r.qsy(7058000)

    def test_saisie(self):
        try:
            import app
        except ImportError as e:
            self.skipTest(str(e))
        p = app.App._parse_mhz
        self.assertEqual(p("7.058"), 7058000)
        self.assertEqual(p("7,058 MHz"), 7058000)
        self.assertEqual(p("14233"), 14233000)
        self.assertEqual(p("3733000"), 3733000)
        self.assertIsNone(p("abc"))
        self.assertIsNone(p("0.5"))


if __name__ == "__main__":
    unittest.main()
