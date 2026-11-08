"""2.26 : GitHub en panne passagère (504) -> la mise à jour réessaie toute seule."""
import os
import sys
import unittest
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import updater  # noqa: E402


def err(code):
    return urllib.error.HTTPError("https://github.com/x", code, "x", {}, None)


class Reessai(unittest.TestCase):
    def test_504_puis_ok(self):
        calls = []

        def fn():
            calls.append(1)
            if len(calls) < 3:
                raise err(504)
            return "ok"
        waits = []
        self.assertEqual(updater._retry(fn, sleep=waits.append), "ok")
        self.assertEqual(waits, [5, 15])

    def test_abandon_apres_3_essais(self):
        n = []

        def fn():
            n.append(1)
            raise err(504)
        with self.assertRaises(urllib.error.HTTPError):
            updater._retry(fn, sleep=lambda s: None)
        self.assertEqual(len(n), 3)

    def test_vraie_erreur_pas_de_reessai(self):
        n = []

        def fn():
            n.append(1)
            raise err(404)
        with self.assertRaises(urllib.error.HTTPError):
            updater._retry(fn, sleep=lambda s: None)
        self.assertEqual(len(n), 1)

    def test_empreinte_fausse_pas_de_reessai(self):
        n = []

        def fn():
            n.append(1)
            raise ValueError("empreinte SHA-256 différente")
        with self.assertRaises(ValueError):
            updater._retry(fn, sleep=lambda s: None)
        self.assertEqual(len(n), 1)

    def test_annule(self):
        import threading
        stop = threading.Event()
        stop.set()
        with self.assertRaises(urllib.error.HTTPError):
            updater._retry(lambda: (_ for _ in ()).throw(err(504)), stop=stop)
