"""1.12 : prénom séparé de l'indicatif ; une seule ligne par station dans les listes."""
import json
import os
import sys
import tempfile
import time
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


class Prenom(unittest.TestCase):
    def test_split(self):
        app = _app()
        self.assertEqual(app.split_call(" f4ltx chris "), ("F4LTX", "Chris"))
        self.assertEqual(app.split_call("F4GOP"), ("F4GOP", ""))
        self.assertEqual(app.split_call("PA0041SWL"), ("PA0041SWL", ""))
        self.assertEqual(app.split_call(""), ("", ""))
        self.assertEqual(app.split_call("F1ABL  jean pierre"), ("F1ABL", "Jean Pierre"))

    def test_reglages_corriges(self):
        app = _app()
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "c.json")
            with open(p, "w") as f:
                json.dump({"callsign": "F4LTX CHRIS", "conf_v": 64}, f)
            with mock.patch.object(app, "CONF_PATH", p):
                c = app.load_conf()
        self.assertEqual(c["callsign"], "F4LTX")
        self.assertEqual(c["opname"], "Chris")

    def _stub(self, app):
        s = types.SimpleNamespace(opnames={}, online={}, heard={}, known_loc={}, log=lambda m: None,
                                  _net_status=lambda: None, _heard_refresh=lambda: None,
                                  _remember_loc=lambda c, l: None)
        for n in ("_station_call", "_label", "_net_station"):
            setattr(s, n, getattr(app.App, n).__get__(s))
        return s

    def test_une_ligne_par_station(self):
        app = _app()
        s = self._stub(app)
        now = time.time()
        # ancienne version : prénom dans l'indicatif ; nouvelle : prénom à part
        s._net_station("F4LTX-CHRIS", {"call": "F4LTX CHRIS", "t": now})
        s._net_station("M7WUV", {"call": "M7WUV", "name": "andy", "t": now})
        s._net_station("F4LTX", {"call": "F4LTX", "t": now})
        calls = {d["call"] for d in s.online.values()}
        self.assertEqual(calls, {"F4LTX", "M7WUV"})
        self.assertEqual(s._label("F4LTX"), "F4LTX Chris")
        self.assertEqual(s._label("M7WUV"), "M7WUV Andy")
        # coupé à 8 caractères par la radio : même station, « AN » n'est pas pris pour un prénom
        self.assertEqual(s._station_call("M7WUV AN"), "M7WUV")
        self.assertEqual(s._station_call("G4ABC JO"), "G4ABC")
        self.assertEqual(s._label("G4ABC"), "G4ABC")
        self.assertEqual(s._station_call("F1JI PAU"), "F1JI")       # 8 caractères : peut-être coupé
        self.assertEqual(s._label("F1JI"), "F1JI")

    def test_mon_indicatif(self):
        app = _app()
        Var = lambda v: types.SimpleNamespace(get=lambda: v)
        s = types.SimpleNamespace(v_call=Var("f4gop denis"), v_opname=Var(""))
        self.assertEqual(app.App.mycall(s), "F4GOP")
        self.assertEqual(app.App.myname(s), "Denis")
        s.v_opname = Var("denis")
        s.v_call = Var("F4GOP")
        self.assertEqual(app.App.myname(s), "Denis")


if __name__ == "__main__":
    unittest.main()
