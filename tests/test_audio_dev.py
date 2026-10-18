"""Version 0.79 : entrée et sortie d'un codec USB portant exactement le même nom (TS-890 renommé)."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class FakeSD:
    DEVS = [{"name": "Microsoft Sound Mapper", "hostapi": 0, "max_input_channels": 2, "max_output_channels": 0},
            {"name": "TS-890 (2- USB AUDIO  CODEC)", "hostapi": 0, "max_input_channels": 2, "max_output_channels": 0},
            {"name": "Haut-parleurs (Realtek)", "hostapi": 0, "max_input_channels": 0, "max_output_channels": 2},
            {"name": "TS-890 (2- USB AUDIO  CODEC)", "hostapi": 0, "max_input_channels": 0, "max_output_channels": 2}]

    def query_devices(self, i=None):
        return self.DEVS if i is None else self.DEVS[i]

    def query_hostapis(self, i=None):
        apis = [{"name": "MME"}]
        return apis if i is None else apis[i]


class MemeNom(unittest.TestCase):
    def test_sortie_et_entree(self):
        try:
            import app
        except ImportError as e:            # pas de tkinter sur cette machine
            self.skipTest(str(e))
        with mock.patch.object(app, "sd", lambda: FakeSD()):
            lab = "8: TS-890 (2- USB AUDIO  CODEC) [MME]"      # numéro enregistré périmé
            self.assertEqual(app.App._dev_index(lab, output=True), 3)
            self.assertEqual(app.App._dev_index(lab, output=False), 1)
            self.assertEqual(app.App._dev_index("3: TS-890 (2- USB AUDIO  CODEC) [MME]", output=True), 3)
            self.assertEqual(app.App._dev_index(lab), 1)         # sans précision : comme avant


if __name__ == "__main__":
    unittest.main()
