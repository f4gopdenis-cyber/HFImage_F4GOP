"""Carte : nom d'un petit pays écrit sur sa capitale (Liechtenstein/Vaduz, Monaco…) -> la capitale seule."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import stationmap as m


class PetitsPays(unittest.TestCase):
    def test_capitale_seule(self):
        for vivid in (True, False):
            im = m.render(m.View(6, 48, 28, 1000, 640), [], None, vivid=vivid)
            pays, villes = im.info.get("countries", []), im.info.get("cities", [])
            for p in ("LIECHTENSTEIN", "MONACO", "ANDORRE", "LUXEMBOURG"):
                self.assertNotIn(p, pays)
            for v in ("Vaduz", "Monaco", "Andorra", "Luxembourg"):
                self.assertIn(v, villes)
            for p in ("FRANCE", "ALLEMAGNE", "ITALIE", "SUISSE", "BELGIQUE"):
                self.assertIn(p, pays)                      # les grands pays restent, décalés s'il le faut
