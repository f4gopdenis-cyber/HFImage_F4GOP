"""Version 1.74 : interface en russe (traduction de Yuri)."""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import i18n  # noqa: E402
from i18n_ru import RU  # noqa: E402


class Russe(unittest.TestCase):
    def tearDown(self):
        i18n.set_lang("fr")

    def test_langue_proposee(self):
        self.assertEqual(i18n.LANGS["ru"], "Русский")

    def test_traduction(self):
        i18n.set_lang("ru")
        self.assertEqual(i18n.tr("Réglages"), "Настройки")
        self.assertIn("COM4", i18n.tr("COM4 n'existe pas (poste éteint, câble USB débranché ?)"))

    def test_chinois_toujours_la(self):
        i18n.set_lang("zh")
        self.assertEqual(i18n.tr("Réglages"), "设置")

    def test_valeurs_gardees(self):
        for fr, ru in RU.items():
            self.assertEqual(sorted(re.findall(r"\{\d\}", fr)), sorted(re.findall(r"\{\d\}", ru)), fr)

    def test_boutons_courts(self):
        i18n.set_lang("ru")
        self.assertEqual(i18n.tr_short("Log Station"), "Журнал")
        self.assertEqual(i18n.tr_short("Dossier"), i18n.tr("Dossier"))
        i18n.set_lang("en")
        self.assertEqual(i18n.tr_short("Log Station"), i18n.tr("Log Station"))


if __name__ == "__main__":
    unittest.main()


class RetoursLigne(unittest.TestCase):
    def test_pas_de_br(self):
        self.assertFalse([k for k, v in RU.items() if "<br>" in v])
