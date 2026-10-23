"""1.27 : vignette de la dernière image reçue dans le panneau d'état."""
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Vignette(unittest.TestCase):
    def test_texte_et_image(self):
        try:
            import app
            from PIL import Image
        except (ImportError, OSError) as e:
            self.skipTest(str(e))
        got = []
        s = types.SimpleNamespace(opnames={"F4EEH": "Jean"}, known_loc={"F4EEH": "JN18EU"},
                                  v_loc=types.SimpleNamespace(get=lambda: "IN98QR"), mycall=lambda: "F4GOP",
                                  myname=lambda: "", _journal=lambda t: got.append(("err", t)),
                                  panel=types.SimpleNamespace(set_thumb=lambda im, t: got.append((im.size, t))))
        s.online = {}
        for n in ("_station_call", "_label", "_distance_to"):
            setattr(s, n, getattr(app.App, n).__get__(s))
        app.App._panel_thumb(s, Image.new("RGB", (40, 30)), "F4EEH")
        size, txt = got[0]
        self.assertEqual(size, (40, 30))
        self.assertEqual(txt.split("\n")[0], "F4EEH Jean")
        self.assertRegex(txt.split("\n")[1], r"^\d+ km$")
        got.clear()
        app.App._panel_thumb(s, Image.new("RGB", (40, 30)), "?")      # indicatif inconnu : image seule
        self.assertEqual(got[0][1], "")


if __name__ == "__main__":
    unittest.main()
