"""Version 0.95 : attendre que la fréquence soit libre avant d'émettre."""
import os
import sys
import time
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Var:
    def __init__(self, v):
        self.v = v

    def get(self):
        return self.v

    def set(self, v):
        self.v = v


class Btn(dict):
    def configure(self, **k):
        self.update(k)


def make(app, online=None, modems=None, waitfree=True):
    s = types.SimpleNamespace()
    for n in ("_freq_busy", "_tx_when_free", "_wait_tick", "_wait_clear", "_wait_go", "_wait_cancel",
              "_btn_emission", "_btn_emission_force"):
        setattr(s, n, getattr(app.App, n).__get__(s))
    s.WAIT_MAX_S, s.WAIT_HOLD_S, s.WAIT_SYNC_S = app.App.WAIT_MAX_S, app.App.WAIT_HOLD_S, app.App.WAIT_SYNC_S
    s.v_waitfree, s.v_state, s.v_call = Var(waitfree), Var(""), Var("F4GOP")
    s.mycall = lambda: "F4GOP"
    s.tx_busy, s.rig_freq, s.online = False, 7058000, online or {}
    s.rx_engine = types.SimpleNamespace(modems=modems or {}, drm=None, drm_t=0) if modems is not None else None
    s.rx_stream = object()
    s.gbtn = {"tx": Btn()}
    s._set_text = lambda w, t: w.__setitem__("text", t)
    s.logs, s.sent, s.ticks = [], [], []
    s.log = s.logs.append
    s.after = lambda ms, fn: s.ticks.append(fn)
    s.transmit = lambda: s.sent.append("image")
    return s


def tx_station(freq=7058500, state="TX"):
    return {"F4EEH": {"call": "F4EEH", "state": state, "freq": freq, "seen": time.time()}}


class FreqLibre(unittest.TestCase):
    def setUp(self):
        try:
            import app
        except ImportError as e:
            self.skipTest(str(e))
        self.app = app

    def test_libre_part_tout_de_suite(self):
        s = make(self.app)
        s._btn_emission()
        self.assertEqual(s.sent, ["image"])

    def test_case_decochee(self):
        s = make(self.app, online=tx_station(), waitfree=False)
        s._btn_emission()
        self.assertEqual(s.sent, ["image"])

    def test_station_internet_sur_ma_frequence(self):
        s = make(self.app, online=tx_station())
        s._btn_emission()
        self.assertEqual(s.sent, [])
        self.assertEqual(s.gbtn["tx"]["text"], "ATTENTE…")
        self.assertIn("F4EEH", s.v_state.get())
        # elle s'arrête : départ après le petit délai aléatoire
        s.online["F4EEH"]["state"] = "RX"
        s._wait_job["delay"] = 0
        s.ticks.pop()()
        self.assertEqual(s.sent, ["image"])
        self.assertEqual(s.gbtn["tx"]["text"], "ÉMISSION")

    def test_autre_bande_ignoree(self):
        s = make(self.app, online=tx_station(freq=14233000))
        s._btn_emission()
        self.assertEqual(s.sent, ["image"])

    def test_signal_radio(self):
        m = types.SimpleNamespace(sync=1, last_ok=0.0)
        s = make(self.app, modems={"DATAC3": m})
        s._btn_emission()
        self.assertEqual(s.sent, [])
        self.assertIn("DATAC3", s.v_state.get())
        m.sync = 0
        s._wait_job["delay"] = 0
        s.ticks.pop()()
        self.assertEqual(s.sent, ["image"])

    def test_annuler_et_forcer(self):
        s = make(self.app, online=tx_station())
        s._btn_emission()
        s._btn_emission()                       # second clic : annulée
        self.assertIsNone(s._wait_job)
        self.assertEqual(s.sent, [])
        s._btn_emission()
        s._btn_emission_force()                 # clic droit : tout de suite
        self.assertEqual(s.sent, ["image"])

    def test_attente_trop_longue(self):
        s = make(self.app, online=tx_station())
        s._btn_emission()
        s._wait_job["t0"] -= 400
        with mock.patch.object(self.app.messagebox, "askyesno", lambda *a, **k: True):
            s.ticks.pop()()
        self.assertEqual(s.sent, ["image"])


if __name__ == "__main__":
    unittest.main()
