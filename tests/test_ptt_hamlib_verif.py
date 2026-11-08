"""2.25 (IC-9700) : « T 3 » accepté sans passer en émission -> HFImage le voit (« t ») et essaie T 1."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import radio  # noqa: E402


class FakeRig(radio.RigctlRig):
    def __init__(self, keys_on, report=True):
        self.keys_on, self.report, self.sent, self.tx = keys_on, report, [], False

    def cmd(self, c, nlines=1):
        self.sent.append(c)
        if c.startswith("T "):
            self.tx = c in self.keys_on or (c == "T 0" and False)
            if c == "T 0":
                self.tx = False
            return ["RPRT 0"]
        if c == "t":
            return [("1" if self.tx else "0")] if self.report else ["RPRT -11"]
        return ["RPRT 0"]

    def _ok(self, c):
        r = self.cmd(c)
        return bool(r) and r[0] == "RPRT 0"


class Verif(unittest.TestCase):
    def setUp(self):
        self.p = mock.patch.object(radio.time, "sleep")
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_ic9700_t3_accepte_sans_emettre(self):
        r = FakeRig(keys_on={"T 1"})
        r.ptt(True)
        self.assertTrue(r.tx)
        self.assertEqual(r._ptt_cmd, "T 1")
        r.sent.clear()
        r.ptt(False)
        r.ptt(True)                                           # la 2e fois : T 1 directement
        self.assertEqual([c for c in r.sent if c.startswith("T ") and c != "T 0"][0], "T 1")

    def test_poste_normal_t3(self):
        r = FakeRig(keys_on={"T 3", "T 1"})
        r.ptt(True)
        self.assertEqual(r._ptt_cmd, "T 3")
        self.assertNotIn("T 1", r.sent)

    def test_poste_qui_ne_dit_pas_son_etat(self):
        r = FakeRig(keys_on={"T 3"}, report=False)
        r.ptt(True)
        self.assertEqual([c for c in r.sent if c.startswith("T ")], ["T 3"])   # comme avant
