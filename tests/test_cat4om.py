"""2.28 (PD1EG, Cat4om) : faux rigctld en « mode VFO » qui refuse « T currVFO 1 » : autres formes essayées."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import radio  # noqa: E402


class FakeServer(radio.RigctlRig):
    def __init__(self, accepts, vfo=True):
        self.accepts, self.sent, self.vfo_mode, self.sock = accepts, [], vfo, object()
        import threading
        self.lock = threading.Lock()
        self.tx = False

    def cmd(self, c, nlines=1, raw=False):
        if self.vfo_mode and not raw and c[:1] in "fmFMTl":
            c = c[:1] + " currVFO" + c[1:]
        self.sent.append(c)
        if c == "t" or c == "t currVFO":
            return ["1" if self.tx else "0"]
        ok = any(c.startswith(a) for a in self.accepts)
        if ok and ("T" in c[:9] or "set_ptt" in c):
            self.tx = not c.endswith(" 0")
        return ["RPRT 0" if ok else "RPRT -1"]


class Cat4om(unittest.TestCase):
    def setUp(self):
        self.p = mock.patch.object(radio.time, "sleep")
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_t_sans_vfo_accepte(self):
        r = FakeServer(accepts=["T 1", "T 0", "T 3", "T 2"])           # refuse « T currVFO … »
        r.ptt(True)
        self.assertTrue(r.tx)
        self.assertEqual(r._set_style, "none")
        r.sent.clear()
        r.ptt(False)
        self.assertEqual(r.sent[0], "T 0")                               # la bonne forme d'emblée

    def test_forme_longue(self):
        r = FakeServer(accepts=["\\set_ptt currVFO"])
        r.ptt(True)
        self.assertTrue(r.tx)
        self.assertEqual(r._set_style, "long")

    def test_vfoa(self):
        r = FakeServer(accepts=["F VFOA"])
        self.assertTrue(r._ok("F 7058000"))
        self.assertIn("F VFOA 7058000", r.sent)

    def test_vrai_rigctld_inchange(self):
        r = FakeServer(accepts=["T currVFO", "F currVFO"])
        self.assertTrue(r._ok("T 1"))
        self.assertEqual(r.sent, ["T currVFO 1"])

    def test_sans_mode_vfo_inchange(self):
        r = FakeServer(accepts=["T 1"], vfo=False)
        self.assertTrue(r._ok("T 1"))
        self.assertEqual(r.sent, ["T 1"])
