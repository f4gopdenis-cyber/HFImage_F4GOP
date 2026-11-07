"""2.22 : barres de titre aux couleurs de l'ambiance (Windows 11 ; Windows 10 : sombre)."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import theme  # noqa: E402
import titlebar  # noqa: E402


class Barre(unittest.TestCase):
    def test_colorref(self):
        self.assertEqual(titlebar.colorref("#ff0000"), 0x0000FF)
        self.assertEqual(titlebar.colorref("#0000ff"), 0xFF0000)
        self.assertEqual(titlebar.colorref("#123456"), 0x563412)

    def test_plan_ambiance(self):
        P = theme.MODERN["Néon trio"]
        d = dict(titlebar.plan(P))
        self.assertEqual(d[titlebar.DWMWA_USE_IMMERSIVE_DARK_MODE], 1)
        self.assertEqual(d[titlebar.DWMWA_CAPTION_COLOR], titlebar.colorref(P["top"]))
        self.assertEqual(d[titlebar.DWMWA_TEXT_COLOR], titlebar.colorref(P["top_fg"]))
        self.assertEqual(d[titlebar.DWMWA_BORDER_COLOR], titlebar.colorref(P["border"]))

    def test_plan_classique_remet_windows(self):
        d = dict(titlebar.plan(None))
        self.assertEqual(d[titlebar.DWMWA_USE_IMMERSIVE_DARK_MODE], 0)
        self.assertEqual(d[titlebar.DWMWA_CAPTION_COLOR], titlebar.DWMWA_COLOR_DEFAULT)

    def test_rien_hors_windows(self):
        with mock.patch.object(titlebar.sys, "platform", "linux"):
            self.assertFalse(titlebar.apply(object(), theme.MODERN["Néon trio"]))

    def test_toutes_les_ambiances(self):
        for n, P in theme.MODERN.items():
            self.assertEqual(len(titlebar.plan(P)), 4, n)
