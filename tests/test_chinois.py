"""Version 1.71 : interface en chinois simplifié (traduction de BH2RMX et BD4QXR)."""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import i18n  # noqa: E402
from i18n_zh import ZH  # noqa: E402


class Chinois(unittest.TestCase):
    def tearDown(self):
        i18n.set_lang("fr")

    def test_langue_proposee(self):
        self.assertIn("zh", i18n.LANGS)

    def test_traduction(self):
        i18n.set_lang("zh")
        self.assertEqual(i18n.tr("Réglages"), "设置")
        self.assertIn("COM4", i18n.tr("COM4 n'existe pas (poste éteint, câble USB débranché ?)"))

    def test_texte_absent_en_anglais(self):
        i18n.set_lang("zh")
        fr = next(r[0] for r in i18n.T if r[0] not in ZH and "{0}" not in r[0])
        row = next(r for r in i18n.T if r[0] == fr)
        self.assertEqual(i18n.tr(fr), row[1])

    def test_valeurs_gardees(self):
        for fr, zh in ZH.items():
            self.assertEqual(sorted(re.findall(r"\{\d\}", fr)), sorted(re.findall(r"\{\d\}", zh)), fr)

    def test_polices_chinoises_seulement_en_chinois(self):
        self.assertEqual(i18n.cjk_fonts(), ())
        i18n.set_lang("zh")
        self.assertIn("msyh.ttc", i18n.cjk_fonts())


if __name__ == "__main__":
    unittest.main()
