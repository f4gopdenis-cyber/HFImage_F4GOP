"""2.04 (demande de VK6NJP) : format de la date du bandeau « Mes conditions de trafic » au choix :
international (par défaut), jour/mois/année, mois/jour/année."""
import os
import re
import sys
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import clocktz  # noqa: E402
import trafic  # noqa: E402

T = time.struct_time((2026, 11, 4, 8, 53, 0, 2, 308, 0))


class Format(unittest.TestCase):
    def date(self, fmt=None):
        c = dict(trafic.DEFAULT, tc_call=False, tc_loc=False, tc_freq=False)
        if fmt:
            c["tc_datefmt"] = fmt
        with mock.patch.object(time, "gmtime", lambda *a: T), mock.patch.object(time, "localtime", lambda *a: T):
            return trafic.parts(c)[0]

    def test_par_defaut_inchange(self):
        self.assertTrue(self.date().startswith("2026-11-04 "))

    def test_australie(self):
        self.assertTrue(self.date("jma").startswith("04/11/2026 "))

    def test_etats_unis(self):
        self.assertTrue(self.date("mja").startswith("11/04/2026 "))

    def test_cache_ignore_la_minute(self):
        # la date change chaque minute : elle ne doit pas refaire l'image à chaque fois (tous formats)
        rx = r"(\d{4}-\d\d-\d\d|\d\d/\d\d/\d{4}) \d\d:\d\d"
        for f in ("iso", "jma", "mja"):
            self.assertTrue(re.match(rx, self.date(f)), f)


if __name__ == "__main__":
    unittest.main()
