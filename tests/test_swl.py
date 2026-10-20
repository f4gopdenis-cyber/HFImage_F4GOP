"""Version 0.99 : indicatifs d'écouteurs (SWL)."""
import os
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


def _app():
    try:
        import app
        return app
    except (ImportError, OSError) as e:
        raise unittest.SkipTest(str(e))


class Swl(unittest.TestCase):
    def test_reconnus(self):
        app = _app()
        for c in ("PA0041SWL", "F-12345", "14VD274", "14FR79", "ONL1234", "de-ab123"):
            self.assertTrue(app.is_swl(c), c)
        for c in ("F4GOP", "F4GOP/P", "2E0ABC", "4X1AB", "9A1A", "M0JGM", "G7VQV", "DL1ABC", "EA8/F4GOP",
                  "F11GYT", "AA3SO", ""):
            self.assertFalse(app.is_swl(c), c)

    def test_assistant_accepte(self):
        try:
            import setupwiz
        except ImportError as e:
            self.skipTest(str(e))
        for c in ("F4GOP", "F4GOP/P", "PA0041SWL", "F-12345", "14VD274", "EA8/F4GOP"):
            self.assertTrue(setupwiz.CALL_RE.match(c), c)
        for c in ("", "AB", "SWL", "F4GOP!"):
            self.assertFalse(setupwiz.CALL_RE.match(c), c)

    def test_swl_n_emet_jamais(self):
        app = _app()
        logs, shown = [], []
        s = types.SimpleNamespace(tx_busy=False, v_call=types.SimpleNamespace(get=lambda: "PA0041SWL"), mycall=lambda: "PA0041SWL",
                                  log=logs.append)
        with mock.patch.object(app.messagebox, "showinfo", lambda *a, **k: shown.append(a[1])):
            self.assertFalse(app.App._start_job(s, {"kind": "ack"}, quiet=True))
            self.assertFalse(app.App._start_job(s, {"kind": "image"}))
        self.assertEqual(len(logs), 1)
        self.assertIn("Internet", shown[0])

    def test_indicatif_complet(self):
        app = _app()
        s = types.SimpleNamespace(online={"x": {"call": "PA0041SWL"}, "y": {"call": "F4EEH"}}, heard={})
        self.assertEqual(app.App._full_call(s, "PA0041SW"), "PA0041SWL")
        self.assertEqual(app.App._full_call(s, "F4EEH"), "F4EEH")
        s.online["z"] = {"call": "PA0041SWX"}            # ambigu : on ne devine pas
        self.assertEqual(app.App._full_call(s, "PA0041SW"), "PA0041SW")


    def test_liste_lisible(self):
        """1.00 : indicatifs longs alignés, liste jamais décalée vers la droite."""
        app = _app()
        import tkinter as tk
        try:
            root = tk.Tk()
        except tk.TclError as e:
            self.skipTest(str(e))
        lb, rx = tk.Listbox(root, width=10), tk.Listbox(root, width=8)
        lb.pack()
        rx.pack()
        now = __import__("time").time()
        s = types.SimpleNamespace(
            heard={}, rxok={"PA0041SWL": (-1, now)}, lst_heard=lb, lst_rxok=rx, rig_freq=None, map_win=None,
            online={"a": {"call": "PA0041SWL", "t": now, "state": "RX"}, "b": {"call": "F4EEH", "t": now,
                                                                              "state": "RX", "freq": 7058000}},
            lb_heard=tk.Label(root), lb_rxok=tk.Label(root), _net_status=lambda: None,
            _set_text=lambda w, t: None, _c=lambda c: c, _mhz=app.App._mhz.__get__(object()) if False else
            (lambda f: f"{f / 1e6:.3f}" if f else "—"), _is_hyb=lambda c, on=None: False, _label=lambda c: c)
        lb.insert("end", "x" * 80)
        lb.xview_moveto(0.5)
        app.App._heard_refresh(s)
        root.update()
        self.assertEqual(lb.xview()[0], 0.0)
        rows = lb.get(0, "end")
        self.assertEqual(len(rows[0].rstrip()), len(rows[1].rstrip()))   # colonnes alignées
        root.destroy()


if __name__ == "__main__":
    unittest.main()
