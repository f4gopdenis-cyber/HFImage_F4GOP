"""2.59 (Keith Woodley) : aperçu traduit, enregistrer l'image RX, ◀ ▶, Échap, fermer ?, carte (recherche,
redessin regroupé)."""
import gc
import json
import os
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Keith259(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        cls.app_mod = app
        conf = os.path.join(tempfile.mkdtemp(), "c.json")
        cls.folder = tempfile.mkdtemp()
        with open(conf, "w") as f:
            json.dump({"callsign": "VK6WK", "licence_ok": "1.0", "lang": "en", "net_on": False,
                       "folder": cls.folder, "locator": "OF88CD"}, f)
        gc.collect()
        cls.p = mock.patch.object(app, "CONF_PATH", conf)
        cls.p.start()
        try:
            cls.a = app.App()
        except Exception as e:
            cls.p.stop()
            raise unittest.SkipTest(str(e))

    @classmethod
    def tearDownClass(cls):
        cls.a.destroy()
        cls.p.stop()
        import i18n
        i18n.set_lang("fr")

    def test_apercu_traduit(self):
        self.assertEqual(self.app_mod._mode_disp("DATAC1X aperçu"), "DATAC1X preview")
        self.assertEqual(self.app_mod._fmt_size(1170), "1.2 kB")
        self.assertEqual(self.app_mod._fmt_size(500), "500 B")

    def test_fermer_demande(self):
        a = self.a
        with mock.patch.object(self.app_mod.messagebox, "askyesno", return_value=False) as ask, \
                mock.patch.object(a, "_quit") as q:
            a._close_request()
        ask.assert_called_once()
        q.assert_not_called()
        a.conf["confirm_close"] = False
        with mock.patch.object(self.app_mod.messagebox, "askyesno") as ask, mock.patch.object(a, "_quit") as q:
            a._close_request()
        ask.assert_not_called()
        q.assert_called_once()
        a.conf["confirm_close"] = True

    def test_parcourir_et_enregistrer(self):
        from PIL import Image
        a = self.a
        a._gallery_open()
        paths = []
        for k, col in enumerate(("red", "green", "blue")):
            p = os.path.join(self.folder, f"img{k}.png")
            Image.new("RGB", (64, 48), col).save(p)
            paths.append(p)
            a._gallery_add("rx", f"VK6A{k}", "DATAC1", p, p, 100)
            time.sleep(0.01)
        a.rx_browse(-1)                                     # rien d'affiché : la plus récente
        self.assertEqual(a._rx_shown["png"], paths[2])
        a.rx_browse(-1)                                     # ◀ : plus ancienne
        self.assertEqual(a._rx_shown["png"], paths[1])
        a.rx_browse(1)                                      # ▶ : plus récente
        self.assertEqual(a._rx_shown["png"], paths[2])
        out = os.path.join(tempfile.mkdtemp(), "saved.jpg")
        with mock.patch.object(self.app_mod.filedialog, "asksaveasfilename", return_value=out):
            a.save_rx_image(a.lb_rx.pil)
        self.assertEqual(Image.open(out).format, "JPEG")
        a.show_tab("rx")
        a.update()
        r = a._key_escape(SimpleNamespace(widget=a.lb_rx))
        self.assertEqual(r, "break")
        a.update()
        self.assertTrue(a._tab_shown("tx"))

    def test_carte(self):
        import stationmap
        a = self.a
        prov = lambda: ({"call": "VK6WK", "pos": (-32.0, 115.9)},
                        [{"call": "F4EEH", "pos": (48.8, -0.5), "ok": False},
                         {"call": "VK6NJP", "pos": (-31.9, 115.8), "ok": True}])
        m = stationmap.MapWindow(a, prov, tr=self.app_mod.tr)
        try:
            t0 = time.time()
            while time.time() - t0 < 0.5:                  # premier dessin (taille de la fenêtre)
                m.win.update()
                time.sleep(0.05)
            n = {"k": 0}
            orig = m.redraw
            m.redraw = lambda: (n.__setitem__("k", n["k"] + 1), orig())
            m._redraw_t = time.time()
            for _ in range(10):
                m.redraw_soon()
            t0 = time.time()
            while time.time() - t0 < 2.6:
                m.win.update()
                time.sleep(0.05)
            self.assertEqual(n["k"], 1)                    # dix demandes -> un seul dessin
            self.assertTrue(m.find("eeh"))
            self.assertTrue(m.v_heard.get())               # station en jaune : les autres sont affichées
            self.assertFalse(m.find("ZZ9ZZ"))
        finally:
            m.close()


if __name__ == "__main__":
    unittest.main()
