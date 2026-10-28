"""1.83 : préréglages de poste (comme EasyPal) — VK6NJP : FT-857D, IC-7300, IC-9700."""
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import app  # noqa: E402


class Var:
    def __init__(self, v):
        self.v = v

    def get(self):
        return self.v

    def set(self, v):
        self.v = v


class Prereglages(unittest.TestCase):
    def stub(self):
        s = types.SimpleNamespace(conf={}, logs=[], saved=[], restarted=[])
        s.v_out, s.v_in, s.v_lvl = Var("3: Speakers (USB CODEC) [MME]"), Var("1: Mic (USB CODEC) [MME]"), Var(40)
        s.log = s.logs.append
        s._save_conf_file = lambda: s.saved.append(1)
        s.save_conf = lambda quiet=False: s.saved.append(2)
        s._in_changed = lambda: s.restarted.append(s.v_in.get())
        for k in ("rig_presets", "save_rig_preset", "delete_rig_preset", "use_rig_preset"):
            setattr(s, k, getattr(app.App, k).__get__(s))
        return s

    def test_enregistrer_charger_supprimer(self):
        s = self.stub()
        s.save_rig_preset("IC-7300", {"rig": "hamlib:3073", "port": "COM3"})
        s.v_out.set("5: Speakers (Interface) [MME]"); s.v_in.set("2: Line (Interface) [MME]"); s.v_lvl.set(70)
        s.save_rig_preset("FT-857D", {"rig": "hamlib:1022", "port": "COM7"})
        self.assertEqual(sorted(s.rig_presets()), ["FT-857D", "IC-7300"])
        self.assertEqual(s.rig_presets()["IC-7300"]["radio"]["port"], "COM3")
        s.use_rig_preset("IC-7300")                          # cartes son et niveau du 7300
        self.assertEqual(s.v_in.get(), "1: Mic (USB CODEC) [MME]")
        self.assertEqual(s.v_out.get(), "3: Speakers (USB CODEC) [MME]")
        self.assertEqual(s.v_lvl.get(), 40)
        self.assertEqual(s.restarted, ["1: Mic (USB CODEC) [MME]"])     # écoute relancée
        self.assertEqual(s.conf["rig_preset"], "IC-7300")
        s.delete_rig_preset("IC-7300")
        self.assertEqual(list(s.rig_presets()), ["FT-857D"])
        self.assertEqual(s.conf["rig_preset"], "")

    def test_reglages_anciens_sans_prereglage(self):
        s = self.stub()
        s.conf["rig_presets"] = "abîmé"
        self.assertEqual(s.rig_presets(), {})


if __name__ == "__main__":
    unittest.main()
