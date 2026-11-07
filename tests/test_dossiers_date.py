"""2.14 (BH2RMX) : vrai dossier Documents (déplacé sur D:), fichiers recopiés ; un seul format de
date (Réglages → Station) pour le bandeau et la carte QSL, montré avec la date du jour."""
import gc
import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Migration(unittest.TestCase):
    def setUp(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.app = app

    def test_fichiers_recopies(self):
        d = tempfile.mkdtemp()
        old, new = os.path.join(d, "C", "HFImage"), os.path.join(d, "D", "HFImage")
        os.makedirs(os.path.join(old, "wav"))
        for n in ("stations.csv", "locators.json"):
            with open(os.path.join(old, n), "w") as f:
                f.write(n)
        with open(os.path.join(old, "wav", "id.wav"), "w") as f:
            f.write("x")
        os.makedirs(os.path.join(old, "2026-11-06"))                 # images reçues : pas recopiées
        done = self.app._migrate_old_out(old, new)
        self.assertEqual(sorted(done), ["locators.json", "stations.csv", "wav"])
        self.assertTrue(os.path.exists(os.path.join(new, "wav", "id.wav")))
        self.assertFalse(os.path.exists(os.path.join(new, "2026-11-06")))
        self.assertEqual(self.app._migrate_old_out(old, new), [])   # déjà là : rien d'écrasé

    def test_meme_dossier(self):
        d = tempfile.mkdtemp()
        self.assertEqual(self.app._migrate_old_out(d, d), [])

    def test_documents_existe(self):
        self.assertTrue(self.app._documents_dir())


class DateFmt(unittest.TestCase):
    def setUp(self):
        gc.collect()
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.app = app
        d = tempfile.mkdtemp()
        self.conf = os.path.join(d, "c.json")
        with open(self.conf, "w") as f:
            json.dump({"callsign": "BH2RMX", "licence_ok": "1.0", "lang": "en", "net_on": False}, f)
        self.p = mock.patch.object(app, "CONF_PATH", self.conf)
        self.p.start()
        try:
            self.a = app.App()
        except Exception as e:
            self.p.stop()
            raise unittest.SkipTest(str(e))
        self.a.update()

    def tearDown(self):
        self.a._closing = True
        for w in self.a.winfo_children():
            if isinstance(w, self.app.tk.Toplevel):
                w.destroy()
        self.a.destroy()
        self.a = None
        gc.collect()
        self.p.stop()

    def test_date_du_jour(self):
        dn = self.a._date_names()
        self.assertEqual(dn["iso"], time.strftime("%Y-%m-%d"))
        self.assertTrue(dn["jma"].startswith(time.strftime("%d/%m/%Y")))

    def test_reglage_station_et_qsl(self):
        a = self.a
        if not hasattr(a, "v_datefmt"):
            self.skipTest("réglages non construits")
        a.v_datefmt.set(a._date_names()["jma"])
        a._datefmt_chosen()
        self.assertEqual(a.conf["tc_datefmt"], "jma")
        seen = []
        with mock.patch.object(self.app.clocktz, "fmt", lambda f, *x, **k: (seen.append(f), "x")[1]):
            a.qsl_dialog()
        self.assertIn("%d/%m/%Y %H:%M", seen)


class OneDriveRefuse(unittest.TestCase):
    """2.17 (VK6NJP) : Documents dans OneDrive, création du dossier refusée -> ancien emplacement."""
    def setUp(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.app = app

    def test_dossier_refuse_ancien_emplacement(self):
        d = tempfile.mkdtemp()
        bloque = os.path.join(d, "fichier")
        with open(bloque, "w") as f:
            f.write("x")                                   # un fichier : on ne peut rien créer dessous
        home = os.path.join(d, "home")
        with mock.patch.object(self.app, "_documents_dir", return_value=bloque), \
                mock.patch.object(self.app.os.path, "expanduser", return_value=home):
            out = self.app._main_out()
        self.assertEqual(out, os.path.join(home, "Documents", "HFImage"))

    def test_dossier_utilisable_garde(self):
        d = tempfile.mkdtemp()
        with mock.patch.object(self.app, "_documents_dir", return_value=d):
            self.assertEqual(self.app._main_out(), os.path.join(d, "HFImage"))
        self.assertEqual(os.listdir(os.path.join(d, "HFImage")), [])     # fichier de test effacé
